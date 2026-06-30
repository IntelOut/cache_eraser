"""GUI application for Cache Eraser.

Copyright IntelOut (c) 2026

Tkinter-based interface for scanning directories, previewing
cache artifacts, and deleting them with optional dry-run mode.
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from cache_patterns import CACHE_PATTERNS
from scanner import scan_directory, delete_items, format_size, ScanResult


def _resource_path(relative: str) -> str:
    """Get absolute path to a resource, works for dev and PyInstaller builds.

    When bundled with PyInstaller the icon is extracted to a temporary
    directory pointed to by ``sys._MEIPASS``.
    """
    base: str | None = getattr(sys, '_MEIPASS', None)
    if base is None:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative)


ICON_FILE = _resource_path("icon.png")


class CacheEraserApp:
    """Main application window.

    Provides directory selection, cache type filtering, scan results
    in a sortable table, dry-run toggle, and bulk deletion.
    """

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Cache Eraser")

        self._set_window_icon()

        self.root.geometry("950x650")
        self.root.minsize(700, 500)

        self.scan_results: ScanResult = []
        self._busy = False
        self.path_var = tk.StringVar()
        self.type_vars: dict[str, tk.BooleanVar] = {}
        self.scan_btn: ttk.Button = ttk.Button()
        self.dry_run_var = tk.BooleanVar()
        self.delete_btn: ttk.Button = ttk.Button()
        self.tree: ttk.Treeview = ttk.Treeview()
        self.progress: ttk.Progressbar = ttk.Progressbar()
        self.status_var = tk.StringVar()

        self._build_widgets()
        self._bind_events()

    def _set_window_icon(self) -> None:
        """Set the window and taskbar icon from *ICON_FILE* if it exists."""
        if os.path.isfile(ICON_FILE):
            try:
                img = tk.PhotoImage(file=ICON_FILE)
                self.root.iconphoto(True, img)
            except tk.TclError:
                pass

    # ------------------------------------------------------------------
    # Widget layout
    # ------------------------------------------------------------------

    def _build_widgets(self) -> None:
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(3, weight=1)

        self._build_path_row(main)
        self._build_type_grid(main)
        self._build_button_bar(main)
        self._build_tree(main)
        self._build_progress_and_status(main)

    def _build_path_row(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Root directory", padding=5)
        frame.grid(row=0, column=0, sticky=tk.EW, pady=(0, 5))
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Path:").grid(row=0, column=0, padx=(0, 5))
        self.path_var = tk.StringVar(value=os.path.abspath("."))
        entry = ttk.Entry(frame, textvariable=self.path_var)
        entry.grid(row=0, column=1, sticky=tk.EW, padx=(0, 5))
        ttk.Button(frame, text="Browse", command=self._browse).grid(row=0, column=2)

    def _build_type_grid(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Cache types to find", padding=5)
        frame.grid(row=1, column=0, sticky=tk.EW, pady=(0, 5))

        self.type_vars.clear()
        cols = 4
        for i, p in enumerate(CACHE_PATTERNS):
            var = tk.BooleanVar(value=True)
            self.type_vars[p.id] = var
            row = i // cols
            col = i % cols
            cb = ttk.Checkbutton(frame, text=p.label, variable=var)
            cb.grid(row=row, column=col, sticky=tk.W, padx=(5, 15), pady=1)

    def _build_button_bar(self, parent: ttk.Frame) -> None:
        frame = ttk.Frame(parent)
        frame.grid(row=2, column=0, sticky=tk.EW, pady=(0, 5))
        frame.columnconfigure(3, weight=1)

        self.scan_btn = ttk.Button(frame, text="Scan", command=self._start_scan)
        self.scan_btn.grid(row=0, column=0, padx=(0, 5))

        self.dry_run_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text="Dry run (no deletion)", variable=self.dry_run_var).grid(
            row=0, column=1, padx=(5, 10))

        self.delete_btn = ttk.Button(frame, text="Delete All", command=self._confirm_delete)
        self.delete_btn.grid(row=0, column=2, padx=(5, 0))
        self.delete_btn.state(["disabled"])

        ttk.Button(frame, text="Select All", command=self._select_all).grid(
            row=0, column=4, padx=(5, 2))
        ttk.Button(frame, text="Deselect All", command=self._deselect_all).grid(
            row=0, column=5, padx=(2, 0))

    def _build_tree(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Found items", padding=5)
        frame.grid(row=3, column=0, sticky=tk.NSEW, pady=(0, 5))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        columns = ("path", "type", "size")
        self.tree = ttk.Treeview(frame, columns=columns, show="tree headings",
                                 selectmode="extended")
        self.tree.heading("#0", text="", anchor=tk.W)
        self.tree.heading("path", text="Path", anchor=tk.W)
        self.tree.heading("type", text="Type", anchor=tk.W)
        self.tree.heading("size", text="Size", anchor=tk.E)
        self.tree.column("#0", width=40, minwidth=30, stretch=False)
        self.tree.column("path", width=500, minwidth=200, stretch=True)
        self.tree.column("type", width=130, minwidth=80, stretch=False)
        self.tree.column("size", width=100, minwidth=70, stretch=False)

        vsb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=1, column=0, sticky=tk.NSEW)
        vsb.grid(row=1, column=1, sticky=tk.NS)

    def _build_progress_and_status(self, parent: ttk.Frame) -> None:
        self.progress = ttk.Progressbar(parent, mode="indeterminate")
        self.progress.grid(row=4, column=0, sticky=tk.EW, pady=(0, 3))

        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(parent, textvariable=self.status_var,
                                 relief=tk.SUNKEN, anchor=tk.W)
        status_label.grid(row=5, column=0, sticky=tk.EW)

    # ------------------------------------------------------------------
    # Event bindings
    # ------------------------------------------------------------------

    def _bind_events(self) -> None:
        self.dry_run_var.trace_add("write", self._update_delete_button)

    def _update_delete_button(self, *_args) -> None:
        """Enable/disable the Delete button based on dry-run state."""
        if self.dry_run_var.get():
            self.delete_btn.state(["disabled"])
        else:
            self.delete_btn.state(["!disabled"])

    # ------------------------------------------------------------------
    # UI actions
    # ------------------------------------------------------------------

    def _browse(self) -> None:
        """Open a folder-selection dialog and update the path entry."""
        d = filedialog.askdirectory(title="Select root directory")
        if d:
            self.path_var.set(d)

    def _select_all(self) -> None:
        for var in self.type_vars.values():
            var.set(True)

    def _deselect_all(self) -> None:
        for var in self.type_vars.values():
            var.set(False)

    def _set_busy(self, busy: bool) -> None:
        """Toggle the UI between busy and idle states.

        Disables controls and starts an indeterminate progress bar
        when *busy* is ``True``; reverts everything when ``False``.
        """
        self._busy = busy
        state_spec = ["disabled"] if busy else ["!disabled"]
        self.scan_btn.configure(text="Scanning..." if busy else "Scan")
        self.scan_btn.state(state_spec)
        self.delete_btn.state(state_spec)
        if busy:
            self.progress.configure(mode="indeterminate")
            self.progress.start(50)
        else:
            self.progress.stop()
            self.progress.configure(mode="determinate", value=0)
        self.root.update_idletasks()

    # ------------------------------------------------------------------
    # Scan workflow
    # ------------------------------------------------------------------

    def _start_scan(self) -> None:
        """Validate inputs and start the scan in a background thread."""
        if self._busy:
            return
        root_path = self.path_var.get().strip()
        if not root_path or not os.path.isdir(root_path):
            messagebox.showerror("Error", "Invalid directory path")
            return

        selected = {pid for pid, var in self.type_vars.items() if var.get()}
        if not selected:
            messagebox.showinfo("Info", "Select at least one cache type")
            return

        self._set_busy(True)
        self.status_var.set("Scanning...")
        self.tree.delete(*self.tree.get_children())

        t = threading.Thread(target=self._scan_thread,
                             args=(root_path, selected), daemon=True)
        t.start()

    def _scan_thread(self, root_path: str, selected: set[str]) -> None:
        """Run *scan_directory* in a thread and schedule the UI callback."""
        try:
            results = scan_directory(root_path, selected)
            self.root.after(0, self._scan_complete, results)
        except OSError as e:
            self.root.after(0, self._scan_error, str(e))

    def _scan_complete(self, results: ScanResult) -> None:
        """Populate the tree with scan results and re-enable the UI."""
        self.scan_results = results
        total_size = sum(s for _, _, s in results)
        self.tree.delete(*self.tree.get_children())

        sorted_results = sorted(results, key=lambda x: -x[2])

        for path, pid, size in sorted_results:
            label = next((p.label for p in CACHE_PATTERNS if p.id == pid), pid)
            self.tree.insert("", tk.END, values=(path, label, format_size(size)))

        count = len(results)
        self.status_var.set(
            f"Found {count} item{'s' if count != 1 else ''} ({format_size(total_size)})")
        self._set_busy(False)

        if self.dry_run_var.get():
            self.delete_btn.state(["disabled"])
        elif results:
            self.delete_btn.state(["!disabled"])

    def _scan_error(self, error: str) -> None:
        """Handle an error that occurred during scanning."""
        self._set_busy(False)
        self.status_var.set("Scan failed")
        messagebox.showerror("Scan Error", error)

    # ------------------------------------------------------------------
    # Delete workflow
    # ------------------------------------------------------------------

    def _confirm_delete(self) -> None:
        """Ask for confirmation, then delete in a background thread."""
        if self._busy or self.dry_run_var.get():
            return
        if not self.scan_results:
            messagebox.showinfo("Info", "Nothing to delete. Run Scan first.")
            return

        total_size = sum(s for _, _, s in self.scan_results)
        count = len(self.scan_results)
        msg = (
            f"Delete {count} item{'s' if count != 1 else ''} "
            f"({format_size(total_size)})?\n"
            "This action cannot be undone."
        )

        if not messagebox.askyesno("Confirm Deletion", msg, icon=messagebox.WARNING):
            return

        self._set_busy(True)
        self.status_var.set("Deleting...")
        threading.Thread(target=self._delete_thread, daemon=True).start()

    def _delete_thread(self) -> None:
        """Run *delete_items* in a thread and schedule the UI callback."""
        paths = [p for p, _, _ in self.scan_results]
        try:
            success, errors = delete_items(paths)
            self.root.after(0, self._delete_complete, success, errors)
        except OSError as e:
            self.root.after(0, self._scan_error, str(e))

    def _delete_complete(self, success: int, errors: int) -> None:
        """Clear the results and show the final status."""
        self._set_busy(False)
        self.scan_results = []
        self.tree.delete(*self.tree.get_children())
        self.delete_btn.state(["disabled"])

        parts = [f"Deleted {success} item{'s' if success != 1 else ''}"]
        if errors:
            parts.append(f"{errors} error{'s' if errors != 1 else ''}")
        self.status_var.set(" | ".join(parts))
        messagebox.showinfo("Complete", "\n".join(parts))


def entry_point() -> None:
    """Application entry point."""
    root = tk.Tk()
    CacheEraserApp(root)
    root.mainloop()


if __name__ == "__main__":
    entry_point()
