# RISD Yearbook 2027 — Fabric Only

A browser-only green-screen fabric editor. Open `index.html` locally or host it as a static site. Select a local NEF, JPG, PNG or WebP photograph and artwork; images are processed on your device. NEF support depends on the camera model and compression; unsupported files can be converted to JPG or PNG first. NEF decoding uses the locally bundled libraw-wasm (see vendor/libraw/NOTICE.txt). The page and decoder must be served over HTTP(S), such as GitHub Pages, rather than opened as a file:// URL.

The editor detects multiple green regions and offers independent artwork, fold distortion, lighting, mesh adjustment and shadow recovery. Enter a positive photo number to download an uncompressed, 8-bit-per-channel RGB TIFF named `1_original-name.tif`, or download a PNG. The prototype limits the rendered image's longest side to 3200 pixels. It does not offer 16-bit editing, original RAW quality, Google Drive integration, or server-side processing.

GitHub Pages publishes `index.html`; `static/index.html` is the same page for compatibility with earlier links. Keep the two files in sync when updating.

## Save and reopen projects

The Save screen downloads the finished TIFF and an editable project JSON as separate files. The JSON embeds the source photograph and artworks, plus the mask, mesh, settings and photo number. It may be large and contains the original images; handle it like the source files. If your browser blocks multiple downloads, allow this site to download multiple files and save again. Use **Open Saved Project** on the Upload screen to continue editing. Project files are processed locally.

In supported browsers, SAVE asks you to choose a folder and grant access. The app remembers that folder until the page is closed; choose Change Folder to select another. Existing matching filenames get a numbered suffix. Other browsers use normal downloads, which may require allowing multiple files. Folder selection is required because browsers do not reveal the source file location.

## Artwork library

Upload multiple artwork images on the Upload screen, or use **+ Add** in Create. Select the canvas, then click or tap a thumbnail to replace its artwork. Unassigned library images are included in the editable project JSON, which can increase its size.

On the Create screen use Command-Z (Ctrl-Z on Windows) to undo an edit, and Shift-Command-Z (Ctrl-Shift-Z) to redo. History is kept only for the current page session.

NEF files with an embedded near-full-resolution camera-rendered JPEG use that image for editing to preserve the camera appearance; this is an 8-bit JPEG preview, not a full RAW-quality render. When a sufficiently large preview is unavailable, the application uses the 8-bit LibRaw render. Neither path reproduces Lightroom adjustments; the source NEF remains embedded in the editable JSON.
