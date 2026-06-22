# -*- coding: utf-8 -*-
"""
到期提醒工具 — 检查更新 / 关于 标签页（Notebook Tab Mixin）
展示版本信息、更新检查、README 内容、GitHub 链接。
"""

import os
import sys
import re
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk

from modules.config import C, FONT_FAMILY, APP_VERSION, GITHUB_REPO, check_for_updates


class UpdatePanelMixin:
    """检查更新标签页：版本信息 + 更新检查 + README。"""

    def _build_update_tab(self):
        """构建检查更新标签页。"""
        tab = self.update_tab
        self._up_update_result = None
        self._up_checking = False

        # ── 顶部信息栏 ──
        header = tk.Frame(tab, bg=C.surface, height=70)
        header.pack(fill="x", pady=(0, 8))
        header.pack_propagate(False)
        self._treg(header, bg="surface")

        accent_bar = tk.Frame(header, bg=C.accent, height=3)
        accent_bar.place(x=0, y=0, relwidth=1)

        inner = tk.Frame(header, bg=C.surface)
        inner.pack(expand=True, fill="both", padx=24, pady=14)

        left = tk.Frame(inner, bg=C.surface)
        left.pack(side="left")
        tk.Label(left, text="到期提醒工具", bg=C.surface, fg=C.text,
                 font=(FONT_FAMILY, 16, "bold")).pack(anchor="w")
        self._treg(left, bg="surface", fg="text")
        tk.Label(left, text=f"v{APP_VERSION}  ·  by {GITHUB_REPO.split('/')[0]}",
                 bg=C.surface, fg=C.text2, font=(FONT_FAMILY, 10)).pack(anchor="w", pady=(2, 0))

        right = tk.Frame(inner, bg=C.surface)
        right.pack(side="right")
        from modules.widgets import FlatButton
        self._up_github_btn = FlatButton(
            right, "GitHub 主页", command=self._up_open_github,
            bg=C.accent, fg="white", height=32, width=110,
            font=(FONT_FAMILY, 10, "bold"))
        self._up_github_btn.pack()

        # ── 更新检查卡片 ──
        card = tk.Frame(tab, bg=C.surface, highlightbackground=C.border,
                        highlightthickness=1)
        card.pack(fill="x", padx=12, pady=(0, 8))
        self._treg(card, bg="surface")

        title_row = tk.Frame(card, bg=C.surface)
        title_row.pack(fill="x", padx=16, pady=(12, 4))
        self._treg(title_row, bg="surface")
        tk.Label(title_row, text="软件更新", bg=C.surface, fg=C.text,
                 font=(FONT_FAMILY, 12, "bold")).pack(side="left")
        self._treg(title_row, bg="surface", fg="text")

        info_row = tk.Frame(card, bg=C.surface)
        info_row.pack(fill="x", padx=16, pady=(0, 4))
        self._treg(info_row, bg="surface")
        tk.Label(info_row, text=f"当前版本：v{APP_VERSION}",
                 bg=C.surface, fg=C.text2, font=(FONT_FAMILY, 10)).pack(side="left")

        self._up_status_var = tk.StringVar(value="点击右侧按钮检查是否有新版本")
        self._up_status_lbl = tk.Label(
            info_row, textvariable=self._up_status_var,
            bg=C.surface, fg=C.text3, font=(FONT_FAMILY, 10))
        self._up_status_lbl.pack(side="left", padx=(16, 0))

        btn_row = tk.Frame(card, bg=C.surface)
        btn_row.pack(fill="x", padx=16, pady=(4, 12))
        self._treg(btn_row, bg="surface")

        self._up_check_btn = FlatButton(
            btn_row, "检查更新", command=self._up_do_check,
            bg=C.accent, fg="white", height=32, width=110,
            font=(FONT_FAMILY, 10, "bold"))
        self._up_check_btn.pack(side="left")

        self._up_download_btn = FlatButton(
            btn_row, "下载新版", command=self._up_download_latest,
            bg="#16A34A", fg="white", height=32, width=110,
            font=(FONT_FAMILY, 10, "bold"))
        self._up_download_btn.pack(side="left", padx=(12, 0))
        self._up_download_btn.config(state="disabled")

        # 更新详情区（初始隐藏）
        self._up_detail_frame = tk.Frame(card, bg=C.surface2)
        self._up_detail_text = tk.Text(
            self._up_detail_frame, wrap="word", height=6, relief="flat",
            bg=C.surface2, fg=C.text, font=(FONT_FAMILY, 9),
            padx=10, pady=6, state="disabled", bd=0)
        self._up_detail_text.pack(fill="both", expand=True)

        # ── README 区域 ──
        readme_frame = tk.Frame(tab, bg=C.bg)
        readme_frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        tk.Label(readme_frame, text="项目说明", bg=C.bg, fg=C.text,
                 font=(FONT_FAMILY, 11, "bold")).pack(anchor="w", pady=(0, 4))

        text_container = tk.Frame(readme_frame, bg=C.surface,
                                  highlightbackground=C.border, highlightthickness=1)
        text_container.pack(fill="both", expand=True)
        self._treg(text_container, bg="surface")

        self._up_readme_text = tk.Text(
            text_container, wrap="word", relief="flat",
            bg=C.surface, fg=C.text, font=(FONT_FAMILY, 10),
            padx=16, pady=12, bd=0, state="disabled")
        self._up_readme_text.pack(side="left", fill="both", expand=True)

        vsb = ttk.Scrollbar(text_container, orient="vertical",
                            command=self._up_readme_text.yview)
        vsb.pack(side="right", fill="y")
        self._up_readme_text.configure(yscrollcommand=vsb.set)

        # 文本标签样式
        txt = self._up_readme_text
        txt.tag_configure("h1", font=(FONT_FAMILY, 15, "bold"),
                          foreground=C.accent, spacing1=8, spacing3=4)
        txt.tag_configure("h2", font=(FONT_FAMILY, 12, "bold"),
                          foreground=C.text, spacing1=12, spacing3=4)
        txt.tag_configure("h3", font=(FONT_FAMILY, 11, "bold"),
                          foreground=C.text, spacing1=8, spacing3=2)
        txt.tag_configure("body", font=(FONT_FAMILY, 10),
                          foreground=C.text, spacing1=2, spacing3=2)
        txt.tag_configure("bold", font=(FONT_FAMILY, 10, "bold"))
        txt.tag_configure("code", font=("Consolas", 9),
                          background=C.surface2, foreground=C.accent)
        txt.tag_configure("code_block", font=("Consolas", 9),
                          background=C.surface2, foreground=C.text,
                          lmargin1=12, lmargin2=12, spacing1=4, spacing3=4)
        txt.tag_configure("link", foreground=C.accent,
                          underline=True, font=(FONT_FAMILY, 10))
        txt.tag_configure("bullet", foreground=C.text,
                          lmargin1=20, lmargin2=20)
        txt.tag_configure("quote", foreground=C.text2,
                          font=(FONT_FAMILY, 10, "italic"),
                          lmargin1=16, spacing1=4, spacing3=4)
        txt.tag_configure("separator", foreground=C.border,
                          spacing1=8, spacing3=8)

        self._up_load_readme()

    # ==================================================================
    #  README 渲染
    # ==================================================================

    def _up_load_readme(self):
        """读取并渲染 README.md。"""
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

        txt = self._up_readme_text
        txt.config(state="normal")
        txt.delete("1.0", "end")
        self._up_render_markdown(content)
        txt.config(state="disabled")
        txt.yview_moveto(0)

    def _up_render_markdown(self, text):
        """简易 Markdown → Tkinter Text 渲染。"""
        txt = self._up_readme_text
        lines = text.split("\n")
        in_code_block = False

        for line in lines:
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                txt.insert("end", "\n")
                continue

            if in_code_block:
                txt.insert("end", line + "\n", "code_block")
                continue

            stripped = line.strip()

            if not stripped:
                txt.insert("end", "\n")
                continue

            if stripped in ("---", "***", "___"):
                txt.insert("end", "─" * 60 + "\n", "separator")
                continue

            if stripped.startswith("# "):
                txt.insert("end", stripped[2:] + "\n", "h1")
                continue
            if stripped.startswith("## "):
                txt.insert("end", stripped[3:] + "\n", "h2")
                continue
            if stripped.startswith("### "):
                txt.insert("end", stripped[4:] + "\n", "h3")
                continue

            if stripped.startswith("> "):
                txt.insert("end", stripped[2:] + "\n", "quote")
                continue

            if stripped.startswith("- ") or stripped.startswith("* "):
                txt.insert("end", "•  ", "bullet")
                self._up_insert_inline(stripped[2:], "bullet")
                txt.insert("end", "\n")
                continue

            if len(stripped) > 2 and stripped[0].isdigit() and ". " in stripped[:5]:
                idx = stripped.index(". ")
                num = stripped[:idx + 2]
                rest = stripped[idx + 2:]
                txt.insert("end", f"  {num}  ", "body")
                self._up_insert_inline(rest, "body")
                txt.insert("end", "\n")
                continue

            self._up_insert_inline(stripped, "body")
            txt.insert("end", "\n")

    def _up_insert_inline(self, text, base_tag):
        """处理行内格式：**bold**、`code`、[text](url)。"""
        txt = self._up_readme_text
        pattern = re.compile(
            r'\*\*(.+?)\*\*'
            r'|`(.+?)`'
            r'|\[(.+?)\]\((.+?)\)'
        )
        pos = 0
        for m in pattern.finditer(text):
            if m.start() > pos:
                txt.insert("end", text[pos:m.start()], base_tag)

            if m.group(1):
                txt.insert("end", m.group(1), "bold")
            elif m.group(2):
                txt.insert("end", m.group(2), "code")
            elif m.group(3) and m.group(4):
                link_text = m.group(3)
                link_url = m.group(4)
                tag_name = f"up_link_{id(m)}"
                txt.tag_configure(tag_name, foreground=C.accent, underline=True,
                                  font=(FONT_FAMILY, 10))
                txt.tag_bind(tag_name, "<Button-1>",
                             lambda e, u=link_url: webbrowser.open(u))
                txt.tag_bind(tag_name, "<Enter>",
                             lambda e: txt.config(cursor="hand2"))
                txt.tag_bind(tag_name, "<Leave>",
                             lambda e: txt.config(cursor=""))
                txt.insert("end", link_text, tag_name)

            pos = m.end()

        if pos < len(text):
            txt.insert("end", text[pos:], base_tag)

    # ==================================================================
    #  更新检查
    # ==================================================================

    def _up_do_check(self):
        """点击检查更新按钮。"""
        if self._up_checking:
            return
        self._up_checking = True
        self._up_check_btn.config(state="disabled", text="检查中...")
        self._up_status_var.set("正在连接 GitHub...")
        self._up_status_lbl.config(fg=C.text2)
        threading.Thread(target=self._up_check_worker, daemon=True).start()

    def _up_check_worker(self):
        """后台线程执行更新检查。"""
        result = check_for_updates()
        self._up_update_result = result
        self.after(0, lambda: self._up_on_check_done(result))

    def _up_on_check_done(self, result):
        """检查完成后更新 UI。"""
        self._up_checking = False
        self._up_check_btn.config(state="normal", text="检查更新")

        if "error" in result:
            self._up_status_var.set(f"检查失败：{result['error']}")
            self._up_status_lbl.config(fg=C.danger)
            return

        if result["has_update"]:
            self._up_status_var.set(f"发现新版本：{result['latest']}")
            self._up_status_lbl.config(fg="#16A34A")
            self._up_download_btn.config(state="normal")
            self._up_detail_frame.pack(fill="x", padx=16, pady=(0, 8))
            self._up_detail_text.config(state="normal")
            self._up_detail_text.delete("1.0", "end")
            body = result.get("body", "").strip()
            if body:
                self._up_detail_text.insert("end", f"更新内容：\n{body}")
            else:
                self._up_detail_text.insert("end", "暂无更新说明，请前往 GitHub 查看详情。")
            self._up_detail_text.config(state="disabled")
        else:
            self._up_status_var.set(f"已是最新版本 (v{result['current']})")
            self._up_status_lbl.config(fg=C.text2)
            self._up_download_btn.config(state="disabled")
            self._up_detail_frame.pack_forget()

    def _up_download_latest(self):
        """打开 GitHub Release 下载页。"""
        result = getattr(self, "_up_update_result", None)
        if result and result.get("url"):
            webbrowser.open(result["url"])
        else:
            webbrowser.open(f"https://github.com/{GITHUB_REPO}/releases/latest")

    def _up_open_github(self):
        """打开 GitHub 项目主页。"""
        webbrowser.open(f"https://github.com/{GITHUB_REPO}")
