#!/usr/bin/env python3
"""A local crates.io relay: plain HTTP on 127.0.0.1 in front of the HTTPS registries.

The Windows Schannel stack on this machine cannot acquire TLS credentials inside the sandbox, so
cargo's own HTTP (libcurl + Schannel) fails on crates.io. Python's OpenSSL works, so this proxies
the sparse index and the crate downloads for cargo:

    https://index.crates.io/...            ->  http://127.0.0.1:PORT/index/...
    https://static.crates.io/crates/...    ->  http://127.0.0.1:PORT/crates/...

Everything is kept in --cache (prefetch-crates.py can fill it in parallel, which is a lot faster
than cargo's one-request-per-crate walk), and config.json is rewritten so its `dl` points back at
this server.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

INDEX = "https://index.crates.io"
STATIC = "https://static.crates.io"
UA = "cargo-relay/1.1"
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".relay-cache")


def index_path(name):
    """The sparse index's path for a crate name."""
    name = name.lower()
    if len(name) == 1:
        return f"1/{name}"
    if len(name) == 2:
        return f"2/{name}"
    if len(name) == 3:
        return f"3/{name[0]}/{name}"
    return f"{name[:2]}/{name[2:4]}/{name}"


def resolve(path):
    """(cache file, upstream URL) for a request path, or None."""
    if path.startswith("/index/"):
        rest = path[len("/index/"):]
        return os.path.join(CACHE, "index", rest), f"{INDEX}/{rest}"
    if path == "/config.json":
        return os.path.join(CACHE, "index", "config.json"), f"{INDEX}/config.json"
    if path.startswith("/crates/"):
        parts = path[len("/crates/"):].split("/")
        if len(parts) == 3 and parts[2] == "download":
            name, version = parts[0], parts[1]
            file = f"{name}-{version}.crate"
            return (os.path.join(CACHE, "crates", name, file),
                    f"{STATIC}/crates/{name}/{file}")
        if len(parts) == 2:
            return (os.path.join(CACHE, "crates", parts[0], parts[1]),
                    f"{STATIC}/crates/{parts[0]}/{parts[1]}")
    return None


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read(), r.status, r.headers.get("Content-Type", "application/octet-stream")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass

    def do_HEAD(self):
        self.proxy(head=True)

    def do_GET(self):
        self.proxy(head=False)

    def proxy(self, head):
        found = resolve(self.path.split("?")[0])
        if found is None:
            self.send_error(404)
            return
        file, url = found
        status, ctype = 200, None
        if file and os.path.isfile(file):
            with open(file, "rb") as f:
                body = f.read()
        else:
            try:
                body, status, ctype = fetch(url)
            except urllib.error.HTTPError as e:
                body, status = e.read(), e.code
                ctype = e.headers.get("Content-Type", "text/plain")
            except Exception as e:  # network hiccup: let cargo retry
                self.send_error(502, str(e))
                return
            if status == 200 and file:
                os.makedirs(os.path.dirname(file), exist_ok=True)
                tmp = file + ".part"
                with open(tmp, "wb") as f:
                    f.write(body)
                os.replace(tmp, file)
        if url.endswith("config.json") and status == 200:
            config = json.loads(body)
            config["dl"] = f"http://127.0.0.1:{self.server.server_port}/crates"
            body = json.dumps(config).encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if not head:
            self.wfile.write(body)


def main():
    global CACHE
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8899)
    parser.add_argument("--cache", default=CACHE)
    args = parser.parse_args()
    CACHE = args.cache
    os.makedirs(os.path.join(CACHE, "index"), exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"relay listening on http://127.0.0.1:{args.port}, cache {CACHE}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
