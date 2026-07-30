from __future__ import annotations
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from storycraft.ollama import generate


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/v1/models/"):
            # Return model info with context_length
            data = json.dumps({"context_length": 8192}).encode()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        self.server.body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        data = json.dumps({"choices": [{"message": {"content": json.dumps({"schema_version": 1})}}]}).encode()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


class OllamaV2Tests(unittest.TestCase):
    def test_posts_non_streaming_schema_and_parses_object(self):
        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()
        try:
            self.assertEqual(generate(f"http://127.0.0.1:{server.server_port}", "m", "p", {"type": "object"}), {"schema_version": 1})
            self.assertEqual(server.body["messages"], [{"role": "user", "content": "p"}])
            self.assertEqual(server.body["response_format"]["json_schema"]["schema"], {"type": "object"})
            self.assertTrue(server.body["think"])
            self.assertEqual(server.body["options"]["num_ctx"], 8192)
        finally:
            server.shutdown()
            server.server_close()