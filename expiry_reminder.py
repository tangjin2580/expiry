#!/Users/Mr.li/Documents/code/expiry/venv/bin/python3
# -*- coding: utf-8 -*-
"""
到期提醒工具 v5.0
入口文件 — 仅含 UI 构建 & 状态管理，业务逻辑分层在 Mixin 中。
"""

import sys, os, subprocess
import tkinter as tk
from tkinter import ttk
from collections import Counter

# 自修复依赖
for mod, pkg in (("openpyxl", "openpyxl"), ("xlrd", "xlrd")):
    try:
        __import__(mod)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

from modules.config import C, LIGHT_COLORS, DARK_COLORS, FONT_FAMILY, COL_MAP
from modules.widgets import FlatButton
from modules.utils import enable_debug, disable_debug, is_debug_on, log_trace, log_debug

from modules.history_panel import HistoryPanelMixin
from modules.analysis_panel import AnalysisPanelMixin
from modules.file_ops import FileOpsMixin
from modules.notify_panel import NotifyPanelMixin
from modules.robot_sync import RobotSyncMixin


class ExpiryApp(tk.Tk, HistoryPanelMixin, AnalysisPanelMixin, FileOpsMixin, NotifyPanelMixin, RobotSyncMixin):
    def __init__(self):
        super().__init__()
        self.title("到期提醒工具")
        self._set_app_icon()
        self.geometry("1280x840")
        self.minsize(1040, 680)
        self["bg"] = C.bg

        # ---- 数据状态 ----
        self._loaded_path = ""
        self._sheet_headers = ()
        self._sheet_rows = []
        self._result_rows = []
        self._result_detail_rows = []
        self._date_cols = []
        self._failed_rows = []
        self._skip_info = {}
        self._shipped_rows = []
        self._col_map = dict(COL_MAP)
        self._font_size = 13

        # ---- 标志位 ----
        self._loading = False
        self._exporting = False
        self._checking = False
        self._writing = False
        self._theme = "light"
        self._mode = "simple"

        # ---- 映射表 ----
        self._tree_item_map = {}
        self._history_item_map = {}
        self._history_entries = []
        self._current_snapshot_id = ""

        # ---- Debug ----
        self._debug_click_count = 0
        self._debug_click_timer = None

        # ---- 状态恢复 ----
        self._pending_selection_restore = None
        self._suppress_date_col_change = False

        # ---- 定时提醒 ----
        self._notify_schedule_id = None
        self._notify_schedule_running = False

        # ---- 主题注册表（widget -> {bg_role, fg_role}）----
        self._theme_registry = []

        self._build_ui()
        self._apply_mode()
        self._history_entries = self._load_history_entries()
        self._refresh_history_list()
        self._load_last_file()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # =========================================================
    #  UI 构建
    # =========================================================

    # ── 主题注册（类似 Tailwind CSS class）──
    def _treg(self, widget, *, bg=None, fg=None):
        """注册 widget 的主题角色，切换主题时自动按 C.<role> 赋值。"""
        self._theme_registry.append((widget, bg, fg))

    def _set_app_icon(self):
        """加载同目录下的 icon 作为应用图标。"""
        ico_path = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")
        if os.path.exists(ico_path):
            self.iconbitmap(ico_path)

    def _build_ui(self):
        self._init_style()
        self._build_header()
        content = self._build_content()
        self._build_notebook(content)
        self._build_shortcuts()
        self._build_status_bar()

    def _init_style(self):
        s = ttk.Style()
        try: s.theme_use("clam")
        except Exception: pass
        s.configure("Flat.TNotebook", background=C.bg, borderwidth=0)
        s.configure("Flat.TNotebook.Tab", padding=(16, 8), font=(FONT_FAMILY, 11))
        s.map("Flat.TNotebook.Tab",
              background=[("selected", C.surface), ("!selected", C.border)],
              foreground=[("selected", C.accent), ("!selected", C.text2)])
        for name in ("Flat.TEntry", "Flat.TCombobox"):
            s.configure(name, fieldbackground=C.surface2, background=C.surface2)
        s.configure("Flat.TCombobox", bordercolor=C.border, foreground=C.text, padding=(8, 4), relief="solid")
        s.map("Flat.TCombobox",
              fieldbackground=[("readonly", C.surface2)],
              foreground=[("readonly", C.text)],
              selectbackground=[("readonly", C.accent)],
              selectforeground=[("readonly", "white")])
        s.configure("Flat.TCombobox.Listbox",
                    background=C.surface2, foreground=C.text,
                    selectbackground=C.accent, selectforeground="white")
        s.configure("Flat.TEntry", foreground=C.text, borderwidth=1, relief="solid", bordercolor=C.border)
        s.configure("Flat.TCheckbutton", background=C.bg, foreground=C.text, font=(FONT_FAMILY, 11))
        s.configure("Treeview", background=C.surface2, fieldbackground=C.surface2, foreground=C.text,
                     font=(FONT_FAMILY, self._font_size - 2), rowheight=self._font_size * 3)
        s.configure("Treeview.Heading", background=C.border, foreground=C.text,
                     font=(FONT_FAMILY, self._font_size - 1, "bold"))

    def _build_header(self):
        h = tk.Frame(self, bg=C.surface, height=58)
        h.pack(fill="x", side="top"); h.pack_propagate(False)
        self._treg(h, bg="surface")
        # 顶部装饰条用 place 固定，不参与 pack 布局
        accent_bar = tk.Frame(h, bg=C.accent, height=3)
        accent_bar.place(x=0, y=0, relwidth=1)
        title_lbl = tk.Label(h, text="到期提醒工具", bg=C.surface, fg=C.text,
                             font=(FONT_FAMILY, 18, "bold"))
        title_lbl.pack(side="left", padx=(20, 4), pady=14)
        self._treg(title_lbl, bg="surface", fg="text")
        r = tk.Frame(h, bg=C.surface); r.pack(side="right", padx=14, pady=12)
        self._treg(r, bg="surface")
        tk.Label(r, text="字号", bg=C.surface, fg=C.text2, font=(FONT_FAMILY, 10)).pack(side="left", padx=(0, 6))
        self._fs_lbl = tk.Label(r, text=str(self._font_size), bg=C.surface, fg=C.accent,
                                font=(FONT_FAMILY, 11, "bold"), width=3)
        self._fs_lbl.pack(side="left")
        self._treg(self._fs_lbl, bg="surface", fg="accent")
        self._fs_btns = []
        for txt, cmd in (("－", self._fs_down), ("＋", self._fs_up)):
            btn = FlatButton(r, txt, command=cmd, bg=C.bg, fg=C.text, height=28, width=36)
            btn.pack(side="left", padx=2)
            self._fs_btns.append(btn)
        self._theme_btn = FlatButton(r, "🌙", command=self._toggle_theme,
                                     bg=C.bg, fg=C.text, height=28, width=36, font=(FONT_FAMILY, 11))
        self._theme_btn.pack(side="left", padx=(6, 0))
        self._mode_btn = FlatButton(r, "高级", command=self._toggle_mode,
                                    bg=C.bg, fg=C.accent, height=28, width=56, font=(FONT_FAMILY, 10))
        self._mode_btn.pack(side="left", padx=(6, 0))

    def _build_content(self):
        content = tk.Frame(self, bg=C.bg)
        content.pack(fill="both", expand=True, padx=16, pady=12)

        row0 = tk.Frame(content, bg=C.bg); row0.pack(fill="x", pady=(0, 10))
        tk.Label(row0, text="📁", bg=C.bg, fg=C.text2, font=(FONT_FAMILY, 16)).pack(side="left", padx=(0, 6))
        self.path_var = tk.StringVar()
        ttk.Entry(row0, textvariable=self.path_var, style="Flat.TEntry",
                  font=(FONT_FAMILY, self._font_size)).pack(side="left", fill="x", expand=True)

        self.open_btn = FlatButton(row0, "浏览文件…", command=self._open_file,
                                   bg=C.accent, fg="white", height=34, width=110); self.open_btn.pack(side="left", padx=(8, 0))
        self.reload_btn = FlatButton(row0, "🔄 重新加载", command=self._reload_current_file,
                                     bg="#0F766E", fg="white", height=34, width=110); self.reload_btn.pack(side="left", padx=(8, 0))
        self.open_folder_btn = FlatButton(row0, "📂 打开文件夹", command=self._open_file_folder,
                                          bg=C.btn2, fg="white", height=34, width=110); self.open_folder_btn.pack(side="left", padx=(8, 0))
        self.open_in_excel_btn = FlatButton(row0, "📊 Excel 中打开", command=self._open_in_excel,
                                            bg="#7C3AED", fg="white", height=34, width=120); self.open_in_excel_btn.pack(side="left", padx=(8, 0))

        self._hint_frames = []
        for txt, pad in (("📂 支持的 Excel 类型：.xlsx / .xlsm / .xltx / .xltm / .xls / .xlt", (0, 2)),
                         ("🕒 支持的日期：2026-02-02、2026/2/2、2026年2月2日、20260202、含时分秒、日期序列号 等，九九QAQ", (0, 6))):
            f = tk.Frame(content, bg=C.bg); f.pack(fill="x", pady=pad)
            tk.Label(f, text=txt, bg=C.bg, fg=C.text3, font=(FONT_FAMILY, 9),
                     anchor="w", wraplength=1240).pack(side="left", fill="x", expand=True)
            self._hint_frames.append(f)
        return content

    def _build_notebook(self, content):
        self.notebook = ttk.Notebook(content, style="Flat.TNotebook")
        self.notebook.pack(fill="both", expand=True)
        self.analysis_tab = tk.Frame(self.notebook, bg=C.bg)
        self.shipping_tab = tk.Frame(self.notebook, bg=C.bg)
        self.history_tab = tk.Frame(self.notebook, bg=C.bg)
        self.notify_tab = tk.Frame(self.notebook, bg=C.bg)
        self.robot_sync_tab = tk.Frame(self.notebook, bg=C.bg)
        self.notebook.add(self.analysis_tab, text="到期分析")
        self.notebook.add(self.shipping_tab, text="送货记录")
        self.notebook.add(self.history_tab, text="历史记录")
        self.notebook.add(self.notify_tab, text="机器人通知")
        self.notebook.add(self.robot_sync_tab, text="机器人同步")
        self._build_analysis_tab()
        self._build_shipping_tab()
        self._build_history_tab()
        self._build_notify_tab()
        self._build_robot_sync_tab()

    def _build_analysis_tab(self):
        bar = tk.Frame(self.analysis_tab, bg=C.surface2, highlightbackground=C.border, highlightthickness=1)
        bar.pack(fill="x", pady=(0, 6))
        self._treg(bar, bg="surface2")

        r1 = tk.Frame(bar, bg=C.surface2); r1.pack(fill="x", padx=16, pady=(10, 4))
        self._treg(r1, bg="surface2")
        tk.Label(r1, text="📅  日期列", bg=C.surface2, fg=C.text2, font=(FONT_FAMILY, 10)).pack(side="left", padx=(0, 6))
        self.date_col_cb = ttk.Combobox(r1, width=28, style="Flat.TCombobox", font=(FONT_FAMILY, self._font_size - 1), state="readonly")
        self.date_col_cb.pack(side="left", padx=(0, 12))
        self.date_col_cb.bind("<<ComboboxSelected>>", self._on_date_col_change)

        tk.Label(r1, text="🔔", bg=C.surface2, fg=C.text2, font=(FONT_FAMILY, 10)).pack(side="left", padx=(0, 4))
        self.days_var = tk.IntVar(value=7)
        ttk.Entry(r1, textvariable=self.days_var, width=5, style="Flat.TEntry",
                  font=(FONT_FAMILY, self._font_size)).pack(side="left", padx=(0, 4))
        tk.Label(r1, text="天", bg=C.surface2, fg=C.text2, font=(FONT_FAMILY, 10)).pack(side="left", padx=(0, 10))

        self._pending_frame = tk.Frame(r1, bg=C.surface2)
        self._pending_frame.pack(side="left", padx=(0, 10))
        self.pending_only = tk.BooleanVar(value=True)
        ttk.Checkbutton(self._pending_frame, text="只看「待发货」", variable=self.pending_only,
                        style="Flat.TCheckbutton").pack()

        self._view_frame = tk.Frame(r1, bg=C.surface2)
        self._view_frame.pack(side="left", padx=(0, 10))
        tk.Label(self._view_frame, text="视图", bg=C.surface2, fg=C.text2, font=(FONT_FAMILY, 10)).pack(side="left", padx=(0, 4))
        self.view_mode_var = tk.StringVar(value="聚合")
        self.view_mode_cb = ttk.Combobox(self._view_frame, width=6, state="readonly", textvariable=self.view_mode_var,
                                         values=("聚合", "明细"), style="Flat.TCombobox",
                                         font=(FONT_FAMILY, self._font_size - 1))
        self.view_mode_cb.pack(side="left")
        self.view_mode_cb.bind("<<ComboboxSelected>>", self._on_view_mode_change)

        self.hint_var = tk.StringVar(value="请选择 Excel 文件")
        self.compare_var = tk.StringVar(value="历史对比：暂无")
        self._compare_lbl = tk.Label(r1, textvariable=self.compare_var, bg=C.surface2, fg=C.accent,
                                      font=(FONT_FAMILY, 10, "bold"))
        self._compare_lbl.pack(side="right", padx=(0, 8))
        self._treg(self._compare_lbl, bg="surface2", fg="accent")
        tk.Label(r1, textvariable=self.hint_var, bg=C.surface2, fg=C.text3, font=(FONT_FAMILY, 10)).pack(side="right", padx=(0, 8))
        self._search_frame = tk.Frame(r1, bg=C.surface2)
        self._search_frame.pack(side="right", padx=(0, 8))
        self._treg(self._search_frame, bg="surface2")
        tk.Label(self._search_frame, text="🔍", bg=C.surface2, fg=C.text2, font=(FONT_FAMILY, 10)).pack(side="left", padx=(12, 2))
        self._search_var = tk.StringVar()
        self._search_entry = ttk.Entry(self._search_frame, textvariable=self._search_var, style="Flat.TEntry",
                                       width=16, font=(FONT_FAMILY, 10))
        self._search_entry.pack(side="left")
        self._search_var.trace_add("write", lambda *_: self._on_search_change())
        self._search_entry.bind("<Escape>", lambda _: self._search_var.set(""))

        r2 = tk.Frame(bar, bg=C.surface2); r2.pack(fill="x", padx=16, pady=(0, 10))
        self._treg(r2, bg="surface2")
        buttons = [
            ("▶  开始分析", self._do_check, C.accent, 126, 12),
            ("修改订单状态", self._edit_selected_status, "#8B5CF6", 126, 11),
            ("🚀 一键送货", self._ship_now, "#16A34A", 144, 11),
            ("导出结果", self._export, C.btn2, 110, 11),
            ("全部展开", self._expand_all_rows, "#0F766E", 98, 10),
            ("全部折叠", self._collapse_all_rows, "#155E75", 98, 10),
            ("⚠ 查看失败", self._show_failed_rows, "#B45309", 100, 10),
        ]
        btn_refs = []
        for i, (text, cmd, bg, w, fs) in enumerate(buttons):
            btn = FlatButton(r2, text, command=cmd, bg=bg, fg="white", height=36, width=w,
                             font=(FONT_FAMILY, fs, "bold"))
            btn.pack(side="left", padx=(0 if i == 0 else 8, 0))
            btn_refs.append(btn)
        self.go_btn, self.edit_status_btn, self.ship_now_btn, self.export_btn, \
            self.expand_btn, self.collapse_btn, self.fail_btn = btn_refs

        # 结果表格
        table_card = tk.Frame(self.analysis_tab, bg=C.surface, highlightbackground=C.border, highlightthickness=1)
        table_card.pack(fill="both", expand=True)
        self._treg(table_card, bg="surface")
        cols = ("状态", "剩余", "日期", "客户", "产品", "订单状态", "备注")
        self.tv = ttk.Treeview(table_card, columns=cols, show="tree headings", height=26, style="Treeview", selectmode="browse")
        self.tv.heading("#0", text="聚合 / 明细"); self.tv.column("#0", width=180, anchor="w")
        for tag, bg, fg in (("expired", "#FDECEC", "#C42B1C"), ("today", "#FDF0C8", "#92400E"),
                            ("soon3", "#FDF0C8", "#B45309"), ("soon7", "#F7EFD8", "#6D4C00")):
            self.tv.tag_configure(tag, background=bg, foreground=fg)
        self.tv.tag_configure("group_customer", background="#2563EB", foreground="white", font=(FONT_FAMILY, 13, "bold"))
        self.tv.tag_configure("group_product", background="#DBEAFE", foreground="#1E40AF", font=(FONT_FAMILY, 12))
        for c, w in zip(cols, [110, 70, 110, 120, 250, 110, 340]):
            self.tv.heading(c, text=c)
            self.tv.column(c, width=w, anchor="w" if c in ("备注", "产品", "客户") else "center")
        self.tv.pack(fill="both", expand=True, side="left")
        self.analysis_vsb = ttk.Scrollbar(table_card, orient="vertical", command=self.tv.yview)
        self.analysis_vsb.pack(side="right", fill="y")
        self.tv.configure(yscrollcommand=self.analysis_vsb.set)

    def _build_history_tab(self):
        top = tk.Frame(self.history_tab, bg=C.bg); top.pack(fill="x", pady=(0, 10))
        hist_buttons = [
            ("刷新记录", self._refresh_history_list, C.accent, 98),
            ("查看快照", self._show_selected_history_snapshot, "#4F46E5", 98),
            ("对比当前", self._compare_selected_history_with_current, "#0EA5E9", 98),
            ("恢复快照状态", self._restore_selected_history, "#DC2626", 118),
            ("🗑 删除选中", self._delete_selected_history, "#B45309", 108),
            ("🧹 清旧(30天)", lambda: self._clear_old_history(30), "#7C2D12", 118),
            ("⚠ 清空全部", self._clear_all_history, "#7F1D1D", 108),
        ]
        refs = []
        for i, (text, cmd, bg, w) in enumerate(hist_buttons):
            btn = FlatButton(top, text, command=cmd, bg=bg, fg="white", height=34, width=w, font=(FONT_FAMILY, 11, "bold"))
            btn.pack(side="left", padx=(0 if i == 0 else 8, 0)); refs.append(btn)
        (self.history_refresh_btn, self.history_view_btn, self.history_compare_btn,
         self.history_restore_btn, self.history_delete_btn,
         self.history_clear_old_btn, self.history_clear_all_btn) = refs

        tk.Label(top, text="🔍", bg=C.bg, fg=C.text2, font=(FONT_FAMILY, 12)).pack(side="left", padx=(16, 4))
        self.history_search_var = tk.StringVar()
        self.history_search_entry = ttk.Entry(top, textvariable=self.history_search_var, style="Flat.TEntry", width=18, font=(FONT_FAMILY, 10))
        self.history_search_entry.pack(side="left", padx=(0, 8))
        self.history_search_var.trace_add("write", lambda *_: self._refresh_history_list())
        self.history_search_entry.bind("<Escape>", lambda _: self.history_search_var.set(""))
        self.history_info_var = tk.StringVar(value="历史记录：暂无")
        tk.Label(top, textvariable=self.history_info_var, bg=C.bg, fg=C.text2, font=(FONT_FAMILY, 10)).pack(side="right")

        pane = tk.PanedWindow(self.history_tab, bg=C.bg, sashwidth=4, sashrelief="flat")
        pane.pack(fill="both", expand=True)

        left = tk.Frame(pane, bg=C.surface, highlightbackground=C.border, highlightthickness=1)
        right = tk.Frame(pane, bg=C.surface, highlightbackground=C.border, highlightthickness=1)
        pane.add(left, width=400); pane.add(right)
        self._treg(left, bg="surface")
        self._treg(right, bg="surface")

        tk.Label(left, text="历史快照", bg=C.surface, fg=C.text, font=(FONT_FAMILY, 12, "bold")).pack(anchor="w", padx=12, pady=(12, 6))
        self.history_tv = ttk.Treeview(left, columns=("时间", "文件", "概览"), show="headings", height=18, selectmode="browse")
        for name, w, a in (("时间", 140, "center"), ("文件", 120, "w"), ("概览", 200, "w")):
            self.history_tv.heading(name, text=name); self.history_tv.column(name, width=w, anchor=a)
        self.history_tv.pack(fill="both", expand=True, padx=12, pady=(0, 12), side="left")
        self.history_tv.bind("<<TreeviewSelect>>", lambda _: self._show_selected_history_snapshot())
        self.history_vsb = ttk.Scrollbar(left, orient="vertical", command=self.history_tv.yview)
        self.history_vsb.pack(side="right", fill="y", pady=(0, 12))
        self.history_tv.configure(yscrollcommand=self.history_vsb.set)

        tk.Label(right, text="快照详情 / 对比结果", bg=C.surface, fg=C.text, font=(FONT_FAMILY, 12, "bold")).pack(anchor="w", padx=12, pady=(12, 6))
        self.history_detail_var = tk.StringVar(value="请选择左侧历史记录")
        tk.Label(right, textvariable=self.history_detail_var, bg=C.surface, fg=C.text2, font=(FONT_FAMILY, 10),
                 justify="left", wraplength=720).pack(anchor="w", padx=12, pady=(0, 8))
        detail_cols = ("类型", "客户", "产品", "历史状态", "当前状态", "日期")
        self.history_detail_tv = ttk.Treeview(right, columns=detail_cols, show="headings", height=18)
        for name, w in zip(detail_cols, [100, 120, 220, 120, 120, 110]):
            self.history_detail_tv.heading(name, text=name); self.history_detail_tv.column(name, width=w,
                anchor="w" if name in ("客户", "产品") else "center")
        self.history_detail_tv.pack(fill="both", expand=True, padx=12, pady=(0, 12), side="left")
        for tag, bg, fg in (("新增", "#DBEAFE", "#1D4ED8"), ("移除", "#FEE2E2", "#B91C1C"),
                            ("订单状态变更", "#FEF3C7", "#B45309"), ("提醒变化", "#EDE9FE", "#6D28D9")):
            self.history_detail_tv.tag_configure(tag, background=bg, foreground=fg)
        self.history_detail_vsb = ttk.Scrollbar(right, orient="vertical", command=self.history_detail_tv.yview)
        self.history_detail_vsb.pack(side="right", fill="y", pady=(0, 12))
        self.history_detail_tv.configure(yscrollcommand=self.history_detail_vsb.set)

    def _build_shipping_tab(self):
        top = tk.Frame(self.shipping_tab, bg=C.bg); top.pack(fill="x", pady=(0, 8))
        self.shipping_refresh_btn = FlatButton(top, "刷新送货记录", command=self._refresh_shipping_tab,
                                               bg=C.accent, fg="white", height=34, width=118, font=(FONT_FAMILY, 11, "bold"))
        self.shipping_refresh_btn.pack(side="left")
        self.shipping_export_btn = FlatButton(top, "导出送货记录", command=self._export_shipping,
                                              bg=C.btn2, fg="white", height=34, width=118, font=(FONT_FAMILY, 11, "bold"))
        self.shipping_export_btn.pack(side="left", padx=(8, 0))
        self.shipping_info_var = tk.StringVar(value="送货记录：暂无")
        tk.Label(top, textvariable=self.shipping_info_var, bg=C.bg, fg=C.text2, font=(FONT_FAMILY, 11)).pack(side="right", padx=(0, 8))

        table = tk.Frame(self.shipping_tab, bg=C.surface, highlightbackground=C.border, highlightthickness=1)
        table.pack(fill="both", expand=True)
        self._treg(table, bg="surface")
        ship_cols = ("送货日期", "客户", "产品", "订单状态", "备注")
        self.shipping_tv = ttk.Treeview(table, columns=ship_cols, show="headings", height=26, style="Treeview", selectmode="browse")
        for c, w in zip(ship_cols, [120, 140, 280, 100, 340]):
            self.shipping_tv.heading(c, text=c); self.shipping_tv.column(c, width=w,
                anchor="w" if c in ("备注", "产品", "客户") else "center")
        self.shipping_tv.tag_configure("shipped", background="#E3F7EA", foreground="#166534")
        self.shipping_tv.pack(fill="both", expand=True, side="left")
        self.shipping_vsb = ttk.Scrollbar(table, orient="vertical", command=self.shipping_tv.yview)
        self.shipping_vsb.pack(side="right", fill="y")
        self.shipping_tv.configure(yscrollcommand=self.shipping_vsb.set)

    def _build_shortcuts(self):
        for key, cmd in (
            ("<Control-o>", self._open_file), ("<Control-O>", self._open_file),
            ("<Control-r>", self._do_check), ("<Control-R>", self._do_check),
            ("<Control-s>", self._export), ("<Control-S>", self._export),
            ("<F5>", self._reload_current_file),
            ("<Delete>", self._delete_selected_history),
            ("<Control-f>", self._focus_search), ("<Control-F>", self._focus_search),
            ("<Control-Shift-S>", self._ship_now), ("<Control-Shift-s>", self._ship_now),
        ):
            self.bind_all(key, lambda _e, c=cmd: (c(), "break")[1])

    def _build_status_bar(self):
        bot = tk.Frame(self, bg=C.surface2, height=46)
        bot.pack(fill="x", side="bottom"); bot.pack_propagate(False)
        self._treg(bot, bg="surface2")
        tk.Frame(bot, bg=C.border, height=1).pack(side="top", fill="x")
        self.status_var = tk.StringVar(value="就绪")
        tk.Label(bot, textvariable=self.status_var, bg=C.surface2, fg=C.text3,
                 font=(FONT_FAMILY, 10)).pack(side="left", padx=16, pady=10, anchor="w")
        self.bottom_export_btn = FlatButton(bot, "💾  导出到桌面", command=self._export,
                                            bg=C.btn2, fg="white", height=32, width=138, font=(FONT_FAMILY, 11))
        self.bottom_export_btn.pack(side="right", padx=16, pady=6)
        self._sync_button_states()

        # 版本号用 place 放到主窗口右下角，不受 pack 布局挤压
        self._version_lbl = tk.Label(self, text="v5.1", bg=C.bg, fg=C.accent,
                                     font=(FONT_FAMILY, 9), cursor="hand2")
        self._version_lbl.place(relx=1.0, rely=1.0, x=-12, y=-6, anchor="se")
        self._version_lbl.bind("<Button-1>", self._on_version_click)
        self._version_lbl.lift()

    def _focus_search(self):
        """Ctrl+F：根据当前标签页聚焦对应搜索框。"""
        tab_id = self.notebook.select()
        if tab_id == str(self.history_tab):
            self._focus_history_search()
        else:
            self.notebook.select(self.analysis_tab)
            try:
                self._search_entry.focus_set()
            except Exception:
                pass

    def _on_version_click(self, _event):
        """点击版本号 5 次切换 DEBUG 日志开关。"""
        if self._debug_click_timer is not None:
            self.after_cancel(self._debug_click_timer)
        self._debug_click_count += 1
        if self._debug_click_count >= 5:
            self._debug_click_count = 0
            self._toggle_debug()
        else:
            # 2 秒内未继续点击则重置计数
            self._debug_click_timer = self.after(2000, self._reset_debug_clicks)

    def _reset_debug_clicks(self):
        self._debug_click_count = 0
        self._debug_click_timer = None

    def _toggle_debug(self):
        if is_debug_on():
            disable_debug()
            self._version_lbl.config(text="v5.1", fg=C.accent)
            self.status_var.set("DEBUG 日志已关闭")
        else:
            enable_debug()
            self._version_lbl.config(text="v5.1 [DEBUG]", fg="#DC2626")
            from config import LOG_FILE
            self.status_var.set("🔍 DEBUG 日志已开启 → " + LOG_FILE)

    # =========================================================
    #  搜索 / 主题切换
    # =========================================================

    def _on_search_change(self):
        """防抖搜索：300ms 后过滤结果树。"""
        keyword = self._search_var.get().strip().lower()
        if hasattr(self, "_search_timer") and self._search_timer:
            self.after_cancel(self._search_timer)
        self._search_timer = self.after(300, lambda: self._filter_result_tree(keyword))

    # =========================================================
    #  简洁 / 高级模式
    # =========================================================

    # 需切换的控件列在各自的分组中，pack_forget 时直接 forget，恢复时显式 pack。
    # 关键：pack 的 kwargs 必须与 _build_ui 中完全一致。

    def _toggle_mode(self):
        old = self._mode
        self._mode = "simple" if old == "advanced" else "advanced"
        log_trace(f"[MODE] 切换: {old} → {self._mode}")
        self._apply_mode()

    def _apply_mode(self):
        import traceback, time as _time
        _t0 = _time.time()
        is_simple = self._mode == "simple"
        log_trace(f"[MODE] _apply_mode 开始 is_simple={is_simple} mode_btn_text={self._mode_btn._text!r}")

        # ---- 诊断：记录操作前各 widget 的 pack 状态 ----
        def _widget_state(w):
            try:
                mgr = w.winfo_manager()
                mapped = w.winfo_ismapped()
                return f"mgr={mgr} mapped={mapped}"
            except Exception:
                return "mgr=? mapped=?"

        try:
            self._mode_btn.config(text="高级" if is_simple else "简洁",
                                  fg=C.accent if is_simple else C.text)
            log_trace(f"  [BTN] config done → text={self._mode_btn._text!r} fg={self._mode_btn._fg!r}")

            def _hide(name, w):
                st_before = _widget_state(w)
                try:
                    w.pack_forget()
                    st_after = _widget_state(w)
                    log_trace(f"  [hide] {name} before=({st_before}) after=({st_after})")
                except Exception as e:
                    log_trace(f"  [hide] {name} 失败: {e!r}\n{traceback.format_exc()}")

            def _show(name, w, **kw):
                st_before = _widget_state(w)
                try:
                    w.pack(**kw)
                    st_after = _widget_state(w)
                    log_trace(f"  [show] {name} before=({st_before}) after=({st_after}) kw={kw}")
                except Exception as e:
                    log_trace(f"  [show] {name} 失败: {e!r}\n{traceback.format_exc()}")

            nb_tabs_before = [self.notebook.tab(i, "text") for i in range(self.notebook.index("end"))]
            log_trace(f"  [NB] tabs before={nb_tabs_before}")

            if is_simple:
                log_trace("[MODE] >>> 切换到简洁模式")
                _hide("open_folder_btn", self.open_folder_btn)
                _hide("open_in_excel_btn", self.open_in_excel_btn)
                for i, f in enumerate(self._hint_frames):
                    _hide(f"hint_frame[{i}]", f)
                _hide("_pending_frame", self._pending_frame)
                _hide("_compare_lbl", self._compare_lbl)
                _hide("edit_status_btn", self.edit_status_btn)
                _hide("expand_btn", self.expand_btn)
                _hide("collapse_btn", self.collapse_btn)
                _hide("fail_btn", self.fail_btn)
                _hide("bottom_export_btn", self.bottom_export_btn)
                try:
                    self.notebook.hide(self.shipping_tab)
                    log_trace("  [hide] shipping_tab OK")
                except Exception as e:
                    log_trace(f"  [hide] shipping_tab 失败: {e!r}\n{traceback.format_exc()}")
                try:
                    self.notebook.hide(self.history_tab)
                    log_trace("  [hide] history_tab OK")
                except Exception as e:
                    log_trace(f"  [hide] history_tab 失败: {e!r}\n{traceback.format_exc()}")
                try:
                    self.notebook.hide(self.notify_tab)
                    log_trace("  [hide] notify_tab OK")
                except Exception as e:
                    log_trace(f"  [hide] notify_tab 失败: {e!r}\n{traceback.format_exc()}")
                try:
                    self.notebook.hide(self.robot_sync_tab)
                    log_trace("  [hide] robot_sync_tab OK")
                except Exception as e:
                    log_trace(f"  [hide] robot_sync_tab 失败: {e!r}\n{traceback.format_exc()}")
                self.view_mode_var.set("明细")
            else:
                log_trace("[MODE] >>> 切换到高级模式")
                _show("open_folder_btn", self.open_folder_btn, side="left", padx=(8, 0))
                _show("open_in_excel_btn", self.open_in_excel_btn, side="left", padx=(8, 0))
                for i, f in enumerate(self._hint_frames):
                    _show(f"hint_frame[{i}]", f, fill="x", pady=(0, 2) if i == 0 else (0, 6))
                _show("_pending_frame", self._pending_frame, side="left", padx=(0, 10))
                _show("_compare_lbl", self._compare_lbl, side="right", padx=(0, 8))
                _show("edit_status_btn", self.edit_status_btn, side="left", padx=(8, 0))
                _show("expand_btn", self.expand_btn, side="left", padx=(8, 0))
                _show("collapse_btn", self.collapse_btn, side="left", padx=(8, 0))
                _show("fail_btn", self.fail_btn, side="left", padx=(8, 0))
                _show("bottom_export_btn", self.bottom_export_btn, side="right", padx=16, pady=6)
                try:
                    self.notebook.add(self.shipping_tab, text="送货记录")
                    log_trace("  [show] shipping_tab OK")
                except Exception as e:
                    log_trace(f"  [show] shipping_tab 失败: {e!r}\n{traceback.format_exc()}")
                try:
                    self.notebook.add(self.history_tab, text="历史记录")
                    log_trace("  [show] history_tab OK")
                except Exception as e:
                    log_trace(f"  [show] history_tab 失败: {e!r}\n{traceback.format_exc()}")
                try:
                    self.notebook.add(self.notify_tab, text="机器人通知")
                    log_trace("  [show] notify_tab OK")
                except Exception as e:
                    log_trace(f"  [show] notify_tab 失败: {e!r}\n{traceback.format_exc()}")
                try:
                    self.notebook.add(self.robot_sync_tab, text="机器人同步")
                    log_trace("  [show] robot_sync_tab OK")
                except Exception as e:
                    log_trace(f"  [show] robot_sync_tab 失败: {e!r}\n{traceback.format_exc()}")
                self.view_mode_var.set("聚合")

            # ---- 诊断：操作后验证 ----
            nb_tabs_after = [self.notebook.tab(i, "text") for i in range(self.notebook.index("end"))]
            log_trace(f"  [NB] tabs after={nb_tabs_after}")
            # 抽检几个关键控件的最终状态
            for name, w in [("open_folder_btn", self.open_folder_btn),
                            ("bottom_export_btn", self.bottom_export_btn),
                            ("edit_status_btn", self.edit_status_btn)]:
                log_trace(f"  [FINAL] {name} {_widget_state(w)}")
            log_trace(f"  [FINAL] view_mode_var={self.view_mode_var.get()!r}")
            log_trace(f"[MODE] _apply_mode 完成 (耗时 {_time.time() - _t0:.3f}s)")
        except Exception as e:
            log_trace(f"[MODE] _apply_mode 顶层异常: {e!r}\n{traceback.format_exc()}")
        finally:
            self._sync_button_states()

    def _toggle_theme(self):
        old = self._theme
        self._theme = "dark" if old == "light" else "light"
        log_trace(f"[THEME] 切换: {old} → {self._theme}")
        self._apply_theme()

    def _apply_theme(self):
        """更新 C 色板 → 先遍历 Frame 设基色 → 再配置 FlatButton → 注册表覆盖 → ttk 样式 → tree 标签。"""
        is_dark = self._theme == "dark"
        log_trace(f"[THEME] is_dark={is_dark} registry={len(self._theme_registry)}")
        colors = DARK_COLORS if is_dark else LIGHT_COLORS
        for k, v in colors.items():
            setattr(C, k, v)

        self["bg"] = C.bg

        # ── 1. 必须先遍历树：更新所有 Frame/Label 的背景色，
        #        这样后续 FlatButton.draw() 读取 self.master.cget("bg") 时才能拿到新色 ──
        self._theme_walk(self)

        # ── 1b. 非 FlatButton 单独配置 ──
        self._theme_btn.config(text="☀️" if is_dark else "🌙", bg=C.bg, fg=C.text)
        self._mode_btn.config(bg=C.bg, fg=C.accent if self._mode == "simple" else C.text)
        self._version_lbl.config(bg=C.bg)
        if not is_debug_on():
            self._version_lbl.config(fg=C.accent)

        # ── 2. 刷新 FlatButton（此时父容器背景已是新色，draw() 读到的四角颜色正确） ──
        for btn in self._fs_btns:
            btn.config(bg=C.bg, fg=C.text)
        for btn in (self.open_btn, self.go_btn, self.shipping_refresh_btn, self.history_refresh_btn):
            btn.config(bg=C.accent)
        for btn in (self.open_folder_btn, self.export_btn, self.shipping_export_btn, self.bottom_export_btn):
            btn.config(bg=C.btn2)
        # 通知面板按钮重绘（Canvas 背景同步）
        for btn in (self._notify_dingtalk_test_btn, self._notify_wechat_test_btn,
                    self._notify_save_btn, self._notify_send_now_btn,
                    self._notify_toggle_btn, self._notify_clear_log_btn):
            btn.draw()
        # 机器人同步面板按钮重绘
        for btn in (self._rs_dingtalk_test_btn, self._rs_wechat_test_btn,
                    self._rs_save_btn, self._rs_preview_btn, self._rs_send_now_btn,
                    self._rs_toggle_btn, self._rs_clear_log_btn):
            btn.draw()

        # ── 3. 注册表覆盖特定角色 ──
        for w, bg_role, fg_role in self._theme_registry:
            try:
                if bg_role: w.config(bg=getattr(C, bg_role))
                if fg_role: w.config(fg=getattr(C, fg_role))
                if isinstance(w, FlatButton): w.draw()
            except Exception: pass

        # ── 3. ttk 样式 ──
        s = ttk.Style()
        s.configure("Treeview", background=C.surface2, fieldbackground=C.surface2,
                     foreground=C.text, font=(FONT_FAMILY, self._font_size - 2),
                     rowheight=max(30, self._font_size * 3))
        s.configure("Treeview.Heading", background=C.border, foreground=C.text,
                     font=(FONT_FAMILY, self._font_size - 1, "bold"))
        for name in ("Flat.TEntry", "Flat.TCombobox"):
            s.configure(name, fieldbackground=C.surface2, background=C.surface2)
        s.configure("Flat.TCombobox", bordercolor=C.border, foreground=C.text, padding=(8, 4), relief="solid")
        s.map("Flat.TCombobox",
              fieldbackground=[("readonly", C.surface2)],
              foreground=[("readonly", C.text)],
              selectbackground=[("readonly", C.accent)],
              selectforeground=[("readonly", "white")])
        s.configure("Flat.TCombobox.Listbox",
                    background=C.surface2, foreground=C.text,
                    selectbackground=C.accent, selectforeground="white")
        s.configure("Flat.TEntry", foreground=C.text, borderwidth=1, relief="solid", bordercolor=C.border)
        s.configure("Flat.TCheckbutton", background=C.bg, foreground=C.text, font=(FONT_FAMILY, 11))
        s.configure("Flat.TNotebook", background=C.bg, borderwidth=0)
        s.configure("Flat.TNotebook.Tab", padding=(16, 8), font=(FONT_FAMILY, 11))
        s.map("Flat.TNotebook.Tab",
              background=[("selected", C.surface), ("!selected", C.border)],
              foreground=[("selected", C.accent), ("!selected", C.text2)])

        # ── 4. Treeview 行颜色 ──
        expired_bg,  expired_fg  = ("#450A0A", "#F87171") if is_dark else ("#FDECEC", "#C42B1C")
        today_bg,    today_fg    = ("#451A03", "#FBBF24") if is_dark else ("#FDF0C8", "#92400E")
        soon3_bg,    soon3_fg    = ("#422006", "#F59E0B") if is_dark else ("#FDF0C8", "#B45309")
        soon7_bg,    soon7_fg    = ("#1E293B", "#60A5FA") if is_dark else ("#F7EFD8", "#6D4C00")
        shipped_bg,  shipped_fg  = ("#022C22", "#34D399") if is_dark else ("#E3F7EA", "#166534")

        for tv in (self.tv, self.history_tv, self.history_detail_tv, self.shipping_tv, self._notify_log_tv, self._rs_log_tv):
            if tv is self.tv:
                tv.tag_configure("expired", background=expired_bg, foreground=expired_fg)
                tv.tag_configure("today", background=today_bg, foreground=today_fg)
                tv.tag_configure("soon3", background=soon3_bg, foreground=soon3_fg)
                tv.tag_configure("soon7", background=soon7_bg, foreground=soon7_fg)
                if is_dark:
                    tv.tag_configure("group_customer", background="#1D4ED8", foreground="white",
                                     font=(FONT_FAMILY, 13, "bold"))
                    tv.tag_configure("group_product", background="#1E3A5F", foreground="#60A5FA",
                                     font=(FONT_FAMILY, 12))
                else:
                    tv.tag_configure("group_customer", background="#2563EB", foreground="white",
                                     font=(FONT_FAMILY, 13, "bold"))
                    tv.tag_configure("group_product", background="#DBEAFE", foreground="#1E40AF",
                                     font=(FONT_FAMILY, 12))
            if tv is self.shipping_tv:
                tv.tag_configure("shipped", background=shipped_bg, foreground=shipped_fg)
            if tv is self.history_detail_tv:
                tv.tag_configure("新增", background="#1E3A5F" if is_dark else "#DBEAFE",
                                 foreground="#60A5FA" if is_dark else "#1D4ED8")
                tv.tag_configure("移除", background="#450A0A" if is_dark else "#FEE2E2",
                                 foreground="#F87171" if is_dark else "#B91C1C")
                tv.tag_configure("订单状态变更", background=C.warn_bg, foreground=C.warn)
                tv.tag_configure("提醒变化", background="#2E1065" if is_dark else "#EDE9FE",
                                 foreground="#A78BFA" if is_dark else "#6D28D9")
            if tv is self._notify_log_tv:
                tv.tag_configure("ok", background=C.ok_bg, foreground=C.ok)
                tv.tag_configure("fail", background=C.danger_bg, foreground=C.danger)
            if tv is self._rs_log_tv:
                tv.tag_configure("ok", background=C.ok_bg, foreground=C.ok)
                tv.tag_configure("fail", background=C.danger_bg, foreground=C.danger)
                tv.tag_configure("preview", background=C.info_bg, foreground=C.info)
        log_trace(f"[THEME] 完成 bg={C.bg} surface={C.surface} text={C.text}")

    @staticmethod
    def _theme_walk(root):
        """单次递归：Frame 设基色，Label 同时设前景 + 背景（合并原 _theme_walk + _sync_label_bgs）。"""
        for child in root.winfo_children():
            if isinstance(child, (tk.Frame, tk.PanedWindow)):
                try: child.config(bg=C.bg)
                except Exception: pass
                ExpiryApp._theme_walk(child)
            elif isinstance(child, tk.Label):
                try:
                    child.config(fg=C.text, bg=child.master.cget("bg"))
                except Exception:
                    pass
            elif not isinstance(child, FlatButton):
                ExpiryApp._theme_walk(child)

    # =========================================================
    #  字号
    # =========================================================

    def _fs_up(self):
        if self._font_size < 17:
            self._font_size += 2; self._fs_lbl.config(text=str(self._font_size)); self._apply_font()

    def _fs_down(self):
        if self._font_size > 9:
            self._font_size -= 2; self._fs_lbl.config(text=str(self._font_size)); self._apply_font()

    def _apply_font(self):
        sz = self._font_size
        s = ttk.Style()
        s.configure("Treeview", background=C.surface2, fieldbackground=C.surface2, foreground=C.text,
                     font=(FONT_FAMILY, sz - 2), rowheight=max(30, sz * 3))
        s.configure("Treeview.Heading", background=C.border, foreground=C.text, font=(FONT_FAMILY, sz - 1, "bold"))
        for name in ("Flat.TEntry", "Flat.TCombobox"):
            s.configure(name, fieldbackground=C.surface2, background=C.surface2, font=(FONT_FAMILY, sz if name.endswith("Entry") else sz - 1))
        for w in (self.tv, self.history_tv, self.history_detail_tv, self.shipping_tv, self._notify_log_tv, self._rs_log_tv):
            try: w.update()
            except Exception: pass

    # =========================================================
    #  状态管理
    # =========================================================

    def _is_busy(self):
        return self._loading or self._checking or self._exporting or self._writing

    def _sync_button_states(self):
        """防抖：同一帧内多次调用只执行最后一次。"""
        if getattr(self, "_sync_pending", False):
            return
        self._sync_pending = True
        self.after_idle(self._sync_button_states_impl)

    def _sync_button_states_impl(self):
        self._sync_pending = False
        busy = self._is_busy()
        has_file = bool(self._loaded_path)
        results = bool(self._result_rows)
        agg = self.view_mode_var.get() == "聚合"
        sel = self._get_selected_snapshot()
        is_simple = self._mode == "simple"
        log_trace(f"[BTN] sync busy={busy} has_file={has_file} results={results} mode={self._mode} is_simple={is_simple}")

        self.open_btn.config(state="disabled" if busy else "normal")
        self.reload_btn.config(state="disabled" if busy or not has_file else "normal")
        self.go_btn.config(state="disabled" if busy or not has_file else "normal")
        self.ship_now_btn.config(state="disabled" if busy or not results or not has_file else "normal")
        self.export_btn.config(state="disabled" if busy or not results else "normal")

        if not is_simple:
            self.open_folder_btn.config(state="disabled" if not has_file else "normal")
            self.open_in_excel_btn.config(state="disabled" if not has_file else "normal")
            self.edit_status_btn.config(state="disabled" if busy or not results else "normal")
            self.bottom_export_btn.config(state="disabled" if busy or not results else "normal")
            self.expand_btn.config(state="disabled" if busy or not (results and agg) else "normal")
            self.collapse_btn.config(state="disabled" if busy or not (results and agg) else "normal")
            self.fail_btn.config(state="disabled" if busy or not (self._failed_rows or self._skip_info) else "normal")
            self.shipping_refresh_btn.config(state="disabled" if busy else "normal")
            self.shipping_export_btn.config(state="disabled" if not self._shipped_rows else "normal")
            self.history_refresh_btn.config(state="disabled" if busy else "normal")
            self.history_view_btn.config(state="disabled" if sel is None else "normal")
            self.history_compare_btn.config(state="disabled" if busy or sel is None or not self._result_detail_rows else "normal")
            self.history_restore_btn.config(state="disabled" if busy or sel is None else "normal")
            self.history_delete_btn.config(state="disabled" if busy or sel is None else "normal")
            self.history_clear_old_btn.config(state="disabled" if busy else "normal")
            self.history_clear_all_btn.config(state="disabled" if busy else "normal")

    def _priority_key(self, diff):
        return (0, diff) if diff < 0 else ((1, diff) if diff == 0 else (2, diff))

    def _nearest_detail(self, rows):
        return min(rows, key=lambda r: self._priority_key(r["diff"]))

    def _summarize_order_status(self, rows):
        c = Counter((r["order_status"] or "空").strip() or "空" for r in rows)
        return " / ".join(f"{k}{v}" for k, v in c.most_common(3))

    def _summarize_alert(self, rows):
        c = Counter(r["tag"] for r in rows)
        parts = [f"已过期{c['expired']}"] if c["expired"] else []
        if c["today"]: parts.append(f"今天{c['today']}")
        st = c["soon3"] + c["soon7"]
        if st: parts.append(f"即将{st}")
        return " / ".join(parts) if parts else "正常"

    def _on_close(self):
        """窗口关闭时停止所有定时提醒。"""
        if getattr(self, "_notify_schedule_running", False):
            self._notify_schedule_running = False
            if self._notify_schedule_id is not None:
                self.after_cancel(self._notify_schedule_id)
        if getattr(self, "_rs_schedule_running", False):
            self._rs_schedule_running = False
            if self._rs_schedule_id is not None:
                self.after_cancel(self._rs_schedule_id)
        self.destroy()


if __name__ == "__main__":
    ExpiryApp().mainloop()
