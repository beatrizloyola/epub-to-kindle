#!/usr/bin/env python3
"""EPUB -> AZW3 converter GUI. Wraps Calibre's ebook-convert."""

import os
import queue
import shutil
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

APP_TITLE = "EPUB -> AZW3 Converter"
COVER_TYPES = [("Images", "*.jpg *.jpeg *.png"), ("All files", "*.*")]


def find_ebook_convert():
    """Locate ebook-convert on PATH, falling back to common Calibre install dirs."""
    found = shutil.which("ebook-convert")
    if found:
        return found
    for candidate in ("/usr/bin/ebook-convert",
                      "/opt/calibre/ebook-convert",
                      "/usr/local/bin/ebook-convert"):
        if os.access(candidate, os.X_OK):
            return candidate
    return None


def read_epub_metadata(path):
    """Return (title, author) from an EPUB, empty strings when unavailable."""
    try:
        from ebooklib import epub
    except ImportError:
        return "", ""
    try:
        book = epub.read_epub(path)
    except Exception:
        return "", ""

    def first(field):
        try:
            values = book.get_metadata("DC", field)
        except Exception:
            return ""
        if values and values[0] and values[0][0]:
            return str(values[0][0]).strip()
        return ""

    return first("title"), first("creator")


class ConverterApp:
    def __init__(self, root):
        self.root = root
        self.ebook_convert = find_ebook_convert()
        self.msg_queue = queue.Queue()
        self.worker = None

        self.input_path = tk.StringVar()
        self.title_var = tk.StringVar()
        self.author_var = tk.StringVar()
        self.cover_path = tk.StringVar()
        self.output_dir = tk.StringVar(value=str(Path.home()))

        root.title(APP_TITLE)
        root.geometry("720x520")
        root.minsize(620, 460)
        self._build_ui()
        self._poll_queue()

        if not self.ebook_convert:
            self.log("ERROR: 'ebook-convert' not found on PATH.")
            self.log("Install Calibre: sudo apt install calibre")
            messagebox.showerror(
                APP_TITLE,
                "Calibre's 'ebook-convert' was not found on your PATH.\n\n"
                "Install it with:\n    sudo apt install calibre\n\n"
                "Conversion is disabled until it is available.",
            )
            self.convert_btn.state(["disabled"])
        else:
            self.log(f"Using: {self.ebook_convert}")

    # ---------- UI ----------

    def _build_ui(self):
        pad = {"padx": 8, "pady": 5}
        frm = ttk.Frame(self.root, padding=12)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)

        row = 0
        ttk.Label(frm, text="EPUB file:").grid(row=row, column=0, sticky="w", **pad)
        ttk.Entry(frm, textvariable=self.input_path).grid(row=row, column=1, sticky="ew", **pad)
        ttk.Button(frm, text="Browse...", command=self.pick_input).grid(row=row, column=2, **pad)

        row += 1
        ttk.Label(frm, text="Title:").grid(row=row, column=0, sticky="w", **pad)
        ttk.Entry(frm, textvariable=self.title_var).grid(row=row, column=1, columnspan=2, sticky="ew", **pad)

        row += 1
        ttk.Label(frm, text="Author:").grid(row=row, column=0, sticky="w", **pad)
        ttk.Entry(frm, textvariable=self.author_var).grid(row=row, column=1, columnspan=2, sticky="ew", **pad)

        row += 1
        ttk.Label(frm, text="Cover image:").grid(row=row, column=0, sticky="w", **pad)
        ttk.Entry(frm, textvariable=self.cover_path).grid(row=row, column=1, sticky="ew", **pad)
        cover_btns = ttk.Frame(frm)
        cover_btns.grid(row=row, column=2, **pad)
        ttk.Button(cover_btns, text="Browse...", command=self.pick_cover).pack(side="left")
        ttk.Button(cover_btns, text="Clear", command=lambda: self.cover_path.set("")).pack(side="left", padx=(4, 0))

        row += 1
        ttk.Label(frm, text="Output folder:").grid(row=row, column=0, sticky="w", **pad)
        ttk.Entry(frm, textvariable=self.output_dir).grid(row=row, column=1, sticky="ew", **pad)
        ttk.Button(frm, text="Browse...", command=self.pick_output).grid(row=row, column=2, **pad)

        row += 1
        actions = ttk.Frame(frm)
        actions.grid(row=row, column=0, columnspan=3, sticky="ew", **pad)
        self.convert_btn = ttk.Button(actions, text="Convert", command=self.start_convert)
        self.convert_btn.pack(side="left")
        ttk.Button(actions, text="Clear log", command=self.clear_log).pack(side="left", padx=8)
        self.progress = ttk.Progressbar(actions, mode="indeterminate", length=200)
        self.progress.pack(side="right")

        row += 1
        ttk.Label(frm, text="Status / Calibre output:").grid(row=row, column=0, columnspan=3, sticky="w", **pad)

        row += 1
        frm.rowconfigure(row, weight=1)
        log_frame = ttk.Frame(frm)
        log_frame.grid(row=row, column=0, columnspan=3, sticky="nsew", padx=8, pady=(0, 8))
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        self.log_text = tk.Text(log_frame, wrap="word", height=12, state="disabled")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scroll.set)

    def log(self, text):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text.rstrip() + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    # ---------- pickers ----------

    def pick_input(self):
        path = filedialog.askopenfilename(
            title="Select an EPUB file",
            filetypes=[("EPUB files", "*.epub"), ("All files", "*.*")],
        )
        if not path:
            return
        self.input_path.set(path)
        if not self.output_dir.get():
            self.output_dir.set(str(Path(path).parent))
        self.log(f"Selected: {path}")
        title, author = read_epub_metadata(path)
        if title:
            self.title_var.set(title)
        if author:
            self.author_var.set(author)
        if title or author:
            self.log(f"Metadata read - title: {title or '(none)'} | author: {author or '(none)'}")
        else:
            self.log("Could not read metadata from this EPUB; fill title/author manually.")

    def pick_cover(self):
        path = filedialog.askopenfilename(title="Select a cover image", filetypes=COVER_TYPES)
        if not path:
            return
        if Path(path).suffix.lower() not in (".jpg", ".jpeg", ".png"):
            messagebox.showwarning(APP_TITLE, "Cover must be a .jpg, .jpeg or .png file.")
            return
        self.cover_path.set(path)

    def pick_output(self):
        path = filedialog.askdirectory(title="Select an output folder")
        if path:
            self.output_dir.set(path)

    # ---------- conversion ----------

    def _validate(self):
        """Return (input, outdir) or None after showing the relevant error."""
        if not self.ebook_convert:
            messagebox.showerror(APP_TITLE, "'ebook-convert' is not available.")
            return None

        src = self.input_path.get().strip()
        if not src:
            messagebox.showwarning(APP_TITLE, "Select an input .epub file first.")
            return None
        src_path = Path(src).expanduser()
        if not src_path.is_file():
            messagebox.showerror(APP_TITLE, f"Input file does not exist:\n{src_path}")
            return None
        if src_path.suffix.lower() != ".epub":
            if not messagebox.askyesno(APP_TITLE, "Input does not end in .epub. Convert anyway?"):
                return None

        cover = self.cover_path.get().strip()
        if cover and not Path(cover).expanduser().is_file():
            messagebox.showerror(APP_TITLE, f"Cover image does not exist:\n{cover}")
            return None

        outdir = self.output_dir.get().strip() or str(src_path.parent)
        out_path = Path(outdir).expanduser()
        if not out_path.is_dir():
            messagebox.showerror(APP_TITLE, f"Output folder does not exist:\n{out_path}")
            return None
        if not os.access(out_path, os.W_OK):
            messagebox.showerror(APP_TITLE, f"Output folder is not writable:\n{out_path}")
            return None

        return src_path, out_path

    def start_convert(self):
        validated = self._validate()
        if not validated:
            return
        src_path, out_path = validated

        dest = out_path / (src_path.stem + ".azw3")
        if dest.exists():
            if not messagebox.askyesno(APP_TITLE, f"{dest.name} already exists. Overwrite?"):
                return

        cmd = [self.ebook_convert, str(src_path), str(dest)]
        title = self.title_var.get().strip()
        author = self.author_var.get().strip()
        cover = self.cover_path.get().strip()
        if title:
            cmd += ["--title", title]
        if author:
            cmd += ["--authors", author]
        if cover:
            cmd += ["--cover", str(Path(cover).expanduser())]

        self.convert_btn.state(["disabled"])
        self.progress.start(12)
        self.log("")
        self.log("=" * 60)
        self.log(f"Converting -> {dest}")
        self.worker = threading.Thread(target=self._run_convert, args=(cmd, dest), daemon=True)
        self.worker.start()

    def _run_convert(self, cmd, dest):
        """Runs off the UI thread; talks back through msg_queue."""
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            for line in proc.stdout:
                self.msg_queue.put(("log", line.rstrip()))
            code = proc.wait()
        except FileNotFoundError:
            self.msg_queue.put(("done", (False, "ebook-convert disappeared from PATH.")))
            return
        except Exception as exc:
            self.msg_queue.put(("done", (False, f"Failed to run ebook-convert: {exc}")))
            return

        if code == 0 and Path(dest).is_file():
            self.msg_queue.put(("done", (True, f"SUCCESS: wrote {dest}")))
        else:
            self.msg_queue.put(("done", (False, f"FAILED: ebook-convert exited with code {code}")))

    def _poll_queue(self):
        while True:
            try:
                kind, payload = self.msg_queue.get_nowait()
            except queue.Empty:
                break
            if kind == "log":
                self.log(payload)
            elif kind == "done":
                ok, message = payload
                self.progress.stop()
                self.convert_btn.state(["!disabled"])
                self.log(message)
                if ok:
                    messagebox.showinfo(APP_TITLE, message)
                else:
                    messagebox.showerror(APP_TITLE, message + "\n\nSee the status area for details.")
        self.root.after(120, self._poll_queue)


def main():
    root = tk.Tk()
    ConverterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
