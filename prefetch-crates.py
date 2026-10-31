#!/usr/bin/env python3
"""Fill the crates relay's cache from a Cargo.lock, in parallel.

Cargo walks the sparse index one crate at a time (about a second each through the relay), which is
minutes of waiting before the first line compiles. This reads the versions the lockfile pins and
fetches every index entry and .crate file up front, so cargo's walk is served from local disk.

    python prefetch-crates.py path/to/Cargo.lock [--jobs 32]
"""

import argparse
import hashlib
import os
import sys
import time
import tomllib
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

INDEX = "https://index.crates.io"
STATIC = "https://static.crates.io"
UA = "cargo-relay/1.1"
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".relay-cache")


def index_path(name):
    name = name.lower()
    if len(name) == 1:
        return f"1/{name}"
    if len(name) == 2:
        return f"2/{name}"
    if len(name) == 3:
        return f"3/{name[0]}/{name}"
    return f"{name[:2]}/{name[2:4]}/{name}"


def get(url, tries=4):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 - retried
            last = e
            time.sleep(1.0 * (attempt + 1))
    raise last


def write(path, body):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".part"
    with open(tmp, "wb") as f:
        f.write(body)
    os.replace(tmp, path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("lock")
    parser.add_argument("--jobs", type=int, default=32)
    parser.add_argument("--cache", default=CACHE)
    args = parser.parse_args()
    with open(args.lock, "rb") as f:
        lock = tomllib.load(f)
    packages = [p for p in lock.get("package", [])
                if str(p.get("source", "")).startswith("registry+")]

    jobs = []
    for name in sorted({p["name"].lower() for p in packages}):
        path = os.path.join(args.cache, "index", index_path(name))
        if not os.path.isfile(path):
            jobs.append(("index", path, f"{INDEX}/{index_path(name)}", None))
    for p in packages:
        name, version = p["name"].lower(), p["version"]
        path = os.path.join(args.cache, "crates", name, f"{name}-{version}.crate")
        if not os.path.isfile(path):
            jobs.append(("crate", path, f"{STATIC}/crates/{name}/{name}-{version}.crate",
                         p.get("checksum")))
    print(f"{len(packages)} packages pinned, {len(jobs)} files to fetch", flush=True)

    done = failed = 0
    started = time.time()
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(get, url): (path, checksum) for _, path, url, checksum in jobs}
        for future in as_completed(futures):
            path, checksum = futures[future]
            done += 1
            try:
                body = future.result()
                if checksum and hashlib.sha256(body).hexdigest() != checksum:
                    raise RuntimeError(f"sha256 mismatch for {os.path.basename(path)}")
                write(path, body)
            except Exception as e:  # noqa: BLE001 - reported, rest continue
                failed += 1
                print(f"  FAILED {os.path.basename(path)}: {e}", flush=True)
            if done % 100 == 0 or done == len(jobs):
                rate = done / max(time.time() - started, 0.001)
                print(f"  {done}/{len(jobs)}  {rate:.0f}/s  failed {failed}", flush=True)
    print(f"cached in {time.time() - started:.0f}s: {done - failed} files, {failed} failed",
          flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
