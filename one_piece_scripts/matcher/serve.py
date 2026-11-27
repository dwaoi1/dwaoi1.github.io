#!/usr/bin/env python3
"""Local manual price-matching tool.

Run:
    python one_piece_scripts/matcher/serve.py [--port 8777]

Reads  remap_out/queue.json + remap_out/mappings.json   (deterministic results)
Serves a local UI where you link official variant images to CardRush entries
by eye, and persists your decisions to manual_links.json (atomically).

No AI/vision inference happens here: images are shown, you decide.
"""

import argparse
import json
import os
import re
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
REPO = os.path.dirname(SCRIPTS)
QUEUE_PATH = os.path.join(SCRIPTS, 'remap_out', 'queue.json')
AUTO_PATH = os.path.join(SCRIPTS, 'remap_out', 'mappings.json')
STATE_PATH = os.path.join(SCRIPTS, 'manual_links.json')
OFFICIAL_DIR = os.path.join(REPO, 'one_piece_app', 'public', 'images', 'cards')
CR_CACHE = os.path.join(SCRIPTS, '.image_cache')

SAFE_NAME = re.compile(r'^[A-Za-z0-9_.-]+$')
_download_lock = threading.Lock()
DEFAULT_STATE = {'links': {}, 'resolved': []}


def atomic_write(path, data):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def load_json(path, default):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def validate_state(data):
    if not isinstance(data, dict):
        raise ValueError('state must be an object')
    links = data.get('links', {})
    resolved = data.get('resolved', [])
    if not isinstance(links, dict) or not isinstance(resolved, list):
        raise ValueError('links must be an object, resolved a list')
    if len(links) > 20000:
        raise ValueError('links too large')
    clean_links = {}
    for code, pats in links.items():
        if not isinstance(code, str) or not SAFE_NAME.match(code):
            raise ValueError(f'bad image code: {code!r}')
        if not isinstance(pats, list) or not all(isinstance(p, str) for p in pats):
            raise ValueError(f'bad patterns for {code}')
        if len(pats) > 200:
            raise ValueError(f'too many patterns for {code}')
        clean_links[code] = pats
    clean_resolved = []
    for r in resolved:
        if not isinstance(r, str) or not SAFE_NAME.match(r):
            raise ValueError(f'bad resolved code: {r!r}')
        if len(clean_resolved) < 5000:
            clean_resolved.append(r)
    return {'links': clean_links, 'resolved': clean_resolved}


def cardrush_image(url):
    img_id = re.sub(r'\D', '', os.path.basename(url.split('?')[0])) or 'x'
    dest = os.path.join(CR_CACHE, img_id + '.webp')
    if os.path.isfile(dest):
        return dest
    legacy = os.path.join(OFFICIAL_DIR, img_id + '.webp')
    if os.path.isfile(legacy):
        return legacy
    with _download_lock:
        if os.path.isfile(dest):
            return dest
        parsed = urllib.parse.urlparse(url)
        if parsed.netloc != 'files.cardrush.media':
            raise ValueError('unexpected image host')
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
        os.makedirs(CR_CACHE, exist_ok=True)
        with open(dest + '.tmp', 'wb') as f:
            f.write(data)
        os.replace(dest + '.tmp', dest)
        time.sleep(0.05)
        return dest


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path, ctype):
        try:
            with open(path, 'rb') as f:
                data = f.read()
        except OSError:
            self._send(404, b'not found', 'text/plain')
            return
        self._send(200, data, ctype)

    def _send_json(self, obj):
        self._send(200, json.dumps(obj, ensure_ascii=False).encode('utf-8'),
                   'application/json; charset=utf-8')

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        path = parsed.path

        if path in ('/', '/index.html'):
            self._send_file(os.path.join(HERE, 'index.html'), 'text/html; charset=utf-8')
        elif path == '/app.js':
            self._send_file(os.path.join(HERE, 'app.js'), 'application/javascript; charset=utf-8')
        elif path == '/styles.css':
            self._send_file(os.path.join(HERE, 'styles.css'), 'text/css; charset=utf-8')
        elif path == '/api/data':
            self._send_json({
                'queue': load_json(QUEUE_PATH, []),
                'auto': load_json(AUTO_PATH, {}),
            })
        elif path == '/api/state':
            self._send_json(load_json(STATE_PATH, DEFAULT_STATE))
        elif path.startswith('/img/o/'):
            name = os.path.basename(path[len('/img/o/'):])
            if not SAFE_NAME.match(name):
                self._send(400, b'bad name', 'text/plain')
                return
            self._send_file(os.path.join(OFFICIAL_DIR, name), 'image/png')
        elif path.startswith('/img/c/'):
            url = (qs.get('u') or [''])[0]
            if not url:
                self._send(400, b'missing u', 'text/plain')
                return
            try:
                fpath = cardrush_image(url)
            except Exception as exc:
                self._send(502, str(exc).encode('utf-8', 'replace'), 'text/plain')
                return
            self._send_file(fpath, 'image/webp')
        else:
            self._send(404, b'not found', 'text/plain')

    def do_POST(self):
        if urllib.parse.urlparse(self.path).path != '/api/state':
            self._send(404, b'not found', 'text/plain')
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length > 4_000_000:
                raise ValueError('body too large')
            raw = self.rfile.read(length)
            data = validate_state(json.loads(raw.decode('utf-8')))
            atomic_write(STATE_PATH, data)
        except (ValueError, json.JSONDecodeError) as exc:
            self._send(400, str(exc).encode('utf-8', 'replace'), 'text/plain')
            return
        self._send_json({'ok': True, 'links': len(data['links']),
                         'resolved': len(data['resolved'])})

    def log_message(self, fmt, *args):
        print(f'[matcher] {self.address_string()} {fmt % args}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8777)
    parser.add_argument('--host', default='127.0.0.1')
    args = parser.parse_args()
    if not os.path.isfile(QUEUE_PATH):
        raise SystemExit(f'ERROR: {QUEUE_PATH} not found - run remap_prices.py first')
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f'Manual matcher on http://{args.host}:{args.port}/  (Ctrl+C to stop)')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nstopped')


if __name__ == '__main__':
    main()
