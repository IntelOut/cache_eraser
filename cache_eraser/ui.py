"""Tkinter user interface for Cache Eraser."""

# pylint: disable=attribute-defined-outside-init,too-many-instance-attributes
# pylint: disable=too-many-public-methods

import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from cache_eraser import __version__
from cache_eraser.deleter import DeleteReport, delete_items
from cache_eraser.formatter import format_size
from cache_eraser.paths import IS_WINDOWS, resource_path
from cache_eraser.patterns import (
    CACHE_PATTERNS,
    DEFAULT_SELECTED_IDS,
    PATTERNS_BY_ID,
    RISK_CAUTION,
)
from cache_eraser.scanner import ScanItem, ScanStats, scan_directory
from cache_eraser.ui_logic import close_action, deletion_allowed


class Tooltip:
    """Show a small tooltip after hovering over a widget."""

    def __init__(self, widget: tk.Widget, text: str, delay: int = 500) -> None:
        self.widget = widget
        self.text = text
        self.delay = delay
        self._after_id: str | None = None
        self._window: tk.Toplevel | None = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event: object = None) -> None:
        self._cancel()
        self._after_id = self.widget.after(self.delay, self._show)

    def _cancel(self) -> None:
        if self._after_id is not None:
            self.widget.after_cancel(self._after_id)
            self._after_id = None

    def _show(self) -> None:
        self._after_id = None
        if self._window is not None or not self.text:
            return
        try:
            x = self.widget.winfo_rootx() + 12
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        except tk.TclError:
            return
        window = tk.Toplevel(self.widget)
        window.wm_overrideredirect(True)
        window.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            window,
            text=self.text,
            justify=tk.LEFT,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            wraplength=380,
        )
        label.pack()
        self._window = window

    def _hide(self, _event: object = None) -> None:
        self._cancel()
        if self._window is not None:
            self._window.destroy()
            self._window = None


