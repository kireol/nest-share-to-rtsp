#!/usr/bin/env python3
"""Pull a Nest public-share camera's HLS stream and write raw MPEG-TS to stdout.

Usage: nest_hls.py <public_token>

The Nest/Wowza stream server binds an HLS session to the TCP connection: segments
404 unless they're fetched over the same keep-alive connection as the chunklist.
ffmpeg's HLS demuxer can't guarantee that, so we fetch everything over one
http.client connection here and pipe the TS into ffmpeg.
"""
import http.client
import json
import sys
import time
import urllib.request

API = "https://video.nest.com/api/dropcam/cameras.get_by_public_token?token={}"
MAX_FAILURES = 5


def log(msg):
    print(f"nest_hls: {msg}", file=sys.stderr, flush=True)


def resolve(token):
    with urllib.request.urlopen(API.format(token), timeout=20) as r:
        info = json.load(r)
    items = info.get("items") or []
    if not items:
        raise RuntimeError(f"token {token} not found: {info}")
    cam = items[0]
    if not cam.get("is_streaming"):
        log("warning: camera reports is_streaming=false")
    host = cam["live_stream_host"].split(":")[0]
    return host, f"/nexus_aac/{cam['uuid']}", cam.get("name", "")


def get(conn, path):
    conn.request("GET", path, headers={"Connection": "keep-alive"})
    resp = conn.getresponse()
    body = resp.read()
    if resp.status != 200:
        raise RuntimeError(f"HTTP {resp.status} for {path}")
    return body


def parse_media_playlist(text):
    seq, segs, dur = 0, [], 4.0
    for line in text.splitlines():
        if line.startswith("#EXT-X-MEDIA-SEQUENCE:"):
            seq = int(line.split(":", 1)[1])
        elif line.startswith("#EXT-X-TARGETDURATION:"):
            dur = float(line.split(":", 1)[1])
        elif line and not line.startswith("#"):
            segs.append(line)
    return seq, segs, dur


def stream(token, out):
    host, base, name = resolve(token)
    log(f"camera '{name}' via {host}{base}")
    conn = http.client.HTTPSConnection(host, timeout=20)
    master = get(conn, f"{base}/playlist.m3u8?public={token}").decode()
    chunklist = next(l for l in master.splitlines() if l and not l.startswith("#"))
    next_seq = None
    while True:
        seq, segs, dur = parse_media_playlist(get(conn, f"{base}/{chunklist}").decode())
        if next_seq is None:
            next_seq = seq + len(segs) - 1  # start at the live edge
        for i, seg in enumerate(segs):
            if seq + i < next_seq:
                continue
            out.write(get(conn, f"{base}/{seg}"))
            out.flush()
            next_seq = seq + i + 1
        time.sleep(dur / 2)


def main():
    token = sys.argv[1]
    out = sys.stdout.buffer
    failures = 0
    while failures < MAX_FAILURES:
        started = time.time()
        try:
            stream(token, out)
        except BrokenPipeError:
            return  # ffmpeg went away; go2rtc will restart us when needed
        except Exception as e:  # noqa: BLE001 - reconnect on any network/parse error
            if time.time() - started > 60:
                failures = 0
            failures += 1
            log(f"error ({failures}/{MAX_FAILURES}): {e}; reconnecting")
            time.sleep(2)
    sys.exit(1)


if __name__ == "__main__":
    main()
