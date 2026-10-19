"""Opt-in browser test; conftest blocks production and rolls back all fixtures."""
import json,os,subprocess,threading
from http.server import BaseHTTPRequestHandler,HTTPServer
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from main import app
from test_relational_facts import indexed

@pytest.mark.skipif(os.getenv('RUN_ASK_BROWSER')!='1',reason='Opt-in real browser integration')
def test_real_clarification_click(test_database):
    for i,date in enumerate(('20-Nov-2027','21-Nov-2027')):
        indexed(test_database,f'Travel date: {date}\nDeparture time: 08:15',subject=f'Synthetic trip {i}',message_id=f'click-{i}')
    test_database.commit()
    with TestClient(app) as client:
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                response=client.post('/ask',json=body)
                self.send_response(response.status_code);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(response.content)
        server=HTTPServer(('127.0.0.1',0),Handler)
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        try:
            environment=dict(os.environ,ASK_TEST_BRIDGE=f'http://127.0.0.1:{server.server_port}/ask')
            result=subprocess.run(['node','scripts/check-ask-integration.mjs'],cwd=Path(__file__).parent/'frontend',env=environment,capture_output=True,text=True,encoding='utf-8',timeout=90)
            assert result.returncode==0,result.stdout+result.stderr
        finally:
            server.shutdown();server.server_close();worker.join()