class CacheEraserApp:
    """Main application window."""

    scan_btn: ttk.Button
    cancel_btn: ttk.Button
    browse_btn: ttk.Button
    delete_selected_btn: ttk.Button
    delete_all_btn: ttk.Button
    details_btn: ttk.Button
    tree: ttk.Treeview
    progress: ttk.Progressbar
    path_entry: ttk.Entry

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(f"Cache Eraser {__version__}")
        self.root.geometry("1050x780")
        self.root.minsize(820, 620)
        self._icon: tk.PhotoImage | None = None
        self._set_window_icon()

        self.items: list[ScanItem] = []
        self.item_by_iid: dict[str, ScanItem] = {}
        self._queue: queue.Queue[tuple[str, object, object]] = queue.Queue()
        self._cancel = threading.Event()
        self._busy = False
        self._sort_column = "size"
        self._sort_reverse = True
        self._scan_incomplete = False
        self._deleting = False
        self._last_errors: list[str] = []
        self._last_skipped = 0
        self.scan_root: str | None = None

        self.path_var = tk.StringVar(value=os.getcwd())
        self.dry_run_var = tk.BooleanVar(value=False)
        self.trash_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Ready")
        self.selection_var = tk.StringVar(value="")
        self.type_vars: dict[str, tk.BooleanVar] = {}

        self._initial_selection = set(DEFAULT_SELECTED_IDS)

        self._build_widgets()
        self._bind_events()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._update_buttons()
        self._poll_queue()

    def _set_window_icon(self) -> None:
        """Set the window icon from a bundled ``.ico`` or ``.png`` file."""
        for name in ("icon.ico", "icon.png"):
            path = resource_path(name)
            if not os.path.isfile(path):
                continue
            try:
                if name.endswith(".ico"):
                    self.root.iconbitmap(path)
                else:
                    self._icon = tk.PhotoImage(file=path)
                    self.root.iconphoto(True, self._icon)
                return
            except tk.TclError:
                pass

    def _build_widgets(self) -> None:
        """Create every widget in the main window."""
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(4, weight=1)

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
        self.path_entry = ttk.Entry(frame, textvariable=self.path_var)
        self.path_entry.grid(row=0, column=1, sticky=tk.EW, padx=(0, 5))
        self.browse_btn = ttk.Button(frame, text="Browse", command=self._browse)
        self.browse_btn.grid(row=0, column=2)

    def _build_type_grid(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(
            parent,
            text="Cache types to find (hover for details, warning sign = risky)",
            padding=5,
        )
        frame.grid(row=1, column=0, sticky=tk.EW, pady=(0, 5))

        columns = 4
        for index, pattern in enumerate(CACHE_PATTERNS):
            variable = tk.BooleanVar(value=pattern.id in self._initial_selection)
            self.type_vars[pattern.id] = variable
            prefix = "\u26a0 " if pattern.risk == RISK_CAUTION else ""
            checkbutton = ttk.Checkbutton(frame, text=f"{prefix}{pattern.label}", variable=variable)
            checkbutton.grid(
                row=index // columns,
                column=index % columns,
                sticky=tk.W,
                padx=(5, 15),
                pady=1,
            )
            Tooltip(
                checkbutton,
                f"[{pattern.category}] {pattern.description}\nRisk: {pattern.risk}",
            )

    def _build_button_bar(self, parent: ttk.Frame) -> None:
        frame = ttk.Frame(parent)
        frame.grid(row=2, column=0, sticky=tk.EW, pady=(0, 5))

        top = ttk.Frame(frame)
        top.grid(row=0, column=0, sticky=tk.EW)

        self.scan_btn = ttk.Button(top, text="Scan (F5)", command=self._start_scan)
        self.scan_btn.grid(row=0, column=0, padx=(0, 5))

        self.cancel_btn = ttk.Button(top, text="Cancel (Esc)", command=self._cancel_operation)
        self.cancel_btn.grid(row=0, column=1, padx=(0, 10))
        self.cancel_btn.state(["disabled"])

        ttk.Checkbutton(top, text="Dry run (no deletion)", variable=self.dry_run_var).grid(
            row=0, column=2, padx=(5, 10)
        )

        ttk.Checkbutton(top, text="Move to Recycle Bin", variable=self.trash_var).grid(
            row=0, column=3, padx=(5, 10)
        )

        self.details_btn = ttk.Button(top, text="Details", command=self._show_details)
        self.details_btn.grid(row=0, column=4, padx=(5, 0))
        self.details_btn.state(["disabled"])

        bottom = ttk.Frame(frame)
        bottom.grid(row=1, column=0, sticky=tk.EW, pady=(4, 0))
        bottom.columnconfigure(2, weight=1)

        ttk.Button(bottom, text="Safe only", command=self._check_safe).grid(
            row=0, column=0, padx=(0, 5)
        )
        ttk.Button(bottom, text="Unselect all", command=self._uncheck_all).grid(
            row=0, column=1, padx=(0, 10)
        )

        self.delete_selected_btn = ttk.Button(
            bottom, text="Delete Selected (Del)", command=self._delete_selected
        )
        self.delete_selected_btn.grid(row=0, column=3, padx=(5, 5))

        self.delete_all_btn = ttk.Button(bottom, text="Delete All", command=self._delete_all)
        self.delete_all_btn.grid(row=0, column=4, padx=(5, 0))

    def _build_tree(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Found items", padding=5)
        frame.grid(row=4, column=0, sticky=tk.NSEW, pady=(0, 5))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        columns = ("path", "type", "size", "risk")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="extended")
        self.tree.heading("path", text="Path", anchor=tk.W, command=lambda: self._sort_by("path"))
        self.tree.heading("type", text="Type", anchor=tk.W, command=lambda: self._sort_by("type"))
        self.tree.heading("size", text="Size", anchor=tk.E, command=lambda: self._sort_by("size"))
        self.tree.heading("risk", text="Risk", anchor=tk.W, command=lambda: self._sort_by("risk"))
        self.tree.column("path", width=560, minwidth=200, stretch=True)
        self.tree.column("type", width=180, minwidth=80, stretch=False)
        self.tree.column("size", width=110, minwidth=70, stretch=False)
        self.tree.column("risk", width=80, minwidth=60, stretch=False)
        self.tree.tag_configure("caution", foreground="#b36b00")

        vertical = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vertical.set)
        self.tree.grid(row=1, column=0, sticky=tk.NSEW)
        vertical.grid(row=1, column=1, sticky=tk.NS)

        self._context_menu = tk.Menu(self.root, tearoff=0)
        self._context_menu.add_command(label="Open location", command=self._open_location)
        self._context_menu.add_command(label="Copy path", command=self._copy_path)
        self._context_menu.add_separator()
        self._context_menu.add_command(label="Delete selected", command=self._delete_selected)

    def _build_progress_and_status(self, parent: ttk.Frame) -> None:
        self.progress = ttk.Progressbar(parent, mode="determinate", maximum=100)
        self.progress.grid(row=5, column=0, sticky=tk.EW, pady=(0, 3))

        status_row = ttk.Frame(parent)
        status_row.grid(row=6, column=0, sticky=tk.EW)
        status_row.columnconfigure(0, weight=1)
        ttk.Label(status_row, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W).grid(
            row=0, column=0, sticky=tk.EW
        )
        ttk.Label(
            status_row,
            textvariable=self.selection_var,
            relief=tk.SUNKEN,
            anchor=tk.E,
            width=34,
        ).grid(row=0, column=1, sticky=tk.E)

    def _bind_events(self) -> None:
        self.dry_run_var.trace_add("write", self._on_dry_run_change)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Return>", self._on_double_click)
        self.tree.bind("<Button-3>", self._on_context_menu)
        self.tree.bind("<Control-a>", self._select_all_rows)
        self.tree.bind("<Delete>", self._on_delete_key)
        self.root.bind("<F5>", self._start_scan)
        self.root.bind("<Escape>", self._cancel_operation)

    def _browse(self) -> None:
        """Open a folder-selection dialog and update the path entry."""
        directory = filedialog.askdirectory(title="Select root directory")
        if directory:
            self.path_var.set(directory)

    def _check_safe(self) -> None:
        for pattern in CACHE_PATTERNS:
            self.type_vars[pattern.id].set(pattern.is_safe())

    def _uncheck_all(self) -> None:
        for variable in self.type_vars.values():
            variable.set(False)

    def _set_busy(self, busy: bool) -> None:
        """Toggle the UI between busy and idle states."""
        self._busy = busy
        if busy:
            self.progress.configure(mode="indeterminate")
            self.progress.start(60)
        else:
            self.progress.stop()
            self.progress.configure(mode="determinate", value=0)
        self._update_buttons()

    def _update_buttons(self) -> None:
        """Synchronize button states with the current selection and mode."""
        self.scan_btn.state(["disabled"] if self._busy else ["!disabled"])
        self.browse_btn.state(["disabled"] if self._busy else ["!disabled"])
        self.cancel_btn.state(["!disabled"] if self._busy else ["disabled"])

        can_delete = deletion_allowed(
            self.items,
            self._busy,
            self.dry_run_var.get(),
            self._scan_incomplete,
        )
        selected = bool(self.tree.selection())
        self.delete_selected_btn.state(["!disabled"] if can_delete and selected else ["disabled"])
        self.delete_all_btn.state(["!disabled"] if can_delete else ["disabled"])
        has_details = bool(self._last_errors or self._last_skipped) and not self._busy
        self.details_btn.state(["!disabled"] if has_details else ["disabled"])

    def _on_dry_run_change(self, *_args: object) -> None:
        self._update_buttons()

    def _on_tree_select(self, _event: object = None) -> None:
        self._update_buttons()
        selected = self._selected_items()
        if selected:
            total = sum(item.size for item in selected)
            self.selection_var.set(f"Selected {len(selected)} item(s) ({format_size(total)})")
        else:
            self.selection_var.set("")

    # ------------------------------------------------------------------
    # Scan workflow
    # ------------------------------------------------------------------

    def _start_scan(self, _event: object = None) -> str | None:
        """Validate inputs and start the scan in a background thread."""
        if self._busy:
            return None
        root_path = self.path_var.get().strip()
        if not root_path or not os.path.isdir(root_path):
            messagebox.showerror("Error", "Invalid directory path")
            return None

        selected = {pid for pid, var in self.type_vars.items() if var.get()}
        if not selected:
            messagebox.showinfo("Info", "Select at least one cache type")
            return None

        self._cancel.clear()
        self._scan_incomplete = False
        self._last_errors = []
        self._last_skipped = 0
        self.scan_root = os.path.abspath(root_path)
        self.items = []
        self.item_by_iid.clear()
        self.selection_var.set("")
        self.tree.delete(*self.tree.get_children())
        self._set_busy(True)
        self.status_var.set("Scanning...")
        threading.Thread(target=self._scan_worker, args=(root_path, selected), daemon=True).start()
        return "break"

    def _scan_worker(self, root_path: str, selected: set[str]) -> None:
        """Run the scan in a worker thread and post the result to the UI queue."""
        stats = ScanStats()
        last_update = 0.0

        def report_progress(count: int, current: str) -> None:
            nonlocal last_update
            now = time.monotonic()
            if now - last_update >= 0.1:
                last_update = now
                self._queue.put(("progress", count, current))

        try:
            items = scan_directory(
                root_path,
                selected,
                progress=report_progress,
                cancel=self._cancel,
                stats=stats,
            )
        except Exception as exc:  # pylint: disable=broad-except
            self._queue.put(("error", f"Scan failed: {exc}", None))
            return
        self._queue.put(("scan_done", items, stats))

    def _scan_complete(self, items: list[ScanItem], stats: ScanStats) -> None:
        """Populate the tree with scan results and re-enable the UI."""
        self.items = list(items)
        self._scan_incomplete = stats.cancelled
        self._last_errors = list(stats.errors)
        self._last_skipped = stats.skipped
        self._sort_items()
        self._populate_tree()
        self._set_busy(False)

        total = sum(item.size for item in self.items)
        parts = [f"Found {len(self.items)} item(s) ({format_size(total)})"]
        if stats.cancelled:
            parts.insert(0, "Cancelled: partial results, deletion disabled")
        if stats.skipped:
            parts.append(f"skipped {stats.skipped}")
        self.status_var.set(" | ".join(parts))
        self._update_buttons()

    def _populate_tree(self) -> None:
        """Rebuild the tree from :attr:`items`."""
        self.tree.delete(*self.tree.get_children())
        self.item_by_iid.clear()
        self.selection_var.set("")
        for item in self.items:
            pattern = PATTERNS_BY_ID.get(item.pattern_id)
            label = pattern.label if pattern is not None else item.pattern_id
            iid = self.tree.insert(
                "",
                tk.END,
                values=(item.path, label, format_size(item.size), item.risk),
            )
            if item.risk == RISK_CAUTION:
                self.tree.item(iid, tags=("caution",))
            self.item_by_iid[iid] = item

    def _sort_by(self, column: str) -> None:
        """Sort results by a tree column, toggling direction on repeat clicks."""
        if self._sort_column == column:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_column = column
            self._sort_reverse = column == "size"
        self._sort_items()
        self._populate_tree()
        self._update_buttons()

    def _sort_items(self) -> None:
        fields = {
            "path": "path",
            "type": "pattern_id",
            "size": "size",
            "risk": "risk",
        }
        field = fields.get(self._sort_column, "size")
        self.items.sort(key=lambda item: getattr(item, field), reverse=self._sort_reverse)

    # ------------------------------------------------------------------
    # Deletion workflow
    # ------------------------------------------------------------------

    def _selected_items(self) -> list[ScanItem]:
        """Return scan items for the current tree selection."""
        return [self.item_by_iid[iid] for iid in self.tree.selection() if iid in self.item_by_iid]

    def _delete_selected(self) -> None:
        self._confirm_delete(selected_only=True)

    def _delete_all(self) -> None:
        self._confirm_delete(selected_only=False)

    def _confirm_delete(self, selected_only: bool) -> None:
        """Ask for confirmation, then delete in a background thread."""
        if self._busy or self.dry_run_var.get() or self._scan_incomplete:
            return
        if selected_only:
            items = self._selected_items()
            if not items:
                messagebox.showinfo("Info", "Select one or more items first.")
                return
        else:
            items = list(self.items)
            if not items:
                messagebox.showinfo("Info", "Nothing to delete. Run Scan first.")
                return

        total = sum(item.size for item in items)
        use_trash = self.trash_var.get()
        action = "Move to Recycle Bin" if use_trash else "Permanently delete"
        consequence = (
            "Items can be restored from the Recycle Bin."
            if use_trash
            else "This action cannot be undone."
        )
        message = f"{action} {len(items)} item(s) ({format_size(total)})?\n{consequence}"
        if not messagebox.askyesno("Confirm Deletion", message, icon=messagebox.WARNING):
            return

        self._cancel.clear()
        self._deleting = True
        self._set_busy(True)
        self.status_var.set(f"{action}...")
        threading.Thread(
            target=self._delete_worker,
            args=([item.path for item in items], use_trash),
            daemon=True,
        ).start()

    def _delete_worker(self, paths: list[str], use_trash: bool) -> None:
        """Run deletion in a worker thread and post the report to the UI queue."""
        try:
            report = delete_items(
                paths,
                root=self.scan_root,
                use_trash=use_trash,
                cancel=self._cancel,
            )
        except Exception as exc:  # pylint: disable=broad-except
            self._queue.put(("error", f"Delete failed: {exc}", None))
            return
        self._queue.put(("delete_done", report, None))

    def _delete_complete(self, report: DeleteReport) -> None:
        """Update the results tree and show the final status."""
        self._deleting = False
        deleted = set(report.deleted)
        self.items = [item for item in self.items if item.path not in deleted]
        self._populate_tree()
        self._set_busy(False)

        permanent = report.success - report.trashed
        parts = []
        if permanent:
            parts.append(f"Deleted {permanent} item(s)")
        if report.trashed:
            parts.append(f"Moved to Recycle Bin: {report.trashed}")
        if not parts:
            parts.append("Nothing deleted")
        if report.errors:
            parts.append(f"errors: {report.errors}")
        summary = " | ".join(parts)
        self.status_var.set(summary)
        self._update_buttons()

        if report.errors:
            details = "\n".join(report.messages[:10])
            messagebox.showwarning("Completed with errors", f"{summary}\n\n{details}")
        else:
            messagebox.showinfo("Complete", summary)

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------

    def _cancel_operation(self, _event: object = None) -> str | None:
        if not self._busy:
            return None
        self._cancel.set()
        self.status_var.set("Cancelling...")
        return "break"

    def _on_delete_key(self, _event: object = None) -> str:
        self._delete_selected()
        return "break"

    def _select_all_rows(self, _event: object = None) -> str:
        self.tree.selection_set(self.tree.get_children())
        return "break"

    def _on_double_click(self, _event: object = None) -> str:
        self._open_location()
        return "break"

    def _on_context_menu(self, event: tk.Event) -> None:
        iid = self.tree.identify_row(event.y)
        if not iid:
            return
        self.tree.selection_set(iid)
        can_delete = deletion_allowed(
            self.items,
            self._busy,
            self.dry_run_var.get(),
            self._scan_incomplete,
        )
        self._context_menu.entryconfigure(3, state=tk.NORMAL if can_delete else tk.DISABLED)
        self._context_menu.tk_popup(event.x_root, event.y_root)

    def _open_location(self) -> None:
        """Reveal the selected item in the system file manager."""
        selected = self._selected_items()
        if not selected:
            return
        path = selected[0].path
        target = path if os.path.isdir(path) else os.path.dirname(path)
        try:
            if IS_WINDOWS:
                if os.path.isdir(path):
                    subprocess.Popen(  # pylint: disable=consider-using-with
                        ["explorer", os.path.normpath(target)]
                    )
                else:
                    subprocess.Popen(  # pylint: disable=consider-using-with
                        ["explorer", f"/select,{os.path.normpath(path)}"]
                    )
            elif sys.platform == "darwin":
                subprocess.Popen(  # pylint: disable=consider-using-with
                    ["open", target]
                )
            else:
                subprocess.Popen(  # pylint: disable=consider-using-with
                    ["xdg-open", target]
                )
        except OSError as exc:
            messagebox.showerror("Open location", str(exc))

    def _copy_path(self) -> None:
        """Copy the selected path to the clipboard."""
        selected = self._selected_items()
        if not selected:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(selected[0].path)
        self.status_var.set("Path copied to clipboard")

    def _show_details(self) -> None:
        """Show skipped entries and access errors collected by the scan."""
        if not self._last_errors and not self._last_skipped:
            return
        window = tk.Toplevel(self.root)
        window.title("Scan details")
        window.geometry("760x420")
        window.transient(self.root)
        frame = ttk.Frame(window, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        text = tk.Text(frame, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        lines = [f"Skipped entries: {self._last_skipped}", ""]
        lines.extend(self._last_errors or ["No detailed errors recorded."])
        text.insert("1.0", "\n".join(lines))
        text.configure(state=tk.DISABLED)
        ttk.Button(window, text="Close", command=window.destroy).pack(pady=(0, 10))

    def _poll_queue(self) -> None:
        """Drain worker messages and schedule the next poll."""
        try:
            while True:
                kind, payload, extra = self._queue.get_nowait()
                self._handle_message(kind, payload, extra)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    def _handle_message(self, kind: str, payload: object, extra: object) -> None:
        if kind == "progress":
            self.status_var.set(f"Scanning... {payload} dirs: {extra}")
        elif kind == "scan_done":
            self._scan_complete(payload, extra)  # type: ignore[arg-type]
        elif kind == "delete_done":
            self._delete_complete(payload)  # type: ignore[arg-type]
        elif kind == "error":
            self._deleting = False
            self._set_busy(False)
            self.status_var.set(str(payload))
            messagebox.showerror("Error", str(payload))

    def _on_close(self) -> None:
        """Cancel pending work and close the window without writing any files."""
        action = close_action(self._deleting, self._busy)
        if action == "blocked":
            messagebox.showinfo(
                "Deletion in progress",
                "Wait for the current deletion to finish or press Esc to cancel.",
            )
            return
        if action == "confirm" and not messagebox.askyesno(
            "Exit", "Scan is in progress. Cancel and exit?"
        ):
            return
        self._cancel.set()
        self.root.destroy()


def entry_point() -> None:
    """Application entry point."""
    root = tk.Tk()
    CacheEraserApp(root)
    root.mainloop()
