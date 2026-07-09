# -*- coding: utf-8 -*-
"""
到期提醒工具 — 简易 Markdown → Tkinter Text 渲染器（update_panel / update_dialog 共享）
"""

import re
import webbrowser


def render_markdown(text_widget, content, font_family, accent_color, text_color, text_color2):
    """将 Markdown 文本渲染到 Tkinter Text 控件中。"""
    lines = content.split("\n")
    in_code_block = False

    for line in lines:
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            text_widget.insert("end", "\n")
            continue

        if in_code_block:
            text_widget.insert("end", line + "\n", "code_block")
            continue

        stripped = line.strip()

        if not stripped:
            text_widget.insert("end", "\n")
            continue

        if stripped in ("---", "***", "___"):
            text_widget.insert("end", "\u2500" * 60 + "\n", "separator")
            continue

        if stripped.startswith("# "):
            text_widget.insert("end", stripped[2:] + "\n", "h1")
            continue
        if stripped.startswith("## "):
            text_widget.insert("end", stripped[3:] + "\n", "h2")
            continue
        if stripped.startswith("### "):
            text_widget.insert("end", stripped[4:] + "\n", "h3")
            continue

        if stripped.startswith("> "):
            text_widget.insert("end", stripped[2:] + "\n", "quote")
            continue

        if stripped.startswith("- ") or stripped.startswith("* "):
            text_widget.insert("end", "\u2022  ", "bullet")
            _insert_inline(text_widget, stripped[2:], "bullet", font_family, accent_color)
            text_widget.insert("end", "\n")
            continue

        if len(stripped) > 2 and stripped[0].isdigit() and ". " in stripped[:5]:
            idx = stripped.index(". ")
            num = stripped[:idx + 2]
            rest = stripped[idx + 2:]
            text_widget.insert("end", f"  {num}  ", "body")
            _insert_inline(text_widget, rest, "body", font_family, accent_color)
            text_widget.insert("end", "\n")
            continue

        _insert_inline(text_widget, stripped, "body", font_family, accent_color)
        text_widget.insert("end", "\n")


def _insert_inline(text_widget, text, base_tag, font_family, accent_color):
    pattern = re.compile(
        r'\*\*(.+?)\*\*'
        r'|`(.+?)`'
        r'|\[(.+?)\]\((.+?)\)'
    )
    pos = 0
    for m in pattern.finditer(text):
        if m.start() > pos:
            text_widget.insert("end", text[pos:m.start()], base_tag)

        if m.group(1):
            text_widget.insert("end", m.group(1), "bold")
        elif m.group(2):
            text_widget.insert("end", m.group(2), "code")
        elif m.group(3) and m.group(4):
            link_text = m.group(3)
            link_url = m.group(4)
            tag_name = f"md_link_{id(m)}"
            text_widget.tag_configure(tag_name, foreground=accent_color, underline=True,
                                      font=(font_family, 10))
            text_widget.tag_bind(tag_name, "<Button-1>",
                                 lambda e, u=link_url: webbrowser.open(u))
            text_widget.tag_bind(tag_name, "<Enter>",
                                 lambda e: text_widget.config(cursor="hand2"))
            text_widget.tag_bind(tag_name, "<Leave>",
                                 lambda e: text_widget.config(cursor=""))
            text_widget.insert("end", link_text, tag_name)

        pos = m.end()

    if pos < len(text):
        text_widget.insert("end", text[pos:], base_tag)
