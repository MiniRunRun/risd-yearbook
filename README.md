# RISD Yearbook 2027 — Fabric Only

A local Flask application using the supplied Shadow Recovery prototype for multi-canvas fabric editing. It detects green regions, assigns artwork per region, and retains the prototype's fold, lighting, mesh and shadow-recovery controls. The app can decode supported camera RAWs with LibRaw through rawpy and use Google Picker to select a file.

## Run locally

Install Python 3.10–3.12 and then:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Open http://127.0.0.1:5000. Without Google credentials, use **Try 3-canvas demo** or upload a local image/RAW. Choose artwork, proceed to Create, and enter a positive photo number at Finalize. The TIFF downloads locally. A `.RAW` extension is not a guarantee that the contents are a camera RAW; decoding depends on LibRaw support for the camera and file.

## Connect Google Drive

1. Create a Google Cloud project, enable Google Drive API and Google Picker API, configure the OAuth consent screen and add test users while the app is in testing.
2. Create a Web application OAuth client. Add `http://localhost:5000` as an authorized JavaScript origin and `http://localhost:5000/oauth/callback` as an authorized redirect URI. Browse at `http://localhost:5000` (the host must match the redirect configuration).
3. Create a browser API key, restrict it to the Picker API and the intended web origins. Copy the numeric Cloud project number as the Picker App ID.
4. Fill in `.env`: OAuth client ID and secret, Picker API key, project number, redirect URI and the ID of the Yearbook root folder. Generate a long random `SECRET_KEY`. Each student signs in to their own Google account and must already have permission to read the source and create files in its folder. No password is collected by this application.
5. Restart, connect Google Drive, and select a file inside the configured folder tree. The backend checks the file's ancestry and checks it again before export. The output is created beside the source; matching names get ` (2)`, ` (3)`, etc. The original is never updated. Drive can allow duplicate names, so simultaneous submissions can still race.

Google authorization requests the broad `drive` scope to support browsing team folders and writing alongside source files; Google may require app verification. Folder restriction is enforced by this app, not by OAuth. Picker receives a short-lived user access token in the browser; the client secret and refresh token remain on the server. Do not place a service-account key in the browser. This project has not been verified against a real Google account or Drive folder; configure and test access before use.

## Image quality and limits

The provided prototype's rendering uses browser canvas, downsizes its output to at most 3200 pixels on the long side, and processes 8-bit pixels. RAW preview is also reduced to at most 2400 pixels. TIFF uses lossless Deflate compression, but **is 8-bit per channel**, not a full-resolution or 16-bit RAW workflow. The TIFF container cannot restore precision already discarded by the preview/compositing pipeline. For production quality, implement a server-side full-resolution 16-bit renderer using the editor's mesh, matte, settings and original artwork; validate with representative camera files and a color-managed reference. Preview and TIFF match the same prototype renderer within those limits.

## Deployment limitations

This is a local development prototype, not a hardened multi-user production service. OAuth tokens and state are process-local and lost on restart; use a shared encrypted session store, expiring sessions, rate limits, quotas, CSRF protection, strict origin/host handling, HTTPS and secure cookies, and isolated resource-limited RAW decoding before public deployment. Set `COOKIE_SECURE=1` under HTTPS. Do not run the Flask development server publicly. Configure upload limits appropriate for the camera files and infrastructure. The local demo uses temporary files for RAW decoding; the server does not permanently store uploaded photographs.

## Checks

Run `python -m unittest discover -s tests` after installing requirements. The tests cover positive integer naming, lossless TIFF format, local preview and demo export. Drive calls, OAuth and camera-specific RAW decoding need credentials and real test files and are not covered by the local test suite.
