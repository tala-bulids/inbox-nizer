"""Mandatory ORM ownership boundary for request sessions.

Maintenance sessions are privileged. Never inject them into API routes.
"""
from sqlalchemy import event, inspect, select
from sqlalchemy.orm import Session, with_loader_criteria
from sqlalchemy.sql.elements import TextClause
from sqlalchemy.sql.schema import Column, Table
from sqlalchemy.sql.selectable import Select
from sqlalchemy.sql.visitors import iterate


class OwnershipError(RuntimeError):
    pass


class OwnedSession(Session):
    def __init__(self, *args, user_id, **kwargs):
        if not isinstance(user_id, int) or user_id <= 0:
            raise OwnershipError('An authenticated principal is required')
        self.__user_id = user_id
        super().__init__(*args, **kwargs)

    @property
    def user_id(self):
        return self.__user_id


def rules(user_id):
    from models import Email, EmailPrediction, EmailTask, EmailEmbeddingChunk, EmailFact, EmailFactState
    from backend_models import GmailAccount, OAuthCredential, ProcessingState, GmailSyncState
    accounts = GmailAccount.__table__
    emails = Email.__table__
    owned_accounts = select(accounts.c.id).where(accounts.c.user_id == user_id)
    owned_emails = select(emails.c.id).where(emails.c.account_id.in_(owned_accounts))
    return {
        GmailAccount: GmailAccount.user_id == user_id,
        OAuthCredential: OAuthCredential.account_id.in_(owned_accounts),
        GmailSyncState: GmailSyncState.account_id.in_(owned_accounts),
        Email: Email.account_id.in_(owned_accounts),
        **{model: model.email_id.in_(owned_emails) for model in
           (EmailPrediction, EmailTask, EmailEmbeddingChunk, EmailFact, EmailFactState, ProcessingState)},
    }


_SAFE_SQL = {
    "SELECT set_config('hnsw.iterative_scan', 'strict_order', true)",
    "SELECT set_config('hnsw.ef_search', :size, true)",
    "SELECT to_regclass('email_facts') IS NOT NULL AND to_regclass('email_fact_states') IS NOT NULL",
    'SELECT pg_try_advisory_xact_lock(724193, :account)',
}


@event.listens_for(OwnedSession, 'do_orm_execute')
def scope_queries(state):
    if isinstance(state.statement, TextClause):
        if state.statement.text not in _SAFE_SQL:
            raise OwnershipError('Raw SQL is not allowed in request sessions')
        return
    if not state.is_orm_statement or not state.is_select:
        raise OwnershipError('Use scoped ORM objects for reads and writes')
    mapped_tables = {mapper.local_table for mapper in state.all_mappers}
    # Mixing Core columns into an ORM SELECT must not bypass loader criteria.
    for node in iterate(state.statement):
        if isinstance(node, TextClause):
            raise OwnershipError('Embedded raw SQL is not allowed in request sessions')
        if (not state.is_relationship_load and not state.is_column_load
                and isinstance(node, Column) and not node._annotations.get('parentmapper')
                and not (node.primary_key and node.table in mapped_tables)):
            raise OwnershipError('Use mapped columns in request queries')
        if isinstance(node, Select) and any(isinstance(c, Table) and not c._annotations.get('parentmapper')
                                          for c in node._raw_columns):
            raise OwnershipError('Use mapped entities in request queries')
    scope = rules(state.session.user_id)
    if any(mapper.class_ not in scope for mapper in state.all_mappers):
        raise OwnershipError('Model is outside the request boundary')
    for model, criterion in scope.items():
        state.statement = state.statement.options(with_loader_criteria(
            model, criterion, include_aliases=True, propagate_to_loaders=False))


@event.listens_for(OwnedSession, 'before_flush')
def scope_writes(db, context, instances):
    from models import Email
    from backend_models import GmailAccount, OAuthCredential, GmailSyncState
    scope = rules(db.user_id)
    for obj in list(db.new) + list(db.dirty) + list(db.deleted):
        model = type(obj)
        if model not in scope:
            raise OwnershipError('Model is outside the request boundary')
        field = 'user_id' if model is GmailAccount else 'account_id' if model in (Email, OAuthCredential, GmailSyncState) else 'email_id'
        state = inspect(obj)
        if state.persistent and state.attrs[field].history.has_changes():
            raise OwnershipError('Ownership cannot be reassigned by requests')
        if model is GmailAccount:
            allowed = obj.user_id == db.user_id
        else:
            parent = GmailAccount if field == 'account_id' else Email
            key = getattr(obj, field)
            if key is None and field == 'email_id' and getattr(obj, 'email', None) is not None:
                key = obj.email.id
            allowed = key is not None and db.scalar(select(parent.id).where(parent.id == key)) is not None
        if not allowed:
            raise OwnershipError('Referenced parent is not owned by this user')
