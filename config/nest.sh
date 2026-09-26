#!/bin/sh
# Usage: nest.sh <public_token> <rtsp_output_url>
# Pulls a Nest public-share camera (see nest_hls.py) and pushes it to go2rtc over RTSP.
set -eu

TOKEN="$1"
OUTPUT="$2"

# -re paces the bursty 4s HLS segments into a smooth real-time feed.
# Copy H.264 as-is; re-encode audio (Nest's ADTS AAC lacks the global header the RTSP
# muxer needs up front); drop the timed_id3 data track.
python3 /config/nest_hls.py "$TOKEN" | exec ffmpeg -hide_banner -loglevel warning \
  -re -f mpegts -i pipe:0 \
  -map 0:v:0 -map 0:a:0? -c:v copy -c:a aac -b:a 64k \
  -rtsp_transport tcp -f rtsp "$OUTPUT"
