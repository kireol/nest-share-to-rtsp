# nest-share-to-rtsp

Turn a **public Nest camera share link** (`https://video.nest.com/live/<TOKEN>`) into a local
**RTSP stream** you can use in Frigate, Home Assistant, Blue Iris, VLC, etc.

It runs [go2rtc](https://github.com/AlexxIT/go2rtc) in Docker. A small Python helper
(`config/nest_hls.py`) looks up the camera's current HLS stream from the share token and pulls
it over a single keep-alive connection (the Nest stream server rejects segment requests made on
a different connection, which breaks ffmpeg's own HLS reader). The MPEG-TS is piped into ffmpeg
and pushed to go2rtc, which serves it as RTSP.

## Requirements

- Docker with Docker Compose
- A Nest camera with public sharing enabled (Nest app → camera settings → Share → public link)

## Setup

1. Copy the example env file and put in your token:

   ```sh
   cp .env.example .env
   ```

   If your share link is `https://video.nest.com/live/AbC123xYz0`, set `NEST_TOKEN=AbC123xYz0`.

2. Start it:

   ```sh
   docker compose up -d
   ```

3. Open the stream:

   - RTSP: `rtsp://<docker-host>:8564/nest` (e.g. `rtsp://192.168.1.50:8564/nest`)
   - go2rtc web UI: `http://<docker-host>:1994`

Ports are set by `RTSP_PORT` and `WEB_PORT` in `.env`.

## Notes

- The stream starts on demand when a client connects; the stream host/UUID is re-resolved on
  every (re)start, so changes on Nest's side are handled.
- Video (H.264) is copied as-is; audio is re-encoded to AAC so the RTSP muxer accepts it.
- To add more cameras, add more entries under `streams:` in `config/go2rtc.yaml`, each with its
  own token (e.g. `backyard: exec:/config/nest.sh ${NEST_TOKEN_2} {output}`) and pass the extra
  env var through in `docker-compose.yml`.
- Your `.env` contains your share token and is git-ignored; anyone with the token can view the camera.
