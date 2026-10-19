import email_pipeline
import gmail_sync
import base64
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import torch
from fastapi.testclient import TestClient

import predict
from classifier_contract import LABELS
import routes
from main import app
from email_utils import clean_email_body, extract_email_body


def part(mime, text):
    return {
        "mimeType": mime,
        "body": {"data": base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")}
    }


def test_html_cleaning():
    body = '<style>.x {color:red}</style><p>Hello&nbsp;Ali</p><p>A &lt; B</p><script>bad()</script><a href="https://example.com">Details</a>'
    assert clean_email_body(body) == 'Hello Ali\n\nA < B\nDetails (https://example.com)'


def test_plain_text_cleaning():
    assert clean_email_body('  Hello\t Ali\r\n\r\n\r\n[https://example.com]\nBye  ') == 'Hello Ali\n\n[https://example.com]\nBye'
    assert clean_email_body('Keep [notes] and 2 < 3', is_html=False) == 'Keep [notes] and 2 < 3'
    assert clean_email_body(None) == ''
    assert clean_email_body('👩\u200d💻') == '👩\u200d💻'


def test_nested_email_prefers_plain_and_skips_attachment():
    attachment = part('text/plain', 'attachment text')
    attachment['filename'] = 'notes.txt'
    payload = {"mimeType": "multipart/mixed", "parts": [
        {"mimeType": "multipart/alternative", "parts": [
            part('text/html', '<p>HTML version</p>'),
            part('text/plain', 'Plain version')
        ]}, attachment
    ]}
    assert extract_email_body(payload) == 'Plain version'
    assert extract_email_body(part('text/html', '<p>Hello</p><p>World</p>')) == 'Hello\n\nWorld'
    assert extract_email_body({}) == ''


def test_email_charset():
    payload = part('text/plain', '')
    payload['headers'] = [{'name': 'Content-Type', 'value': 'text/plain; charset=iso-8859-1'}]
    payload['body']['data'] = base64.urlsafe_b64encode('café'.encode('iso-8859-1')).decode().rstrip('=')
    assert extract_email_body(payload) == 'café'


@pytest.mark.parametrize('logits', [[1.0, 3.0, 2.0] + [-9.0] * 7, [-5.0, -3.0, -4.0] + [-9.0] * 7])
def test_returns_only_highest_prediction(monkeypatch, logits):
    tokenizer = Mock(return_value={})
    model = Mock(return_value=SimpleNamespace(logits=torch.tensor([logits])))
    model.config = SimpleNamespace(id2label=dict(enumerate(LABELS)),
        label2id={label: i for i, label in enumerate(LABELS)},
        problem_type='multi_label_classification', max_position_embeddings=512)
    monkeypatch.setattr(predict, 'tokenizer', tokenizer)
    monkeypatch.setattr(predict, 'model', model)
    result = predict.classify_email('Subject', '<p>Clean body</p>')
    assert len(result) == 1
    assert result[0]['category'] == 'Customer Support'
    assert result[0]['confidence'] == pytest.approx(torch.sigmoid(torch.tensor(logits[1])).item())
    assert tokenizer.call_args.args[0] == 'Subject Clean body'


def test_gmail_returns_clean_body_and_one_prediction(monkeypatch):
    service = Mock()
    service.users.return_value.getProfile.return_value.execute.return_value = {'historyId': '10'}
    messages = service.users.return_value.messages.return_value
    messages.list.return_value.execute.return_value = {'messages': [{'id': 'test-id'}]}
    messages.get.return_value.execute.return_value = {
        'payload': part('text/html', '<p>Hello</p><script>bad()</script>')
    }
    classifier = Mock(return_value=[{'category': 'Personal', 'confidence': 0.8}])
    monkeypatch.setattr(gmail_sync, 'get_gmail_service', lambda *args: service)
    monkeypatch.setattr(email_pipeline, 'classify_email', classifier)
    with TestClient(app) as client:
        response = client.post('/gmail/messages')
    assert response.status_code == 200
    assert response.json()['emails'][0]['body'] == 'Hello'
    assert response.json()['emails'][0]['subject'] == ''
    assert len(response.json()['emails'][0]['predictions']) == 1
    classifier.assert_called_once_with('', 'Hello')


def test_html_in_plain_text():
    payload = part('text/plain', '<div style="display:none">padding</div><p>Offer ends Friday</p>')
    assert extract_email_body(payload) == 'Offer ends Friday'


def test_tracking_footer_and_padding():
    body = 'Register today < Campaign&eventSeriesCode=test&utm_source=email>\n\u034f \u200c \u200c\nPrice: $100\nUnsubscribe | Privacy\nCompany address'
    assert clean_email_body(body) == 'Register today\n\nPrice: $100'


def test_useful_image_text_and_empty_plain_fallback():
    payload = {'mimeType': 'multipart/alternative', 'parts': [
        part('text/plain', 'View in browser\nUnsubscribe'),
        part('text/html', '<img alt="Save 20% on shoes" src="https://example.com/banner.png">')
    ]}
    assert extract_email_body(payload) == 'Save 20% on shoes'


def test_cleaning_keeps_message_content():
    text = 'My newsletter subscription failed. Please help.\nInvoice: $120\nMeeting on Friday at 10:00'
    assert clean_email_body(text) == text
    assert clean_email_body('A &lt; B and C &amp; D') == 'A < B and C & D'


def test_broken_html_and_cleaning_twice():
    body = '<p>New collection</p><table><tr><td><a href=" ><img src=" alt="brand"></a></td></tr></table>'
    cleaned = clean_email_body(body)
    assert '<table' not in cleaned
    assert 'href=' not in cleaned
    assert 'New collection' in cleaned
    assert clean_email_body(cleaned) == cleaned


def test_encoded_html_and_unsubscribe_question():
    assert clean_email_body('&lt;p&gt;Hello&lt;/p&gt;') == 'Hello'
    assert clean_email_body('Unsubscribe is not working. Please help.') == 'Unsubscribe is not working. Please help.'


def test_gmail_passes_clean_content_to_summary_and_tasks(monkeypatch, test_database):
    from models import Email
    from summarizer import summarize_email
    from task_extractor import extract_action_items
    raw = ('Please submit your application.\n\nConfidentiality notice\n'
           'If you are not the intended recipient, delete this message.\n'
           'Send email to info@example.com')
    service = Mock()
    service.users.return_value.getProfile.return_value.execute.return_value = {'historyId': '10'}
    messages = service.users.return_value.messages.return_value
    messages.list.return_value.execute.return_value = {'messages': [{'id': 'clean-content-regression'}]}
    messages.get.return_value.execute.return_value = {'payload': part('text/plain', raw)}
    summary = Mock(wraps=summarize_email)
    tasks = Mock(wraps=extract_action_items)
    monkeypatch.setattr(gmail_sync, 'get_gmail_service', lambda *args: service)
    monkeypatch.setattr(email_pipeline, 'classify_email', Mock(return_value=[{'category': 'Business', 'confidence': 0.8}]))
    monkeypatch.setattr(email_pipeline, 'summarize_email', summary)
    monkeypatch.setattr(email_pipeline, 'extract_action_items', tasks)
    with TestClient(app) as client:
        response = client.post('/gmail/messages')
    assert response.status_code == 200
    assert response.json()['success_count'] == 1
    summary.assert_called_once_with('', 'Please submit your application.')
    tasks.assert_called_once_with('', 'Please submit your application.', None)
    email = test_database.query(Email).filter_by(message_id='clean-content-regression').one()
    assert email.body == email.summary == 'Please submit your application.'
    assert [task.task for task in email.tasks] == ['Submit your application']
