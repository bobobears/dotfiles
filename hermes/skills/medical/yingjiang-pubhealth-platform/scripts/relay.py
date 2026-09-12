#!/usr/bin/env python3
"""Local relay: serves payload JS on 127.0.0.1:8899 (CORS *) and logs page POSTs to relay.log.
Run from a dir containing the q*.js payloads, e.g.: cd <dir> && python3 relay.py
"""
import http.server, os, datetime

class H(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()
    def do_POST(self):
        n = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(n).decode('utf-8', 'ignore')
        ts = datetime.datetime.now().strftime('%H:%M:%S')
        with open(os.path.join(os.getcwd(), 'relay.log'), 'a') as f:
            f.write('[%s] POST %s\n%s\n---END---\n' % (ts, self.path, body))
        self.send_response(204)
        self.end_headers()
    def log_message(self, *a):
        pass

http.server.HTTPServer(('127.0.0.1', 8899), H).serve_forever()
