"""Dry-run by default. --apply writes facts only, committing per email."""
import argparse
import json
from sqlalchemy import text
from database import SessionLocal
from fact_store import backfill_facts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--batch-size', type=int, default=100)
    args = parser.parse_args(argv)
    with SessionLocal() as db:
        if not args.apply:
            db.execute(text('SET TRANSACTION READ ONLY'))
        totals = backfill_facts(db, batch_size=args.batch_size, force=args.force, apply=args.apply,
                               progress=lambda email_id, counts: print(json.dumps(dict(email_id=email_id, **counts))))
    print(json.dumps(dict(mode='apply' if args.apply else 'dry_run', **totals)))
    return totals


if __name__ == '__main__':
    main()
