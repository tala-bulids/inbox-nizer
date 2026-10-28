import copy
import json
from pathlib import Path

import numpy as np
import pytest

from classifier_contract import LABELS
from ml_phase2.data import CONFIG, digest, language, load_development, normalize, prepare, read, write
from ml_phase2.evaluation import evaluate


def examples():
    words = ['invoice','holiday','penguin','university','calendar','ticket','signature','password','volcano','telescope', 'elephant','river','forest','satellite','workshop','interview','appointment','helicopter','document','orchard']
    return [{'subject':word, 'body':word+' sample.', 'labels':[LABELS[i%10]]} for i,word in enumerate(words)]


def test_normalization_and_language():
    text = normalize('Subject', '<p>Contact sample@example.invalid https://example.invalid +12345678901</p>')
    assert '@' not in text and 'https' not in text and '12345678901' not in text
    assert 'EMAIL' in text and 'URL' in text and 'NUMBER' in text
    assert normalize('', 'الرسالة العربية') == 'الرسالة العربية'
    assert language('الرسالة العربية') == 'ar'
    assert language('English meeting') == 'en'
    assert language('Hello مرحبا') == 'mixed'


def test_provenance_conflicts_and_deterministic_group_splits():
    raw = examples()
    raw += [dict(raw[0]), {**raw[1], 'labels':['Business']}]
    rows, audit = prepare(raw, 'fixture@revision')
    assert audit['quarantined_rows'] == 2
    duplicate = next(r for r in rows if r['text'].startswith('invoice'))
    assert len(duplicate['provenance']) == 2
    assert all(p['source']=='fixture@revision' for p in duplicate['provenance'])
    groups = {s:{r['group'] for r in rows if r['split']==s} for s in ('train','validation','test')}
    assert not groups['train'] & groups['validation']
    assert not groups['train'] & groups['test']
    assert not groups['test'] & groups['validation']
    assert prepare(raw, 'fixture@revision') == (rows,audit)


def test_sender_and_template_groups_do_not_cross_splits():
    raw = examples()
    raw[0]['sender_domains'] = ['example.invalid']
    raw[8]['sender_domains'] = ['example.invalid']
    raw += [{'subject':'Booking 123','body':'Your reservation confirmed 2026','labels':['Travel & Bookings']},
            {'subject':'Booking 456','body':'Your reservation confirmed 2027','labels':['Travel & Bookings']}]
    rows,_ = prepare(raw,'fixture')
    grouped = [r for r in rows if r['text'].startswith(('invoice','volcano'))]
    assert len({r['group'] for r in grouped}) == 1
    templates = [r for r in rows if r['text'].startswith('Booking')]
    assert len({r['group'] for r in templates}) == 1


def freeze(tmp_path):
    rows = [{'id':'a','group':'a','text':'only train','labels':['Business'],'language':'en'}]
    write(tmp_path/'train.json',rows)
    write(tmp_path/'validation.json',[{**rows[0],'id':'b','group':'b'}])
    # Malformed test must never be read by the development loader.
    (tmp_path/'test.json').write_text('DO NOT OPEN: not JSON')
    write(tmp_path/'manifest.json',{'config_sha256':digest(CONFIG), 'files':{
        n:digest(tmp_path/n) for n in ('train.json','validation.json','test.json')}})


def test_development_loader_never_reads_test(tmp_path, monkeypatch):
    freeze(tmp_path)
    original = Path.open
    def guard(self,*a,**kw):
        assert self.name != 'test.json'
        return original(self,*a,**kw)
    monkeypatch.setattr(Path,'open',guard)
    parts,_ = load_development(tmp_path)
    assert set(parts)=={'train','validation'}


def test_changed_data_fails_closed(tmp_path):
    freeze(tmp_path)
    (tmp_path/'train.json').write_text('[]')
    with pytest.raises(ValueError,match='changed'):
        load_development(tmp_path)


def test_cross_split_group_leakage_fails_closed(tmp_path):
    freeze(tmp_path)
    path=tmp_path/'validation.json'
    rows=read(path); rows[0]['group']='a'; path.write_text(json.dumps(rows))
    manifest=read(tmp_path/'manifest.json');manifest['files']['validation.json']=digest(path)
    (tmp_path/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match='leakage'):
        load_development(tmp_path)


