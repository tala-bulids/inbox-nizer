"""Shared fields for inbox and detail responses."""
from models import Email


def serialize_email(email: Email, *, include_body: bool = False) -> dict:
    result = {
        'id': email.id,
        'message_id': email.message_id,
        'from': email.sender,
        'date': email.email_date,
        'sent_at': email.sent_at,
        'message_at': email.message_at,
        'date_status': email.date_status,
        'subject': email.subject,
        'summary': email.summary,
        'priority_score': email.priority_score,
        'priority_level': email.priority_level,
        'created_at': email.created_at,
        'predictions': [
            {'category': prediction.category, 'confidence': prediction.confidence}
            for prediction in email.predictions
        ],
        'tasks': [
            {'task': task.task, 'confidence': task.confidence,
             'deadline_text': task.deadline_text, 'deadline_date': task.deadline_date,
             'deadline_at': task.deadline_at, 'deadline_confidence': task.deadline_confidence}
            for task in email.tasks
        ],
    }
    if include_body:
        result['body'] = email.body
    return result
