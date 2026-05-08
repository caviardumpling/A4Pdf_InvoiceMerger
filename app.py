from __future__ import annotations

import threading
from pathlib import Path
import tkinter as tk
from tkinter import END, BOTH, LEFT, RIGHT, VERTICAL, X, Y, filedialog, messagebox, ttk
from tkinter import Tk
from tkinter import Listbox

from merger import Mode, merge_invoices_to_a4


APP_VERSION = "v1.0"


class InvoiceMergerApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title(f"发票PDF合并 {APP_VERSION}")
        self.root.minsize(720, 420)

        self.mode_var = tk.StringVar(value="A4_2UP_PORTRAIT")
        self.output_var = tk.StringVar(value=str(Path.cwd() / "merged_a4.pdf"))
        self.status_var = tk.StringVar(value="就绪")
        self.render_var = tk.BooleanVar(value=True)

        main = ttk.Frame(root, padding=12)
        main.pack(fill=BOTH, expand=True)

        left = ttk.Frame(main)
        left.pack(side=LEFT, fill=BOTH, expand=True)

        right = ttk.Frame(main)
        right.pack(side=RIGHT, fill=Y)

        ttk.Label(left, text="已选择的PDF（按顺序合并）").pack(anchor="w")
        list_frame = ttk.Frame(left)
        list_frame.pack(fill=BOTH, expand=True, pady=(6, 0))

        self.listbox = Listbox(list_frame, selectmode="extended")
        self.listbox.pack(side=LEFT, fill=BOTH, expand=True)
        scroll = ttk.Scrollbar(list_frame, orient=VERTICAL, command=self.listbox.yview)
        scroll.pack(side=RIGHT, fill=Y)
        self.listbox.configure(yscrollcommand=scroll.set)

        btns = ttk.Frame(left)
        btns.pack(fill=X, pady=(8, 0))
        ttk.Button(btns, text="添加PDF…", command=self.add_files).pack(side=LEFT)
        ttk.Button(btns, text="移除选中", command=self.remove_selected).pack(side=LEFT, padx=(8, 0))
        ttk.Button(btns, text="清空", command=self.clear_files).pack(side=LEFT, padx=(8, 0))
        ttk.Button(btns, text="上移", command=lambda: self.move_selection(-1)).pack(side=LEFT, padx=(8, 0))
        ttk.Button(btns, text="下移", command=lambda: self.move_selection(1)).pack(side=LEFT, padx=(8, 0))

        ttk.Separator(left).pack(fill=X, pady=12)

        out_frame = ttk.Frame(left)
        out_frame.pack(fill=X)
        ttk.Label(out_frame, text="输出文件").pack(anchor="w")
        out_row = ttk.Frame(out_frame)
        out_row.pack(fill=X, pady=(6, 0))
        self.output_entry = ttk.Entry(out_row, textvariable=self.output_var)
        self.output_entry.pack(side=LEFT, fill=X, expand=True)
        ttk.Button(out_row, text="选择…", command=self.pick_output).pack(side=LEFT, padx=(8, 0))

        ttk.Label(right, text="预设模式").pack(anchor="w")
        ttk.Radiobutton(
            right,
            text="竖版A4：上下两张",
            value="A4_2UP_PORTRAIT",
            variable=self.mode_var,
        ).pack(anchor="w", pady=(6, 0))
        ttk.Radiobutton(
            right,
            text="横版A4：四张(2×2)",
            value="A4_4UP_LANDSCAPE",
            variable=self.mode_var,
        ).pack(anchor="w", pady=(6, 0))

        ttk.Checkbutton(
            right,
            text="兼容模式(结果有错位时勾选)",
            variable=self.render_var,
        ).pack(anchor="w", pady=(10, 0))

        ttk.Separator(right).pack(fill=X, pady=12)
        self.merge_btn = ttk.Button(right, text="开始合并", command=self.start_merge)
        self.merge_btn.pack(fill=X)

        self.progress = ttk.Progressbar(right, mode="determinate")
        self.progress.pack(fill=X, pady=(10, 0))
        ttk.Label(right, textvariable=self.status_var, wraplength=220, justify="left").pack(
            anchor="w", pady=(8, 0)
        )

        self._merge_thread: threading.Thread | None = None

    def add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="选择发票PDF",
            filetypes=[("PDF", "*.pdf"), ("All files", "*.*")],
        )
        for p in paths:
            self.listbox.insert(END, p)

    def remove_selected(self) -> None:
        indices = list(self.listbox.curselection())
        for i in reversed(indices):
            self.listbox.delete(i)

    def clear_files(self) -> None:
        self.listbox.delete(0, END)

    def move_selection(self, delta: int) -> None:
        sel = list(self.listbox.curselection())
        if not sel:
            return

        items = [self.listbox.get(i) for i in range(self.listbox.size())]
        selected_items = [items[i] for i in sel]
        remaining = [items[i] for i in range(len(items)) if i not in sel]

        insertion_index = sel[0] + delta
        insertion_index = max(0, min(len(remaining), insertion_index))
        new_items = remaining[:insertion_index] + selected_items + remaining[insertion_index:]

        self.listbox.delete(0, END)
        for it in new_items:
            self.listbox.insert(END, it)

        for i in range(insertion_index, insertion_index + len(selected_items)):
            self.listbox.selection_set(i)

    def pick_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title="保存合并后的PDF",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
        )
        if path:
            self.output_var.set(path)

    def _set_ui_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.merge_btn.configure(state=state)

    def start_merge(self) -> None:
        if self._merge_thread and self._merge_thread.is_alive():
            return
        inputs = [self.listbox.get(i) for i in range(self.listbox.size())]
        output = self.output_var.get().strip()
        if not inputs:
            messagebox.showwarning("提示", "请先添加PDF文件")
            return
        if not output:
            messagebox.showwarning("提示", "请选择输出文件路径")
            return

        self.progress.configure(value=0)
        self.status_var.set("合并中…")
        self._set_ui_enabled(False)

        mode: Mode = self.mode_var.get()  # type: ignore[assignment]
        render_compat = bool(self.render_var.get())

        def on_progress(p):
            def ui_update() -> None:
                self.progress.configure(maximum=p.total, value=p.current)
                self.status_var.set(f"{p.current}/{p.total}  {Path(p.source_path).name}  第{p.source_page_index + 1}页")

            self.root.after(0, ui_update)

        def worker() -> None:
            try:
                merge_invoices_to_a4(
                    inputs,
                    output,
                    mode=mode,
                    render_compat=render_compat,
                    progress_callback=on_progress,
                )

                def done() -> None:
                    self._set_ui_enabled(True)
                    self.status_var.set("完成")
                    messagebox.showinfo("完成", f"已生成：\n{output}")

                self.root.after(0, done)
            except Exception as e:
                def failed() -> None:
                    self._set_ui_enabled(True)
                    self.status_var.set("失败")
                    messagebox.showerror("错误", str(e))

                self.root.after(0, failed)

        self._merge_thread = threading.Thread(target=worker, daemon=True)
        self._merge_thread.start()


def main() -> None:
    root = Tk()
    try:
        style = ttk.Style(root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
    except Exception:
        pass
    InvoiceMergerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

