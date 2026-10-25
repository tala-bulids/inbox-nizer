"""Exercise the real same-origin wrapper with synthetic files and API data."""
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from deploy.render_app import create_app


@pytest.fixture
def hosted(tmp_path):
    dist = tmp_path / 'dist'
    dist.mkdir()
    (dist / 'assets').mkdir()
    (dist / 'index.html').write_text('<html>public SPA</html>')
    (dist / 'assets' / 'app.js').write_text('/* public asset */')
    (tmp_path / 'secret.txt').write_text('PRIVATE')
    api = FastAPI()

    @api.get('/probe')
    def probe(request: Request):
        return {'root_path': request.scope['root_path'], 'q': request.query_params.get('q')}

    return TestClient(create_app(api, dist))


def test_mounted_api_retains_prefix_query_and_private_cache_policy(hosted):
    response = hosted.get('/api/probe?q=synthetic')
    assert response.json() == {'root_path': '/api', 'q': 'synthetic'}
    assert response.headers['cache-control'] == 'no-store'
    assert hosted.get('/api/missing').status_code == 404
    assert hosted.get('/api', follow_redirects=False).headers['location'] == '/api/'


@pytest.mark.parametrize('path', ['/', '/settings', '/oauth/complete?result=success'])
def test_spa_deep_links_have_security_headers(hosted, path):
    response = hosted.get(path)
    assert response.status_code == 200 and 'public SPA' in response.text
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert "frame-ancestors 'none'" in response.headers['content-security-policy']
    assert response.headers['cache-control'] == 'no-store'


@pytest.mark.parametrize('path', ['/%2e%2e/secret.txt', '/.env', '/assets/missing.js'])
def test_private_paths_are_not_served(hosted, path):
    response = hosted.get(path)
    assert response.status_code == 404 and 'PRIVATE' not in response.text


def test_assets_and_missing_build(hosted, tmp_path):
    assert hosted.get('/assets/app.js').text == '/* public asset */'
    with pytest.raises(RuntimeError, match='Build the frontend'):
        create_app(FastAPI(), tmp_path)
