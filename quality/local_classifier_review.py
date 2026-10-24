r"""Standalone loopback-only human review. No database, model or product imports.

Run: .\env\Scripts\python.exe -m quality.local_classifier_review
Only development.csv is accepted. The holdout is never opened.
"""
import argparse
from contextlib import contextmanager
import csv
import errno
import hashlib
import io
import json
import os
import re
import secrets
import tempfile
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from classifier_contract import LABELS

DEFAULT_CSV = Path(__file__).resolve().parents[1] / 'private_review/development.csv'
STATE_DIR = Path(__file__).resolve().parents[1] / 'private_review/classifier-ui'
REVIEW_FIELDS = ['gold_label', 'ambiguous', 'reviewer', 'label_source', 'reviewed_at']


def read_development(path):
    if path.name != 'development.csv' or path.resolve().name != 'development.csv':
        raise ValueError('Only development.csv is accepted.')
    raw = path.read_bytes()
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig'), newline=''))
    rows = list(reader)
    fields = reader.fieldnames or []
    if not {'email_id', 'subject', 'sender', 'date', 'body'} <= set(fields):
        raise ValueError('Development export is missing required columns.')
    ids = [row['email_id'] for row in rows]
    if len(set(ids)) != len(ids) or any(not identity for identity in ids):
        raise ValueError('Development email IDs must be unique and nonempty.')
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError('Malformed development CSV; no changes made.')
    return raw, fields, rows


def signals(row, metadata):
    text = (row['subject'] + '\n' + row['body']).lower()
    patterns = {
        'finance': r'\b(invoice|payment|receipt|balance|charged|billing|bank|finance)\b|فاتور|دفع|رصيد|بنك|مالي',
        'business': r'\b(business|professional|networking|company|meeting|project|partnership)\b|اجتماع|مشروع|شرك|أعمال|مهني',
        'job': r'\b(application|applicant|interview|hiring|recruit|career|vacancy|resume)\b|وظيف|توظيف|مقابل|سيرتك|طلبك',
        'newsletter': r'\b(newsletter|digest|weekly|edition|roundup|unsubscribe)\b|نشرة|أسبوع|اخبار|أخبار',
        'promotion': r'\b(discount|sale|offer|deal|coupon|save|promo)\b|خصم|عرض|عروض|تسوق',
    }
    hits = {key: bool(re.search(pattern, text)) for key, pattern in patterns.items()}
    baseline = metadata.get('baseline', '')
    finance_business = ((baseline == 'Finance & Bills' and hits['business'])
                        or (baseline == 'Business' and hits['finance'])
                        or (hits['finance'] and hits['business']))
    business_job = ((baseline == 'Business' and hits['job'])
                    or (baseline == 'Job Application' and hits['business'])
                    or (hits['job'] and hits['business']))
    news_promo = ((baseline == 'Newsletters' and hits['promotion'])
                  or (baseline == 'Promotions' and hits['newsletter'])
                  or (hits['newsletter'] and hits['promotion']))
    ar = len(re.findall(r'[\u0600-\u06ff]', text))
    en = len(re.findall(r'[a-zA-Z]', text))
    bilingual = ar >= 20 and en >= 20
    mismatch = (finance_business or business_job or news_promo)
    confident = float(metadata.get('confidence') or 0) >= .8 and mismatch
    buckets = [finance_business, business_job, news_promo, confident, bilingual]
    score = 4 * sum(buckets[:3]) + 5 * confident + 3 * bilingual + (ar >= 20)
    return score, buckets


def prioritize(rows, metadata, limit=50):
    scored = [(row['email_id'], *signals(row, metadata.get(row['email_id'], {}))) for row in rows]
    scored.sort(key=lambda item: (-item[1], item[0]))
    selected = []
    # Interleave the five priorities rather than letting one large group dominate.
    pools = [[identity for identity, _, buckets in scored if buckets[i]] for i in range(5)]
    while len(selected) < min(limit, len(rows)):
        before = len(selected)
        for pool in pools:
            while pool and pool[0] in selected:
                pool.pop(0)
            if pool and len(selected) < limit:
                selected.append(pool.pop(0))
        if len(selected) == before:
            selected.extend(identity for identity, _, _ in scored if identity not in selected)
            selected = selected[:limit]
            break
    return selected


