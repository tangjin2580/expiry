# -*- coding: utf-8 -*-
"""
到期提醒工具 — 机器人通知 Mixin（钉钉 / 企业微信 Webhook）
"""

import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from modules.config import C, NOTIFY_CONFIG_FILE, FONT_FAMILY
from modules.utils import log_debug, log_trace
from modules.widgets import FlatButton
from modules.webhook_base import (
    do_webhook_request, build_webhook_payload,
    check_response_success, load_json_config,
    save_json_config, parse_mobiles,
)

_NOTIFY_DEFAULTS = {
    "dingtalk_url": "",
    "wechat_url": "",
    "interval_minutes": 30,
    "advance_days": 7,
    "at_mobiles": "",
    "at_all": False,
}


class NotifyPanelMixin:
    """钉钉 / 企业微信机器人通知面板。"""

    def _load_notify_config(self):
        return load_json_config(NOTIFY_CONFIG_FILE, _NOTIFY_DEFAULTS)

    def _save_notify_config(self):
        cfg = {
            "dingtalk_url": self._notify_dingtalk_var.get().strip(),
            "wechat_url": self._notify_wechat_var.get().strip(),
            "interval_minutes": self._notify_interval_var.get(),
            "advance_days": self._notify_days_var.get(),
            "at_mobiles": self._notify_at_mobiles_var.get().strip(),
            "at_all": self._notify_at_all_var.get(),
        }
        save_json_config(NOTIFY_CONFIG_FILE, cfg)
        log_debug(f"[NOTIFY] 配置已保存: {NOTIFY_CONFIG_FILE}")

    def _build_notify_tab(self):
        """构建机器人通知标签页。"""
        cfg = self._load_notify_config()

        header = tk.Frame(self.notify_tab, bg=C.bg)
        header.pack(fill="x", pady=(0, 10))
        tk.Label(header, text="🤖  机器人通知配置", bg=C.bg, fg=C.text,
                 font=(FONT_FAMILY, 14, "bold")).pack(side="left", padx=16, pady=8)

        card = tk.Frame(self.notify_tab, bg=C.surface, highlightbackground=C.border,
                        highlightthickness=1)
        card.pack(fill="x", padx=12, pady=(0, 10))
        self._treg(card, bg="surface")

        r1 = tk.Frame(card, bg=C.surface)
        r1.pack(fill="x", padx=16, pady=(14, 6))
        tk.Label(r1, text="📌  钉钉 Webhook", bg=C.surface, fg=C.text,
                 font=(FONT_FAMILY, 11, "bold"), width=18, anchor="w").pack(side="left")
        self._notify_dingtalk_var = tk.StringVar(value=cfg.get("dingtalk_url", ""))
        ttk.Entry(r1, textvariable=self._notify_dingtalk_var, style="Flat.TEntry",
                  font=(FONT_FAMILY, 10)).pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._notify_dingtalk_test_btn = FlatButton(
            r1, "测试发送", command=lambda: self._test_send("dingtalk"),
            bg="#0EA5E9", fg="white", height=30, width=86, font=(FONT_FAMILY, 10, "bold"))
        self._notify_dingtalk_test_btn.pack(side="left")

        r2 = tk.Frame(card, bg=C.surface)
        r2.pack(fill="x", padx=16, pady=(6, 6))
        tk.Label(r2, text="💬  企业微信 Webhook", bg=C.surface, fg=C.text,
                 font=(FONT_FAMILY, 11, "bold"), width=18, anchor="w").pack(side="left")
        self._notify_wechat_var = tk.StringVar(value=cfg.get("wechat_url", ""))
        ttk.Entry(r2, textvariable=self._notify_wechat_var, style="Flat.TEntry",
                  font=(FONT_FAMILY, 10)).pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._notify_wechat_test_btn = FlatButton(
            r2, "测试发送", command=lambda: self._test_send("wechat"),
            bg="#22C55E", fg="white", height=30, width=86, font=(FONT_FAMILY, 10, "bold"))
        self._notify_wechat_test_btn.pack(side="left")

        r3 = tk.Frame(card, bg=C.surface)
        r3.pack(fill="x", padx=16, pady=(6, 14))
        tk.Label(r3, text="⏱  提醒间隔", bg=C.surface, fg=C.text2,
                 font=(FONT_FAMILY, 10)).pack(side="left", padx=(0, 4))
        self._notify_interval_var = tk.IntVar(value=cfg.get("interval_minutes", 30))
        ttk.Entry(r3, textvariable=self._notify_interval_var, width=5, style="Flat.TEntry",
                  font=(FONT_FAMILY, 11)).pack(side="left", padx=(0, 4))
        tk.Label(r3, text="分钟", bg=C.surface, fg=C.text2,
                 font=(FONT_FAMILY, 10)).pack(side="left", padx=(0, 20))

        tk.Label(r3, text="🔔  提前提醒", bg=C.surface, fg=C.text2,
                 font=(FONT_FAMILY, 10)).pack(side="left", padx=(0, 4))
        self._notify_days_var = tk.IntVar(value=cfg.get("advance_days", 7))
        ttk.Entry(r3, textvariable=self._notify_days_var, width=5, style="Flat.TEntry",
                  font=(FONT_FAMILY, 11)).pack(side="left", padx=(0, 4))
        tk.Label(r3, text="天", bg=C.surface, fg=C.text2,
                 font=(FONT_FAMILY, 10)).pack(side="left", padx=(0, 20))

        r_at = tk.Frame(card, bg=C.surface)
        r_at.pack(fill="x", padx=16, pady=(6, 14))
        tk.Label(r_at, text="📞  @成员手机号", bg=C.surface, fg=C.text2,
                 font=(FONT_FAMILY, 10)).pack(side="left", padx=(0, 4))
        self._notify_at_mobiles_var = tk.StringVar(value=cfg.get("at_mobiles", ""))
        ttk.Entry(r_at, textvariable=self._notify_at_mobiles_var, style="Flat.TEntry",
                  font=(FONT_FAMILY, 10)).pack(side="left", fill="x", expand=True, padx=(0, 12))
        self._notify_at_all_var = tk.BooleanVar(value=cfg.get("at_all", False))
        ttk.Checkbutton(r_at, text="@所有人", variable=self._notify_at_all_var,
                        style="Flat.TCheckbutton").pack(side="left")

        self._notify_save_btn = FlatButton(
            r3, "💾  保存配置", command=self._save_notify_config,
            bg=C.accent, fg="white", height=32, width=110, font=(FONT_FAMILY, 10, "bold"))
        self._notify_save_btn.pack(side="left", padx=(0, 8))

        bar = tk.Frame(self.notify_tab, bg=C.bg)
        bar.pack(fill="x", padx=12, pady=(0, 10))

        self._notify_send_now_btn = FlatButton(
            bar, "📤  立即发送通知", command=self._send_now,
            bg="#7C3AED", fg="white", height=36, width=150, font=(FONT_FAMILY, 11, "bold"))
        self._notify_send_now_btn.pack(side="left", padx=(0, 8))

        self._notify_toggle_btn = FlatButton(
            bar, "▶  开启定时提醒", command=self._toggle_schedule,
            bg="#16A34A", fg="white", height=36, width=150, font=(FONT_FAMILY, 11, "bold"))
        self._notify_toggle_btn.pack(side="left", padx=(0, 8))

        self._notify_status_var = tk.StringVar(value="定时提醒：未开启")
        tk.Label(bar, textvariable=self._notify_status_var, bg=C.bg, fg=C.text2,
                 font=(FONT_FAMILY, 10)).pack(side="left", padx=(8, 0))

        log_card = tk.Frame(self.notify_tab, bg=C.surface, highlightbackground=C.border,
                            highlightthickness=1)
        log_card.pack(fill="both", expand=True, padx=12, pady=(0, 6))
        self._treg(log_card, bg="surface")

        log_header = tk.Frame(log_card, bg=C.surface)
        log_header.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(log_header, text="📋  发送记录", bg=C.surface, fg=C.text,
                 font=(FONT_FAMILY, 11, "bold")).pack(side="left")
        self._notify_clear_log_btn = FlatButton(
            log_header, "清空", command=self._clear_notify_log,
            bg=C.btn2, fg="white", height=26, width=60, font=(FONT_FAMILY, 9))
        self._notify_clear_log_btn.pack(side="right")

        log_cols = ("时间", "平台", "状态", "内容摘要")
        self._notify_log_tv = ttk.Treeview(
            log_card, columns=log_cols, show="headings", height=10, selectmode="browse")
        for c, w, a in [("时间", 140, "center"), ("平台", 80, "center"),
                         ("状态", 70, "center"), ("内容摘要", 600, "w")]:
            self._notify_log_tv.heading(c, text=c)
            self._notify_log_tv.column(c, width=w, anchor=a)
        self._notify_log_tv.tag_configure("ok", background=C.ok_bg, foreground=C.ok)
        self._notify_log_tv.tag_configure("fail", background=C.danger_bg, foreground=C.danger)
        self._notify_log_tv.pack(fill="both", expand=True, padx=12, pady=(0, 12), side="left")
        self._notify_log_vsb = ttk.Scrollbar(
            log_card, orient="vertical", command=self._notify_log_tv.yview)
        self._notify_log_vsb.pack(side="right", fill="y", pady=(0, 12))
        self._notify_log_tv.configure(yscrollcommand=self._notify_log_vsb.set)

        self._notify_schedule_id = None
        self._notify_schedule_running = False

    def _build_notify_message(self):
        """根据分析结果构建通知文本，越临近越靠前。"""
        rows = getattr(self, "_result_detail_rows", [])
        if not rows:
            return None
        days_limit = self._notify_days_var.get()
        filtered = [r for r in rows if r["diff"] <= days_limit]
        if not filtered:
            return None

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [f"📦 发货提醒 ({now_str})", f"共 {len(filtered)} 条待处理：", ""]

        for i, r in enumerate(filtered, 1):
            if r["diff"] < 0:
                urgency = "🔴 已过期"
            elif r["diff"] == 0:
                urgency = "🟠 今天"
            elif r["diff"] <= 3:
                urgency = "🟡 紧急"
            else:
                urgency = "🔵 提醒"

            qty_str = f" x{r['quantity']}" if r.get("quantity") else ""
            line = f"{i}. [{urgency}] {r['customer']} | {r['date']} | {r['product']}{qty_str}"
            lines.append(line)

        return "\n".join(lines)

    def _send_to_platform(self, platform, message, is_test=False):
        """发送到指定平台（在工作线程中）。"""
        at_mobiles = parse_mobiles(self._notify_at_mobiles_var.get().strip())
        at_all = self._notify_at_all_var.get()

        if platform == "dingtalk":
            url = self._notify_dingtalk_var.get().strip()
        elif platform == "wechat":
            url = self._notify_wechat_var.get().strip()
        else:
            return

        if not url:
            self.after(0, lambda: self._log_notify_result(platform, False, "未配置 Webhook 地址"))
            return

        payload = build_webhook_payload(platform, message, at_mobiles, at_all)
        ok, resp_body = do_webhook_request(url, payload)
        success = check_response_success(platform, ok, resp_body)

        label = "测试" if is_test else "通知"
        summary = f"[{label}] 发送成功" if success else f"[{label}] 失败: {resp_body[:100]}"
        self.after(0, lambda: self._log_notify_result(platform, success, summary))
        log_debug(f"[NOTIFY] {platform} {label}: ok={success}, resp={resp_body[:200]}")

    def _log_notify_result(self, platform, success, summary):
        """在发送记录 Treeview 中追加一条。"""
        now_str = datetime.now().strftime("%H:%M:%S")
        plat_name = "钉钉" if platform == "dingtalk" else "企业微信"
        tag = "ok" if success else "fail"
        status = "✅" if success else "❌"
        self._notify_log_tv.insert("", "end", values=(now_str, plat_name, status, summary), tags=(tag,))
        children = self._notify_log_tv.get_children()
        if children:
            self._notify_log_tv.see(children[-1])
        self.status_var.set(summary)

    def _clear_notify_log(self):
        for item in self._notify_log_tv.get_children():
            self._notify_log_tv.delete(item)

    def _test_send(self, platform):
        """测试发送。"""
        test_msg = "🤖 到期提醒工具 — 测试消息\n\n如果你收到这条消息，说明 Webhook 配置正确！"
        log_debug(f"[NOTIFY] 测试发送: {platform}")
        threading.Thread(target=self._send_to_platform, args=(platform, test_msg, True),
                         daemon=True).start()

    def _send_now(self):
        """立即发送一次通知到所有已配置的平台。"""
        msg = self._build_notify_message()
        if msg is None:
            self.status_var.set("没有需要提醒的待发货订单")
            messagebox.showinfo("通知", "没有需要提醒的待发货订单", parent=self)
            return
        log_debug(f"[NOTIFY] 立即发送, 内容长度={len(msg)}")
        dingtalk_url = self._notify_dingtalk_var.get().strip()
        wechat_url = self._notify_wechat_var.get().strip()
        if dingtalk_url:
            threading.Thread(target=self._send_to_platform, args=("dingtalk", msg, False),
                             daemon=True).start()
        if wechat_url:
            threading.Thread(target=self._send_to_platform, args=("wechat", msg, False),
                             daemon=True).start()
        if not dingtalk_url and not wechat_url:
            self.status_var.set("请先配置 Webhook 地址")
            messagebox.showwarning("提示", "请先配置钉钉或企业微信的 Webhook 地址", parent=self)

    def _toggle_schedule(self):
        """开启/关闭定时提醒。"""
        if self._notify_schedule_running:
            self._stop_schedule()
        else:
            self._start_schedule()

    def _start_schedule(self):
        """开启定时提醒。"""
        dingtalk_url = self._notify_dingtalk_var.get().strip()
        wechat_url = self._notify_wechat_var.get().strip()
        if not dingtalk_url and not wechat_url:
            messagebox.showwarning("提示", "请先配置至少一个 Webhook 地址", parent=self)
            return
        self._save_notify_config()
        self._notify_schedule_running = True
        self._notify_toggle_btn.config(text="⏹  停止定时提醒", bg="#DC2626")
        interval = self._notify_interval_var.get()
        self._notify_status_var.set(f"定时提醒：运行中（每 {interval} 分钟）")
        self._schedule_tick()
        log_debug(f"[NOTIFY] 定时提醒已开启, 间隔={interval}分钟")

    def _stop_schedule(self):
        """停止定时提醒。"""
        self._notify_schedule_running = False
        if self._notify_schedule_id is not None:
            self.after_cancel(self._notify_schedule_id)
            self._notify_schedule_id = None
        self._notify_toggle_btn.config(text="▶  开启定时提醒", bg="#16A34A")
        self._notify_status_var.set("定时提醒：已停止")
        log_debug("[NOTIFY] 定时提醒已停止")

    def _schedule_tick(self):
        """定时回调：发送通知 → 调度下一次。"""
        if not self._notify_schedule_running:
            return
        # 自动重新分析（后台模式不弹窗）
        if getattr(self, "_loaded_path", "") and not getattr(self, "_checking", False):
            self._run_analysis(show_dialog=False)
        msg = self._build_notify_message()
        if msg is not None:
            dingtalk_url = self._notify_dingtalk_var.get().strip()
            wechat_url = self._notify_wechat_var.get().strip()
            if dingtalk_url:
                threading.Thread(target=self._send_to_platform, args=("dingtalk", msg, False),
                                 daemon=True).start()
            if wechat_url:
                threading.Thread(target=self._send_to_platform, args=("wechat", msg, False),
                                 daemon=True).start()
        else:
            log_debug("[NOTIFY] 定时：无待提醒订单，跳过")
        interval_min = max(1, self._notify_interval_var.get())
        interval_ms = interval_min * 60 * 1000
        self._notify_schedule_id = self.after(interval_ms, self._schedule_tick)
