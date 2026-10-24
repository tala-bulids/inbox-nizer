# Sanitized portfolio screenshots

Captured on 24 October 2026 from the existing built frontend at code candidate
b3225fa, served by deploy/render_app.py on a local loopback address. No product
code, styles or layout were changed. Desktop capture is 1440 px wide; mobile is
390 px. Both Arabic RTL and English LTR views were visually reviewed.

- inbox-ar.png: Arabic inbox, three synthetic example.invalid messages.
- inbox-en.png: the same fixtures with English navigation.
- settings-mobile.png: synthetic connected demo@example.invalid account.

Browser API responses were mocked with runtime_profile=render-free. Search/Ask
links were checked absent; the capture had no browser page errors or horizontal
overflow. The local server rejected all database connections; the browser blocked
non-loopback requests. Labels, summaries, dates and connection state are fixtures,
not model predictions or evidence of a real Gmail connection. The original API
responses, model artifacts, credentials and backup are not part of these images.

This gallery documents the existing UI. Real hosted acceptance remains open in
PROJECT_STATUS.md. Do not present these images as screenshots of the live service.