def reviewed(row):
    return (row.get('label_source') == 'human_reviewed' and bool(row.get('reviewer', '').strip())
            and bool(row.get('reviewed_at'))
            and (row.get('gold_label') in LABELS or row.get('ambiguous') == 'yes'))


def atomic_write(path, content):
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class ReviewAlreadyRunning(RuntimeError):
    pass


def review_state_path(path, state_dir):
    key = hashlib.sha256(str(Path(path).absolute()).encode()).hexdigest()[:16]
    return state_dir / (key + '.json')


@contextmanager
def review_process_lock(path):
    """Acquire byte zero before any I/O; Windows byte locks also deny reads.

    Windows can lock a range beyond EOF, so a fresh empty file needs no
    initialization. Never truncate or unlink this file: all processes must
    contend on the same file and byte. Closing the handle releases the lock,
    including when startup or serving raises.
    """
    with path.open('a+b', buffering=0) as lock:
        lock.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            if error.errno in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                raise ReviewAlreadyRunning(
                    'A review server is already running for this development file. '
                    'Use its existing local URL, or stop it with Ctrl+C before restarting.'
                ) from error
            raise
        yield


class Review:
    def __init__(self, path, state_dir=STATE_DIR):
        self.path = Path(path).absolute()
        raw, _, rows = read_development(self.path)
        ids = {row['email_id'] for row in rows}
        self.metadata = {}
        manifest = self.path.parent / 'manifest.json'
        if manifest.is_file():
            items = json.loads(manifest.read_text(encoding='utf-8-sig'))
            self.metadata = {str(item['email_id']): item for item in items
                             if str(item.get('email_id')) in ids and item.get('split') == 'development'}
        state_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = review_state_path(self.path, state_dir)
        if self.state_path.exists():
            self.state = json.loads(self.state_path.read_text(encoding='utf-8'))
            if not set(self.state['queue']) <= ids:
                raise ValueError('Development IDs changed; retained queue requires inspection.')
        else:
            queue = prioritize(rows, self.metadata)
            cursor = next((i for i, identity in enumerate(queue)
                           if not reviewed(next(row for row in rows if row['email_id'] == identity))), len(queue))
            self.state = {'queue': queue, 'cursor': cursor, 'skipped': []}
            self.persist()

    def persist(self):
        atomic_write(self.state_path, (json.dumps(self.state, indent=2) + '\n').encode())

    def snapshot(self):
        raw, _, rows = read_development(self.path)
        by_id = {row['email_id']: row for row in rows}
        queue = self.state['queue']
        cursor = self.state['cursor']
        row = by_id[queue[cursor]] if cursor < len(queue) else None
        return {'row': ({key: row.get(key, '') for key in ['email_id', 'subject', 'sender', 'date', 'body'] + REVIEW_FIELDS}
                        if row else None), 'cursor': cursor, 'queued': len(queue),
                'completed': sum(reviewed(by_id[identity]) for identity in queue),
                'skipped': sum(identity in self.state['skipped'] and not reviewed(by_id[identity]) for identity in queue),
                'total': len(rows), 'revision': hashlib.sha256(raw).hexdigest(), 'labels': LABELS}

    def action(self, data):
        current = self.snapshot()
        if data.get('revision') != current['revision'] or data.get('cursor') != current['cursor']:
            raise ValueError('File or position changed. Reload before reviewing again.')
        action = data.get('action')
        if action in {'label', 'ambiguous'}:
            reviewer = str(data.get('reviewer', '')).strip()
            label = data.get('label', '')
            if not reviewer or len(reviewer) > 120 or any(c in reviewer for c in '\r\n'):
                raise ValueError('Enter your reviewer name first (up to 120 characters).')
            if action == 'label' and label not in LABELS:
                raise ValueError('Choose one of the ten labels.')
            if not current['row']:
                raise ValueError('No email selected.')
            raw, fields, rows = read_development(self.path)
            if hashlib.sha256(raw).hexdigest() != current['revision']:
                raise ValueError('CSV changed. Reload before saving.')
            identity = current['row']['email_id']
            row = next(row for row in rows if row['email_id'] == identity)
            row.update(gold_label=label if action == 'label' else '',
                       ambiguous='no' if action == 'label' else 'yes', reviewer=reviewer,
                       label_source='human_reviewed', reviewed_at=datetime.now(timezone.utc).date().isoformat())
            fields += [key for key in REVIEW_FIELDS if key not in fields]
            output = io.StringIO(newline='')
            writer = csv.DictWriter(output, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
            backup = self.path.with_name('development.before-local-review.csv.backup')
            if not backup.exists():
                with backup.open('xb') as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
            atomic_write(self.path, output.getvalue().encode('utf-8-sig'))
            self.state['skipped'] = [item for item in self.state['skipped'] if item != identity]
            self.state['cursor'] += 1
        elif action == 'skip':
            if current['row']:
                identity = current['row']['email_id']
                if identity not in self.state['skipped']:
                    self.state['skipped'].append(identity)
                self.state['cursor'] += 1
        elif action == 'previous':
            self.state['cursor'] = max(0, self.state['cursor'] - 1)
        elif action == 'remaining':
            _, _, rows = read_development(self.path)
            done = {row['email_id'] for row in rows if reviewed(row)}
            self.state['cursor'] = next((i for i, identity in enumerate(self.state['queue']) if identity not in done), len(self.state['queue']))
        else:
            raise ValueError('Unknown action.')
        self.persist()
        return self.snapshot()


def make_server(review, port=8765):
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass  # Never log requests, mailbox text or reviewer identity.

        def reply(self, status, body, content_type='application/json'):
            payload = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
            self.end_headers()
            self.wfile.write(payload)

        def allowed(self):
            authority = f'127.0.0.1:{self.server.server_port}'
            if self.headers.get('Host') != authority:
                self.reply(403, {'error': 'Local access only.'})
                return False
            origin = self.headers.get('Origin')
            if origin and origin != 'http://' + authority:
                self.reply(403, {'error': 'Local access only.'})
                return False
            return True

        def authorized(self):
            if not secrets.compare_digest(self.headers.get('X-Review-Token', ''), token):
                self.reply(403, {'error': 'Open the private URL printed by the local review command.'})
                return False
            return True

        def do_GET(self):
            if not self.allowed():
                return
            path = urlsplit(self.path).path
            assets = {'/': ('review.html', 'text/html; charset=utf-8'),
                      '/review.js': ('review.js', 'text/javascript; charset=utf-8'),
                      '/review.css': ('review.css', 'text/css; charset=utf-8')}
            if path in assets:
                name, mime = assets[path]
                self.reply(200, (Path(__file__).parent / 'local_review_ui' / name).read_bytes(), mime)
            elif path == '/state' and self.authorized():
                try:
                    self.reply(200, review.snapshot())
                except Exception:
                    self.reply(500, {'error': 'Cannot read development.csv. Check the file and restart.'})
            elif path != '/state':
                self.reply(404, {'error': 'Not found.'})

        def do_POST(self):
            if not self.allowed() or not self.authorized():
                return
            if self.path != '/action':
                self.reply(404, {'error': 'Not found.'})
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 4096:
                    raise ValueError('Invalid request size.')
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError('Invalid request.')
                self.reply(200, review.action(data))
            except (ValueError, TypeError):
                self.reply(409, {'error': 'Could not save: check reviewer name and reload if the CSV or position changed.'})
            except OSError:
                self.reply(500, {'error': 'Could not finish saving. Close CSV editors, check file permissions, then reload to verify progress.'})

    server = HTTPServer(('127.0.0.1', port), Handler)
    server.timeout = 2
    return server, token


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, default=DEFAULT_CSV)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--check', action='store_true', help='Prepare queue and print counts only; do not serve or edit CSV.')
    args = parser.parse_args()
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        # Acquire before loading or creating progress, not just before serving.
        with review_process_lock(review_state_path(args.csv, STATE_DIR).with_suffix('.lock')):
            review = Review(args.csv, STATE_DIR)
            snapshot = review.snapshot()
            print(f"Queued {snapshot['queued']} of {snapshot['total']} development emails; {snapshot['completed']} reviewed.", flush=True)
            if args.check:
                return
            server, token = make_server(review, args.port)
            print(f'Open locally: http://127.0.0.1:{server.server_port}/#{token}', flush=True)
            print('Enter your reviewer name. Each label or Ambiguous saves immediately. Ctrl+C stops.', flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
    except ReviewAlreadyRunning as error:
        parser.exit(2, f'{error}\n')


if __name__ == '__main__':
    main()
