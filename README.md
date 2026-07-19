# EPUB → AZW3 Converter

A small desktop GUI for converting EPUB files to AZW3 (Kindle format), wrapping Calibre's
`ebook-convert` CLI. Lets you override the title, author, and cover image before converting.

Built with Tkinter, packaged as a single-file executable with PyInstaller. Targets Ubuntu and Ubuntu-based Linux distributions.

## Features

- File picker for the input `.epub`
- Title and author fields, pre-filled from the EPUB's existing metadata
- Cover image picker (`.jpg`, `.jpeg`, `.png`)
- Output folder picker
- Live Calibre output streamed into a status area
- Error handling for missing `ebook-convert`, missing files, unwritable output folders, and
  existing files that would be overwritten

## Requirements

**At run time:** Calibre must be installed — it supplies the `ebook-convert` binary that does
the actual conversion.

```bash
sudo apt install calibre
```

The bundled executable ships its own Python interpreter, so Python is *not* required on the
machine that runs it.

**To build:** Python 3.8+, Tkinter, and `venv`.

```bash
sudo apt install python3-tk python3-venv
```

## Building

Clone the repository and run the build script:

```bash
git clone <repository-url>
cd conversor
./build.sh
```

This creates a virtualenv in `.venv/`, installs the dependencies from `requirements.txt`, and
runs PyInstaller. The result is a single executable at `dist/epub2azw3` (~19 MB).

The build script fails early with an install hint if Tkinter is missing, and warns (but does
not fail) if Calibre is absent, since Calibre is only needed at run time.

## Running

From a terminal:

```bash
./dist/epub2azw3
```

Or double-click `dist/epub2azw3` in Files. If nothing happens, GNOME Files is likely blocking
executables — either right-click → **Run as Program**, or enable it permanently under
Preferences → Behavior → Executable Text Files → *Run them*.

To get a proper application-menu entry, run this from the project root:

```bash
cat > ~/.local/share/applications/epub2azw3.desktop <<EOF
[Desktop Entry]
Type=Application
Name=EPUB to AZW3 Converter
Exec=$(pwd)/dist/epub2azw3
Terminal=false
Categories=Utility;
EOF
```

`$(pwd)` expands to the absolute path of the executable. If you later move it, edit `Exec=`
in `~/.local/share/applications/epub2azw3.desktop` to match.

## Usage

1. Click **Browse...** next to *EPUB file* and pick your book. Title and author auto-fill from
   the file's metadata.
2. Edit the title and author if you want to override what's embedded in the EPUB.
3. Optionally pick a cover image. Leave it blank to keep the EPUB's existing cover.
4. Choose an output folder — defaults to the input file's folder.
5. Click **Convert**. Calibre's output appears in the status area, and a dialog reports success
   or failure when it finishes.

The output file is named after the input, with the extension swapped to `.azw3`.

## Development

Run directly from source instead of rebuilding each time:

```bash
source .venv/bin/activate
python epub2azw3.py
```

### How it works

- `find_ebook_convert()` checks `PATH` first, then falls back to `/usr/bin`, `/opt/calibre`, and
  `/usr/local/bin` — the last covers Calibre's official binary installer, which doesn't always
  land on `PATH`.
- `read_epub_metadata()` uses `ebooklib` to pull the Dublin Core `title` and `creator` fields.
  Failures are non-fatal: the fields just stay empty and you fill them in manually.
- Conversion runs on a background thread, streaming `ebook-convert`'s stdout through a
  `queue.Queue` that the Tk main loop drains every 120 ms. This keeps the UI responsive during
  long conversions.
- The subprocess is invoked with an argument list and no shell, so paths containing spaces or
  shell metacharacters are passed through safely.

## Known limitations

- The executable is built against the host's glibc. It runs on the same or newer Ubuntu-based
  releases, but not older ones — rebuild on the oldest system you need to support.
- Only one file at a time; no batch conversion.

## Files

| File | Purpose |
|---|---|
| `epub2azw3.py` | Application source |
| `requirements.txt` | Python dependencies |
| `build.sh` | Builds the executable into `dist/` |
