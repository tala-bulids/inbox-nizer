"""Operator-only commands. Never called by HTTP routes."""
import argparse
from sqlalchemy import select, update
from database import SessionLocal
from backend_models import AppUser, AccessToken, GmailAccount, OAuthCredential
from models import Email
from authentication import issue_token
from backend_config import encrypt, decrypt


def claim_legacy(db, account_id):
    target = db.scalar(select(GmailAccount).where(GmailAccount.id == account_id).with_for_update())
    if target is None or target.status != 'connected' or not target.address:
        raise ValueError('First connect and verify the target Gmail account through OAuth')
    source = db.scalar(select(GmailAccount).where(GmailAccount.status == 'quarantine').with_for_update())
    if source is None:
        raise ValueError('No quarantined account exists')
    duplicates = db.scalar(select(Email.id).where(Email.account_id == target.id,
        Email.message_id.in_(select(Email.message_id).where(Email.account_id == source.id))).limit(1))
    if duplicates is not None:
        raise ValueError('Conflicting synced messages: resolve duplicates explicitly before claiming')
    result = db.execute(update(Email).where(Email.account_id == source.id).values(account_id=target.id))
    return result.rowcount


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    create = sub.add_parser('create-user')
    create.add_argument('--name', required=True)
    create.add_argument('--days', type=int, default=7)
    token = sub.add_parser('issue-token')
    token.add_argument('--user-id', type=int, required=True)
    token.add_argument('--days', type=int, default=7)
    revoke = sub.add_parser('revoke-tokens')
    revoke.add_argument('--user-id', type=int, required=True)
    remove = sub.add_parser('delete-user')
    remove.add_argument('--user-id', type=int, required=True)
    remove.add_argument('--confirm-delete', action='store_true', required=True)
    claim = sub.add_parser('claim-legacy')
    claim.add_argument('--account-id', type=int, required=True)
    claim.add_argument('--confirm-ownership', action='store_true', required=True)
    sub.add_parser('rotate-encryption')
    args = parser.parse_args()
    with SessionLocal() as db:
        if args.command in ('create-user', 'issue-token'):
            user = AppUser(name=args.name, active=True) if args.command == 'create-user' else db.get(AppUser, args.user_id)
            if user is None:
                parser.error('User not found')
            db.add(user)
            db.flush()
            secret = issue_token(db, user, days=args.days)
            db.commit()
            print('User ID:', user.id)
            print('Store this bearer token securely; it is shown only once:', secret)
        elif args.command == 'revoke-tokens':
            for row in db.scalars(select(AccessToken).where(AccessToken.user_id == args.user_id)):
                db.delete(row)
            db.commit()
            print('Tokens revoked')
        elif args.command == 'delete-user':
            user = db.get(AppUser, args.user_id)
            if user is None or user.name == 'legacy-quarantine':
                parser.error('User not found or protected legacy owner')
            db.delete(user)
            db.commit()
            print('User and account data deleted')
        elif args.command == 'claim-legacy':
            count = claim_legacy(db, args.account_id)
            db.commit()
            print('Legacy emails linked:', count)
        else:
            for row in db.scalars(select(OAuthCredential)):
                row.ciphertext = encrypt(decrypt(row.ciphertext))
            db.commit()
            print('Stored credentials rotated; keep old keys until OAuth attempts expire')


if __name__ == '__main__':
    main()
