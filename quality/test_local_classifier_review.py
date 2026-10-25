"""Synthetic files only; run with unittest, without product/DB fixtures."""
import csv
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from quality.local_classifier_review import (
    Review, LABELS, main, make_server, prioritize, read_development,
    review_process_lock, review_state_path,
)


class ReviewProcessLockTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.lock_path = self.root / 'review.lock'

    def contender(self):
        # A real second interpreter exercises Windows mandatory byte locks.
        script = '''
import sys
from pathlib import Path
from quality.local_classifier_review import ReviewAlreadyRunning, review_process_lock
try:
    with review_process_lock(Path(sys.argv[1])):
        print('acquired')
except ReviewAlreadyRunning:
    print('already running')
    sys.exit(23)
'''
        return subprocess.run([sys.executable, '-c', script, str(self.lock_path)],
                              capture_output=True, text=True, timeout=15,
                              cwd=Path(__file__).resolve().parents[1])

    def test_empty_and_existing_file_exclude_other_process_then_release(self):
        for content in (b'', b'0existing marker'):
            with self.subTest(content=content):
                self.lock_path.write_bytes(content)
                with review_process_lock(self.lock_path):
                    blocked = self.contender()
                    self.assertEqual(blocked.returncode, 23, blocked.stderr)
                    self.assertEqual(blocked.stdout.strip(), 'already running')
                    self.assertEqual(blocked.stderr, '')
                acquired = self.contender()
                self.assertEqual(acquired.returncode, 0, acquired.stderr)
                self.assertEqual(acquired.stdout.strip(), 'acquired')
                self.assertEqual(self.lock_path.read_bytes(), content)

    def test_new_file_and_exception_release_lock(self):
        with self.assertRaisesRegex(RuntimeError, 'startup failed'):
            with review_process_lock(self.lock_path):
                raise RuntimeError('startup failed')
        acquired = self.contender()
        self.assertEqual(acquired.returncode, 0, acquired.stderr)
        self.assertEqual(self.lock_path.read_bytes(), b'')

    def test_busy_cli_exits_cleanly_before_loading_csv_or_progress(self):
        development = self.root / 'development.csv'
        lock_path = review_state_path(development, self.root).with_suffix('.lock')
        with review_process_lock(lock_path), patch('quality.local_classifier_review.STATE_DIR', self.root), \
                patch('quality.local_classifier_review.Review') as review, \
                patch.object(sys, 'argv', ['review', '--csv', str(development)]), \
                patch('sys.stderr', new_callable=io.StringIO) as stderr:
            with self.assertRaises(SystemExit) as caught:
                main()
            self.assertEqual(caught.exception.code, 2)
            self.assertIn('already running', stderr.getvalue())
            review.assert_not_called()


class LocalReviewTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.path = self.root / 'development.csv'
        self.fields = ['email_id', 'subject', 'sender', 'date', 'body', 'gold_label', 'ambiguous', 'reviewer', 'notes']
        self.rows = [dict(zip(self.fields, [str(i), 'Synthetic subject', 'test@example.invalid', '2026-10-17',
                                          'Invoice and business project\nمرحبا هذا بريد للاختبار فقط', '', '', '', 'Preserve notes'])) for i in range(60)]
        with self.path.open('w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=self.fields)
            writer.writeheader()
            writer.writerows(self.rows)
        self.original = self.path.read_bytes()
        # A directory with this name ensures any attempt to read holdout.csv fails.
        (self.root / 'holdout.csv').mkdir()
        self.review = Review(self.path, self.root / 'state')

    def action(self, kind, **kwargs):
        snapshot = self.review.snapshot()
        return self.review.action(dict(action=kind, cursor=snapshot['cursor'], revision=snapshot['revision'], **kwargs))

    def test_startup_does_not_edit_csv_and_queue_is_stable(self):
        self.assertEqual(self.path.read_bytes(), self.original)
        self.assertEqual(self.review.snapshot()['queued'], 50)
        self.assertEqual(len(set(self.review.state['queue'])), 50)
        again = Review(self.path, self.root / 'state')
        self.assertEqual(again.state, self.review.state)
        with self.assertRaises(ValueError):
            read_development(self.root / 'holdout.csv')

    def test_save_preserves_original_fields_and_all_other_rows(self):
        identity = self.review.snapshot()['row']['email_id']
        saved = self.action('label', label='Business', reviewer='Synthetic reviewer')
        self.assertEqual(saved['completed'], 1)
        _, fields, rows = read_development(self.path)
        self.assertIn('reviewed_at', fields)
        for before, after in zip(self.rows, rows):
            for key in ['email_id', 'subject', 'sender', 'date', 'body', 'notes']:
                self.assertEqual(before[key], after[key])
            if after['email_id'] != identity:
                self.assertEqual({key: after[key] for key in before}, before)
            else:
                self.assertEqual(after['gold_label'], 'Business')
                self.assertEqual(after['ambiguous'], 'no')
                self.assertEqual(after['label_source'], 'human_reviewed')
                self.assertEqual(after['reviewer'], 'Synthetic reviewer')
                self.assertRegex(after['reviewed_at'], r'^\d{4}-\d{2}-\d{2}$')
        self.assertEqual((self.root / 'development.before-local-review.csv.backup').read_bytes(), self.original)

    def test_previous_correction_ambiguous_skip_and_resume(self):
        self.action('label', label='Finance & Bills', reviewer='Synthetic reviewer')
        self.action('previous')
        self.assertEqual(self.review.snapshot()['row']['gold_label'], 'Finance & Bills')
        self.action('ambiguous', reviewer='Synthetic reviewer')
        self.action('previous')
        self.assertEqual(self.review.snapshot()['row']['gold_label'], '')
        self.assertEqual(self.review.snapshot()['row']['ambiguous'], 'yes')
        before = self.path.read_bytes()
        self.action('skip')
        self.action('skip')
        self.assertEqual(self.path.read_bytes(), before)
        again = Review(self.path, self.root / 'state')
        self.assertEqual(again.snapshot()['cursor'], 2)
        self.assertEqual(again.snapshot()['skipped'], 1)
        self.assertEqual(again.snapshot()['completed'], 1)
        self.action('remaining')
        self.assertEqual(self.review.snapshot()['cursor'], 1)

    def test_stale_request_and_missing_reviewer_do_not_write(self):
        old = self.review.snapshot()
        with self.assertRaises(ValueError):
            self.action('label', label='Business', reviewer='')
        self.assertEqual(self.path.read_bytes(), self.original)
        self.action('skip')
        with self.assertRaises(ValueError):
            self.review.action(dict(action='label', label='Business', reviewer='Test', cursor=old['cursor'], revision=old['revision']))
        self.assertEqual(self.path.read_bytes(), self.original)
        current = self.review.snapshot()
        self.path.write_bytes(self.original + b'\r\n')
        with self.assertRaises(ValueError):
            self.review.action(dict(action='label', label='Business', reviewer='Test', cursor=current['cursor'], revision=current['revision']))

    def test_failed_replace_preserves_csv(self):
        with patch('quality.local_classifier_review.os.replace', side_effect=PermissionError('locked')):
            with self.assertRaises(PermissionError):
                self.action('label', label='Business', reviewer='Synthetic reviewer')
        self.assertEqual(self.path.read_bytes(), self.original)
        self.assertEqual(self.review.snapshot()['cursor'], 0)

    def test_priority_is_deterministic_and_includes_competing_categories(self):
        rows = [dict(row, body='Simple personal note') for row in self.rows]
        rows[-1]['body'] = 'Application interview professional company'
        rows[-2]['body'] = 'Weekly newsletter discount sale'
        metadata = {rows[-1]['email_id']: {'baseline': 'Business', 'confidence': .99}}
        queue = prioritize(rows, metadata)
        self.assertIn(rows[-1]['email_id'], queue[:5])
        self.assertIn(rows[-2]['email_id'], queue[:5])
        self.assertEqual(queue, prioritize(list(reversed(rows)), metadata))

    def test_http_requires_token_and_rejects_foreign_origin_and_host(self):
        server, token = make_server(self.review, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        base = f'http://127.0.0.1:{server.server_port}'
        for headers in ({}, {'X-Review-Token': token, 'Origin': 'https://external.invalid'},
                        {'X-Review-Token': token, 'Host': 'external.invalid'}):
            with self.assertRaises(HTTPError) as caught:
                urlopen(Request(base + '/state', headers=headers))
            self.assertEqual(caught.exception.code, 403)
        with urlopen(Request(base + '/state', headers={'X-Review-Token': token})) as response:
            self.assertEqual(response.headers['Cache-Control'], 'no-store')
            data = json.load(response)
            self.assertEqual(data['labels'], LABELS)
            self.assertNotIn('baseline', data['row'])
        with urlopen(base + '/') as response:
            self.assertNotIn('Synthetic subject', response.read().decode())
            self.assertIn("frame-ancestors 'none'", response.headers['Content-Security-Policy'])

    @unittest.skipUnless(os.environ.get('LOCAL_REVIEW_BROWSER_TEST') == '1', 'Opt-in synthetic browser check')
    def test_browser(self):
        server, token = make_server(self.review, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        url = f'http://127.0.0.1:{server.server_port}/#{token}'
        subprocess.run(['node', str(Path(__file__).with_name('check_local_review_browser.mjs')), url], check=True, timeout=90)


if __name__ == '__main__':
    unittest.main()
