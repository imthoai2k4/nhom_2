"""Serve the standalone SPA while preserving its /static asset paths."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)


class FrontendHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        if path.split("?", 1)[0] == "/":
            path = "/static/index.html"
        return super().translate_path(path)


if __name__ == "__main__":
    print("UtilityAI frontend: http://localhost:5500")
    ThreadingHTTPServer(("0.0.0.0", 5500), FrontendHandler).serve_forever()
