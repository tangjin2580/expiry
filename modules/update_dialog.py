# -*- coding: utf-8 -*-
"""
到期提醒工具 — 检查更新 / 关于 对话框
展示版本信息、更新检查、README 内容、GitHub 链接。
"""

import os
import sys
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk

from modules.config import C, FONT_FAMILY, APP_VERSION, GITHUB_REPO, check_for_updates


class UpdateDialog(tk.Toplevel):
    """检查更新 + 关于页面。"""

    _instance = None  # 单例：避免重复打开

    def __init__(self, parent):
        # 单例检查
        if UpdateDialog._instance is not None:
            try:
                UpdateDialog._instance.lift()
                UpdateDialog._instance.focus_force()
                return
            except Exception:
                UpdateDialog._instance = None

        super().__init__(parent)
        UpdateDialog._instance = self
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.title("关于 & 检查更新")
        self.geometry("720x640")
        self.minsize(560, 480)
        self.configure(bg=C.bg)

        # 如果有 parent 窗口则设为 transient
        if parent and parent.winfo_viewable():
            self.transient(parent)

        self._parent = parent
        self._update_result = None
        self._checking = False

        self._build_ui()

    def _on_close(self):
        UpdateDialog._instance = None
        self.destroy()

    # ==================================================================
    #  UI
    # ==================================================================

    def _build_ui(self):
        self._build_header()
        self._build_update_card()
        self._build_readme()
        self._build_footer()

    # ── 顶部标题栏 ──
    def _build_header(self):
        h = tk.Frame(self, bg=C.surface, height=80)
        h.pack(fill="x", side="top")
        h.pack_propagate(False)

        # 顶部装饰条
        accent = tk.Frame(h, bg=C.accent, height=3)
        accent.place(x=0, y=0, relwidth=1)

        inner = tk.Frame(h, bg=C.surface)
        inner.pack(expand=True, fill="both", padx=24, pady=16)

        left = tk.Frame(inner, bg=C.surface)
        left.pack(side="left")

        tk.Label(left, text="到期提醒工具", bg=C.surface, fg=C.text,
                 font=(FONT_FAMILY, 18, "bold")).pack(anchor="w")
        tk.Label(left, text=f"v{APP_VERSION}  ·  by {GITHUB_REPO.split('/')[0]}",
                 bg=C.surface, fg=C.text2,
                 font=(FONT_FAMILY, 10)).pack(anchor="w", pady=(2, 0))

        right = tk.Frame(inner, bg=C.surface)
        right.pack(side="right")
        self._github_btn = tk.Button(
            right, text="GitHub 主页", command=self._open_github,
            bg=C.accent, fg="white", relief="flat", padx=16, pady=6,
            font=(FONT_FAMILY, 10, "bold"), cursor="hand2")
        self._github_btn.pack()

    # ── 更新检查卡片 ──
    def _build_update_card(self):
        card = tk.Frame(self, bg=C.surface, highlightbackground=C.border,
                        highlightthickness=1)
        card.pack(fill="x", padx=16, pady=(12, 6))

        title_row = tk.Frame(card, bg=C.surface)
        title_row.pack(fill="x", padx=16, pady=(12, 4))
        tk.Label(title_row, text="软件更新", bg=C.surface, fg=C.text,
                 font=(FONT_FAMILY, 12, "bold")).pack(side="left")

        info_row = tk.Frame(card, bg=C.surface)
        info_row.pack(fill="x", padx=16, pady=(0, 4))
        tk.Label(info_row, text=f"当前版本：v{APP_VERSION}",
                 bg=C.surface, fg=C.text2,
                 font=(FONT_FAMILY, 10)).pack(side="left")

        self._update_status_var = tk.StringVar(value="点击右侧按钮检查是否有新版本")
        self._update_status_lbl = tk.Label(
            info_row, textvariable=self._update_status_var,
            bg=C.surface, fg=C.text3, font=(FONT_FAMILY, 10))
        self._update_status_lbl.pack(side="left", padx=(16, 0))

        btn_row = tk.Frame(card, bg=C.surface)
        btn_row.pack(fill="x", padx=16, pady=(4, 12))

        self._check_btn = tk.Button(
            btn_row, text="检查更新", command=self._do_check,
            bg=C.accent, fg="white", relief="flat", padx=20, pady=6,
            font=(FONT_FAMILY, 10, "bold"), cursor="hand2")
        self._check_btn.pack(side="left")

        self._download_btn = tk.Button(
            btn_row, text="下载新版", command=self._download_latest,
            bg="#16A34A", fg="white", relief="flat", padx=20, pady=6,
            font=(FONT_FAMILY, 10, "bold"), cursor="hand2", state="disabled")
        self._download_btn.pack(side="left", padx=(12, 0))

        # 更新详情区（初始隐藏）
        self._detail_frame = tk.Frame(card, bg=C.surface2)
        self._detail_text = tk.Text(
            self._detail_frame, wrap="word", height=6, relief="flat",
            bg=C.surface2, fg=C.text, font=(FONT_FAMILY, 9),
            padx=10, pady=6, state="disabled", bd=0)
        self._detail_text.pack(fill="both", expand=True)

    # ── README 内容 ──
    def _build_readme(self):
        readme_frame = tk.Frame(self, bg=C.bg)
        readme_frame.pack(fill="both", expand=True, padx=16, pady=(6, 6))

        tk.Label(readme_frame, text="项目说明", bg=C.bg, fg=C.text,
                 font=(FONT_FAMILY, 11, "bold")).pack(anchor="w", pady=(0, 4))

        text_container = tk.Frame(readme_frame, bg=C.surface,
                                  highlightbackground=C.border, highlightthickness=1)
        text_container.pack(fill="both", expand=True)

        self._readme_text = tk.Text(
            text_container, wrap="word", relief="flat",
            bg=C.surface, fg=C.text, font=(FONT_FAMILY, 10),
            padx=16, pady=12, bd=0, state="disabled")
        self._readme_text.pack(side="left", fill="both", expand=True)

        vsb = ttk.Scrollbar(text_container, orient="vertical",
                            command=self._readme_text.yview)
        vsb.pack(side="right", fill="y")
        self._readme_text.configure(yscrollcommand=vsb.set)

        # 配置文本标签
        self._readme_text.tag_configure("h1", font=(FONT_FAMILY, 15, "bold"),
                                        foreground=C.accent, spacing1=8, spacing3=4)
        self._readme_text.tag_configure("h2", font=(FONT_FAMILY, 12, "bold"),
                                        foreground=C.text, spacing1=12, spacing3=4)
        self._readme_text.tag_configure("h3", font=(FONT_FAMILY, 11, "bold"),
                                        foreground=C.text, spacing1=8, spacing3=2)
        self._readme_text.tag_configure("body", font=(FONT_FAMILY, 10),
                                        foreground=C.text, spacing1=2, spacing3=2)
        self._readme_text.tag_configure("bold", font=(FONT_FAMILY, 10, "bold"))
        self._readme_text.tag_configure("code", font=("Consolas", 9),
                                        background=C.surface2, foreground=C.accent)
        self._readme_text.tag_configure("code_block", font=("Consolas", 9),
                                        background=C.surface2, foreground=C.text,
                                        lmargin1=12, lmargin2=12, spacing1=4, spacing3=4)
        self._readme_text.tag_configure("link", foreground=C.accent,
                                        underline=True, font=(FONT_FAMILY, 10))
        self._readme_text.tag_configure("bullet", foreground=C.text,
                                        lmargin1=20, lmargin2=20)
        self._readme_text.tag_configure("quote", foreground=C.text2,
                                        font=(FONT_FAMILY, 10, "italic"),
                                        lmargin1=16, spacing1=4, spacing3=4)
        self._readme_text.tag_configure("separator", foreground=C.border,
                                        spacing1=8, spacing3=8)

        self._load_readme()

    # ── 底部 ──
    def _build_footer(self):
        bot = tk.Frame(self, bg=C.surface2, height=36)
        bot.pack(fill="x", side="bottom")
        bot.pack_propagate(False)
        tk.Frame(bot, bg=C.border, height=1).pack(fill="x")
        tk.Label(bot, text=f"© {GITHUB_REPO}  ·  MIT License",
                 bg=C.surface2, fg=C.text3,
                 font=(FONT_FAMILY, 9)).pack(pady=8)

    # ==================================================================
    #  README 渲染
    # ==================================================================

    def _load_readme(self):
        """读取并渲染 README.md 到文本控件。"""
        if getattr(sys, "frozen", False):
            base = sys._MEIPASS
        else:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        readme_path = os.path.join(base, "README.md")

        try:
            with open(readme_path, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            content = "# 到期提醒工具\n\nREADME.md 文件未找到。"

        self._readme_text.config(state="normal")
        self._readme_text.delete("1.0", "end")
        self._render_markdown(content)
        self._readme_text.config(state="disabled")
        # 滚回顶部
        self._readme_text.yview_moveto(0)

    def _render_markdown(self, text):
        """简易 Markdown → Tkinter Text 渲染。"""
        lines = text.split("\n")
        in_code_block = False

        for line in lines:
            # 代码块
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                if in_code_block:
                    self._readme_text.insert("end", "\n")
                else:
                    self._readme_text.insert("end", "\n")
                continue

            if in_code_block:
                self._readme_text.insert("end", line + "\n", "code_block")
                continue

            stripped = line.strip()

            # 空行
            if not stripped:
                self._readme_text.insert("end", "\n")
                continue

            # 分隔线
            if stripped in ("---", "***", "___"):
                self._readme_text.insert("end", "─" * 60 + "\n", "separator")
                continue

            # 标题
            if stripped.startswith("# "):
                self._readme_text.insert("end", stripped[2:] + "\n", "h1")
                continue
            if stripped.startswith("## "):
                self._readme_text.insert("end", stripped[3:] + "\n", "h2")
                continue
            if stripped.startswith("### "):
                self._readme_text.insert("end", stripped[4:] + "\n", "h3")
                continue

            # 引用
            if stripped.startswith("> "):
                self._readme_text.insert("end", stripped[2:] + "\n", "quote")
                continue

            # 列表项
            if stripped.startswith("- ") or stripped.startswith("* "):
                bullet_text = stripped[2:]
                self._readme_text.insert("end", "•  ", "bullet")
                self._insert_inline(bullet_text, "bullet")
                self._readme_text.insert("end", "\n")
                continue

            # 有序列表
            if len(stripped) > 2 and stripped[0].isdigit() and ". " in stripped[:5]:
                idx = stripped.index(". ")
                num = stripped[:idx + 2]
                rest = stripped[idx + 2:]
                self._readme_text.insert("end", f"  {num}  ", "body")
                self._insert_inline(rest, "body")
                self._readme_text.insert("end", "\n")
                continue

            # 普通文本
            self._insert_inline(stripped, "body")
            self._readme_text.insert("end", "\n")

    def _insert_inline(self, text, base_tag):
        """处理行内格式：**bold**、`code`、[text](url)。"""
        import re
        # 模式：**bold** | `code` | [text](url)
        pattern = re.compile(
            r'\*\*(.+?)\*\*'     # bold
            r'|`(.+?)`'          # code
            r'|\[(.+?)\]\((.+?)\)'  # link
        )
        pos = 0
        for m in pattern.finditer(text):
            # 插入匹配前的普通文本
            if m.start() > pos:
                self._readme_text.insert("end", text[pos:m.start()], base_tag)

            if m.group(1):  # bold
                self._readme_text.insert("end", m.group(1), "bold")
            elif m.group(2):  # code
                self._readme_text.insert("end", m.group(2), "code")
            elif m.group(3) and m.group(4):  # link
                link_text = m.group(3)
                link_url = m.group(4)
                tag_name = f"link_{id(m)}"
                self._readme_text.tag_configure(
                    tag_name, foreground=C.accent, underline=True,
                    font=(FONT_FAMILY, 10))
                self._readme_text.tag_bind(
                    tag_name, "<Button-1>",
                    lambda e, u=link_url: webbrowser.open(u))
                self._readme_text.tag_bind(
                    tag_name, "<Enter>",
                    lambda e: self._readme_text.config(cursor="hand2"))
                self._readme_text.tag_bind(
                    tag_name, "<Leave>",
                    lambda e: self._readme_text.config(cursor=""))
                self._readme_text.insert("end", link_text, tag_name)

            pos = m.end()

        # 剩余文本
        if pos < len(text):
            self._readme_text.insert("end", text[pos:], base_tag)

    # ==================================================================
    #  更新检查
    # ==================================================================

    def _do_check(self):
        """点击检查更新按钮。"""
        if self._checking:
            return
        self._checking = True
        self._check_btn.config(state="disabled", text="检查中...")
        self._update_status_var.set("正在连接 GitHub...")
        self._update_status_lbl.config(fg=C.text2)
        threading.Thread(target=self._check_worker, daemon=True).start()

    def _check_worker(self):
        """在后台线程执行更新检查。"""
        result = check_for_updates()
        self._update_result = result
        self.after(0, lambda: self._on_check_done(result))

    def _on_check_done(self, result):
        """更新检查完成后在主线程更新 UI。"""
        self._checking = False
        self._check_btn.config(state="normal", text="检查更新")

        if "error" in result:
            self._update_status_var.set(f"检查失败：{result['error']}")
            self._update_status_lbl.config(fg=C.danger)
            return

        if result["has_update"]:
            self._update_status_var.set(
                f"发现新版本：{result['latest']}")
            self._update_status_lbl.config(fg="#16A34A")
            self._download_btn.config(state="normal")
            # 显示更新详情
            self._detail_frame.pack(fill="x", padx=16, pady=(0, 8))
            self._detail_text.config(state="normal")
            self._detail_text.delete("1.0", "end")
            body = result.get("body", "").strip()
            if body:
                self._detail_text.insert("end", f"更新内容：\n{body}")
            else:
                self._detail_text.insert("end", "暂无更新说明，请前往 GitHub 查看详情。")
            self._detail_text.config(state="disabled")
        else:
            self._update_status_var.set(
                f"已是最新版本 (v{result['current']})")
            self._update_status_lbl.config(fg=C.text2)
            self._download_btn.config(state="disabled")
            self._detail_frame.pack_forget()

    def _download_latest(self):
        """打开 GitHub Release 下载页。"""
        if self._update_result and self._update_result.get("url"):
            webbrowser.open(self._update_result["url"])
        else:
            webbrowser.open(
                f"https://github.com/{GITHUB_REPO}/releases/latest")

    def _open_github(self):
        """打开 GitHub 项目主页。"""
        webbrowser.open(f"https://github.com/{GITHUB_REPO}")
