"""Cross-language aliases must not create itinerary facts or bypass scoping."""
from datetime import timedelta
import pytest
from entity_aliases import aliases, identities, matches
from rag_service import answer_email_question
from test_relational_facts import indexed
from test_rag_hybrid import SpyLLM


@pytest.mark.parametrize('first,second',[('Jeddah','جدة'),('Jeddah','جده'),('Muscat','مسقط'),
                                       ('Cairo','القاهرة'),('Doha','الدوحة'),('Dubai','دبي')])
def test_offline_generic_name_equivalence(first,second):
    assert matches(first,second)
    assert matches(second,first)


def test_unknown_ambiguous_and_codes_do_not_supply_a_place():
    assert not matches('Jeddah','مسقط')
    assert not matches('Unknown place','جدة')
    assert not matches('Springfield','Cairo')
    assert not matches('JED','جدة')
    assert not matches('Jeddah','جدة مسقط')
    assert matches('Birch','Birch')


@pytest.mark.parametrize('question', ['متى رحلتي لجدة؟','when is my flight to Jeddah?',
                                     'when am I travelling to Jeddah?','متى flight حقي لجدة؟'])
def test_same_record_itinerary_across_languages(test_database,question):
    email=indexed(test_database,'Travel date: 20-Nov-2027\nDestination: جدة\nDeparture time: 08:15\nArrival time: 10:25\nBooking reference: REF-39',subject='Travel')
    llm=SpyLLM();answer=answer_email_question(test_database,question,llm,min_score=0)
    assert answer['status']=='answered' and llm.calls==0
    assert answer['citations']==[{'email_id':email.id}]
    assert all(value in answer['answer'] for value in ('08:15','10:25','REF-39'))
    assert 'airport' not in answer['answer'].lower()


def test_two_same_city_trips_still_clarify(test_database):
    for i,date in enumerate(('20-Nov-2027','21-Nov-2027')):
        indexed(test_database,f'Travel date: {date}\nDestination: جدة',subject='Travel',message_id=f'city-{i}')
    result=answer_email_question(test_database,'when is my flight to Jeddah?',SpyLLM(),min_score=0)
    assert result['status']=='needs_clarification'


def test_city_in_subject_does_not_override_destination(test_database):
    indexed(test_database,'Travel date: 20-Nov-2027\nDestination: مسقط',subject='Jeddah offers')
    result=answer_email_question(test_database,'when is my flight to Jeddah?',SpyLLM(),min_score=0)
    assert result['status']=='insufficient_evidence'


def test_encoder_loader_is_local_only(monkeypatch):
    import sys
    from types import SimpleNamespace
    import embedding_service
    kwargs={}
    def create(*args,**options):
        kwargs.update(options);return SimpleNamespace()
    monkeypatch.setitem(sys.modules,'sentence_transformers',SimpleNamespace(SentenceTransformer=create))
    # conftest replaces this function; call the original source module in isolation.
    import importlib.util
    spec=importlib.util.spec_from_file_location('offline_embedding_test',embedding_service.__file__)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assert module._load_encoder().max_seq_length==512
    assert kwargs['local_files_only'] is True