def test_multilabel_metrics_missing_arabic_and_calibration():
    rows=[{'labels':['Business','Customer Support'],'language':'en'}, {'labels':['Business'],'language':'en'}]
    scores=np.zeros((2,10))+.01
    scores[0,1]=.9; scores[1,0]=.8
    m=evaluate(scores,rows)
    assert m['top1_accuracy']==1
    assert m['by_language']['ar']=={'n':0,'status':'unavailable'}
    assert sum(map(sum,m['confusion_matrix']))==2
    assert m['confusion_matrix'][0][1]==.5
    assert m['top1_ece']==pytest.approx(.15)
    assert m['top1_weighted_f1']==pytest.approx((2*(2/3)+1)/3)
    assert not m['test_evaluated']


def test_nonfinite_metrics_rejected():
    with pytest.raises(ValueError):
        evaluate(np.full((1,10),np.nan),[{'labels':['Business'],'language':'en'}])


def test_outputs_are_immutable(tmp_path):
    path=tmp_path/'metrics.json';write(path,{'n':1})
    with pytest.raises(FileExistsError):
        write(path,{'n':2})


def test_selection_excludes_contaminated_legacy_and_test_results():
    from ml_phase2.report import compare
    def candidate(name,score,eligible=True):
        return {'run':{'candidate':name,'data_manifest_sha256':'same','config_sha256':'same',
                       'test_evaluated':False,'eligible_research_selection':eligible,'benchmark':{'p95_ms':10}},
                'metrics':{'top1_macro_f1':score,'top1_accuracy':score,'test_evaluated':False}}
    runs=[candidate('A',.7),candidate('B',.99,False),candidate('C',.6)]
    assert compare(runs)['selected_research_candidate']=='A'
    assert compare(runs)['production_selected_model'] is None
    runs[0]['run']['data_manifest_sha256']='different'
    with pytest.raises(ValueError,match='freeze'):
        compare(runs)
    runs[0]['run']['data_manifest_sha256']='same'
    runs[0]['metrics']['test_evaluated']=True
    with pytest.raises(ValueError,match='Test'):
        compare(runs)


@pytest.mark.parametrize('text', ['', 'unknown'])
def test_unknown_labels_rejected(text):
    with pytest.raises(ValueError):
        prepare([{'subject':text,'body':text,'labels':['invented']}], 'fixture')


def test_tiny_hf_training_is_reproducible_and_checkpointed(tmp_path):
    # Architecture test only: random tiny weights and fictional tokens, not an experiment.
    from tokenizers import Tokenizer
    from tokenizers.models import WordLevel
    from tokenizers.pre_tokenizers import Whitespace
    from transformers import PreTrainedTokenizerFast, DistilBertConfig, DistilBertForSequenceClassification
    from ml_phase2.finetune import fit, seed_everything
    vocab={'[PAD]':0,'[UNK]':1, **{f'word{i}':i+2 for i in range(10)}}
    tok=Tokenizer(WordLevel(vocab,unk_token='[UNK]'));tok.pre_tokenizer=Whitespace()
    tokenizer=PreTrainedTokenizerFast(tokenizer_object=tok,unk_token='[UNK]',pad_token='[PAD]',model_max_length=32)
    tokenizer.model_input_names=['input_ids','attention_mask']
    conf=copy.deepcopy(read(CONFIG))
    conf['finetune'].update(epochs=2,batch_size=10,max_length=32,train_last_layers=1,patience=1)
    rows=[{'text':f'word{i}', 'labels':[label], 'language':'en'} for i,label in enumerate(LABELS)]
    def run(name):
        seed_everything(conf['seed'])
        model=DistilBertForSequenceClassification(DistilBertConfig(vocab_size=len(vocab),dim=16,hidden_dim=24,n_layers=1,n_heads=2,max_position_embeddings=32,
            num_labels=10,problem_type='multi_label_classification',id2label=dict(enumerate(LABELS)),label2id={v:k for k,v in enumerate(LABELS)}))
        before=model.classifier.weight.detach().clone()
        history=fit(model,tokenizer,rows,rows,conf,tmp_path/name)
        assert not model.classifier.weight.detach().equal(before)
        assert history['test_evaluated'] is False
        checkpoint=tmp_path/name/f"epoch-{history['best_epoch']}"
        assert (checkpoint/'model.safetensors').exists()
        reloaded=DistilBertForSequenceClassification.from_pretrained(checkpoint,local_files_only=True)
        assert reloaded.config.inbox_nizer_max_length==32
        return history
    first=run('first'); second=run('second')
    assert first==second
    assert all(np.isfinite(e['train_loss']) and np.isfinite(e['validation_loss']) for e in first['epochs'])
