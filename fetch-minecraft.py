#!/usr/bin/env python3
"""Fetch Minecraft: Java Edition 26.3 from Mojang's public CDN into a launcher-style folder.

The files Mojang serves for a version (the client jar, the libraries, the asset index and the
asset objects, plus the server jar) are public and need no account: only the launchers gate them
behind one. This lays them out the way horizon-prepare expects to find a launcher's copy:

    <dir>/versions/<version>/<version>.json
    <dir>/versions/<version>/<version>.jar
    <dir>/libraries/<artifact path>          (as the version JSON lists them)
    <dir>/assets/indexes/<asset id>.json
    <dir>/assets/objects/<xx>/<hash>
    <dir>/server.jar                          (for horizon-prepare --server-jar)

Every file is checked against the sha1 and size Mojang lists, so a partial run resumes.
"""

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

MANIFEST = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
RESOURCES = "https://resources.download.minecraft.net"
UA = "horizon-offline-fetch/1.0"


def log(line):
    print(line, flush=True)


def get_bytes(url, tries=5):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"{url}: {last}")


def sha1_file(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def ok(path, digest, size=None):
    if not os.path.isfile(path):
        return False
    if size is not None and os.path.getsize(path) != size:
        return False
    if digest is None:
        return True
    return sha1_file(path) == digest


def place(destination, data, digest, size=None):
    """Write data at destination atomically, only when it does not already match."""
    if ok(destination, digest, size):
        return "kept"
    os.makedirs(os.path.dirname(destination) or ".", exist_ok=True)
    tmp = destination + ".part"
    with open(tmp, "wb") as f:
        f.write(data)
    got = sha1_file(tmp)
    if digest and got != digest:
        os.unlink(tmp)
        raise RuntimeError(f"{destination}: sha1 {got}, Mojang lists {digest}")
    os.replace(tmp, destination)
    return "got"


def fetch_file(url, destination, digest, size=None):
    if ok(destination, digest, size):
        return "kept"
    data = get_bytes(url)
    return place(destination, data, digest, size)


def version_json(version, cache_dir):
    manifest = json.loads(get_bytes(MANIFEST))
    entry = next((v for v in manifest["versions"] if v["id"] == version), None)
    if entry is None:
        raise SystemExit(f"Minecraft {version} is not in Mojang's version manifest")
    raw = get_bytes(entry["url"])
    got = hashlib.sha1(raw).hexdigest()
    if got != entry["sha1"]:
        raise SystemExit(f"version JSON sha1 {got}, Mojang lists {entry['sha1']}")
    return json.loads(raw), raw


def allowed(library):
    """Whether the version JSON's rules let this OS run the library (no rules: everywhere)."""
    rules = library.get("rules")
    if not rules:
        return True
    verdict = False
    for rule in rules:
        applies = True
        os_rule = rule.get("os", {})
        if "name" in os_rule and os_rule["name"] != "windows":
            applies = False
        if "arch" in os_rule and os_rule["arch"] not in ("x86_64", "x64", "amd64"):
            applies = False
        if "features" in rule:
            applies = False
        if applies:
            verdict = rule["action"] == "allow"
    return verdict


def library_files(version):
    """(path, url, sha1, size) for every library artifact this OS runs."""
    out = []
    for library in version.get("libraries", []):
        downloads = library.get("downloads") or {}
        artifact = downloads.get("artifact")
        if artifact and allowed(library):
            out.append((artifact["path"], artifact["url"], artifact["sha1"], artifact.get("size")))
        for classifier, entry in (downloads.get("classifiers") or {}).items():
            if allowed(library) and "windows" in classifier:
                out.append((entry["path"], entry["url"], entry["sha1"], entry.get("size")))
    return out


def asset_objects(index):
    return [
        (f"assets/objects/{obj['hash'][:2]}/{obj['hash']}",
         f"{RESOURCES}/{obj['hash'][:2]}/{obj['hash']}", obj["hash"], obj.get("size"))
        for obj in index["objects"].values()
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dir", nargs="?", default=os.path.join(os.path.dirname(__file__), "minecraft"))
    parser.add_argument("--version", default="26.3")
    parser.add_argument("--jobs", type=int, default=12)
    args = parser.parse_args()
    root = os.path.abspath(args.dir)
    version_id = args.version

    log(f"Mojang's manifest: {version_id}")
    version, raw = version_json(version_id, root)

    vdir = os.path.join(root, "versions", version_id)
    place(os.path.join(vdir, f"{version_id}.json"), raw, hashlib.sha1(raw).hexdigest())

    downloads = version["downloads"]
    client = downloads["client"]
    log(f"client jar   {client['url']}")
    fetch_file(client["url"], os.path.join(vdir, f"{version_id}.jar"), client["sha1"], client.get("size"))

    server = downloads.get("server")
    if server:
        log(f"server jar   {server['url']}")
        fetch_file(server["url"], os.path.join(root, "server.jar"), server["sha1"], server.get("size"))

    index_info = version["assetIndex"]
    index_path = os.path.join(root, "assets", "indexes", f"{index_info['id']}.json")
    fetch_file(index_info["url"], index_path, index_info["sha1"], index_info.get("size"))
    with open(index_path, "rb") as f:
        index = json.load(f)

    # The version JSON's paths are relative to the `libraries` folder.
    library_jobs = [(url, os.path.join(root, "libraries", path), digest, size)
                    for path, url, digest, size in library_files(version)]
    log(f"libraries    {len(library_jobs)} files")
    object_jobs = [(url, os.path.join(root, path), digest, size)
                   for path, url, digest, size in asset_objects(index)]
    log(f"assets       {len(object_jobs)} files, {index_info.get('totalSize', 0) / 2**20:.0f} MB")

    jobs = library_jobs + object_jobs
    done = kept = failed = 0
    started = time.time()
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(fetch_file, url, dest, digest, size): dest
                   for url, dest, digest, size in jobs}
        for future in as_completed(futures):
            dest = futures[future]
            done += 1
            try:
                if future.result() == "kept":
                    kept += 1
            except Exception as e:  # noqa: BLE001 - report and keep going
                failed += 1
                log(f"  FAILED {os.path.relpath(dest, root)}: {e}")
            if done % 200 == 0 or done == len(jobs):
                rate = done / max(time.time() - started, 0.001)
                log(f"  {done}/{len(jobs)}  kept {kept}  failed {failed}  {rate:.0f}/s")

    log(f"done in {time.time() - started:.0f}s: {done} files, {kept} already there, {failed} failed")
    if failed:
        return 1
    log(f"ready: {root}")
    log(f'  next: horizon-prepare --prepare --server-jar "{os.path.join(root, "server.jar")}" '
        f'--minecraft-dir "{root}"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
