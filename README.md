# RISD Yearbook 2027 — Fabric Only

A browser-only green-screen fabric editor. Open `index.html` locally or host it as a static site. Select a local NEF, JPG, PNG or WebP photograph and artwork; images are processed on your device. NEF support depends on the camera model and compression; unsupported files can be converted to JPG or PNG first. NEF decoding uses the locally bundled libraw-wasm (see vendor/libraw/NOTICE.txt). The page and decoder must be served over HTTP(S), such as GitHub Pages, rather than opened as a file:// URL.

The editor detects multiple green regions and offers independent artwork, fold distortion, lighting, mesh adjustment and shadow recovery. Enter a positive photo number to download an uncompressed, 8-bit-per-channel RGB TIFF named `1_original-name.tif`, or download a PNG. The prototype limits the rendered image's longest side to 3200 pixels. It does not offer 16-bit editing, original RAW quality, Google Drive integration, or server-side processing.

GitHub Pages publishes `index.html`; `static/index.html` is the same page for compatibility with earlier links. Keep the two files in sync when updating.
