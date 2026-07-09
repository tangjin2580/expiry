# -*- coding: utf-8 -*-
"""
到期提醒工具 — 机器人同步面板 Mixin（钉钉 / 企业微信 Webhook 定时推送）
"""

import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from modules.config import C, ROBOT_SYNC_CONFIG_FILE, FONT_FAMILY
from modules.utils import log_debug, log_trace
from modules.widgets import FlatButton
from modules.webhook_base import (
    do_webhook_request, build_webhook_payload,
    check_response_success, load_json_config,
    save_json_config, parse_mobiles,
)

_RS_DEFAULTS = {
    "dingtalk_url": "",
    "wechat_url": "",
    "interval_minutes": 30,
    "advance_days": 7,
    "auto_start": False,
    "at_mobiles": "",
    "at_all": False,
}


class RobotSyncMixin:
    """机器人同步面板：Webhook 配置 + 定时推送 + 消息预览。"""

    def _load_robot_sync_config(self):
        return load_json_config(ROBOT_SYNC_CONFIG_FILE, _RS_DEFAULTS)

    def _save_robot_sync_config(self):
        cfg = {
            "dingtalk_url": self._rs_dingtalk_var.get().strip(),
            "wechat_url": self._rs_wechat_var.get().strip(),
            "interval_minutes": self._rs_interval_var.get(),
            "advance_days": self._rs_days_var.get(),
            "auto_start": self._rs_auto_start_var.get(),
            "at_mobiles": self._rs_at_mobiles_var.get().strip(),
            "at_all": self._rs_at_all_var.get(),
        }
        save_json_config(ROBOT_SYNC_CONFIG_FILE, cfg)
        log_debug(f"[SYNC] 配置已保存: {ROBOT_SYNC_CONFIG_FILE}")

    def _build_robot_sync_tab(self):
        """构建机器人同步标签页。"""
        cfg = self._load_robot_sync_config()

        header = tk.Frame(self.robot_sync_tab, bg=C.bg)
        header.pack(fill="x", pady=(0, 10))
        tk.Label(header, text="🔗  机器人同步", bg=C.bg, fg=C.text,
                 font=(FONT_FAMILY, 14, "bold")).pack(side="left", padx=16, pady=8)
        tk.Label(header, text="配置 Webhook 地址，定时推送发货提醒", bg=C.bg, fg=C.text3,
                 font=(FONT_FAMILY, 10)).pack(side="left", padx=(0, 16))

        webhook_card = tk.Frame(self.robot_sync_tab, bg=C.surface,
                                highlightbackground=C.border, highlightthickness=1)
        webhook_card.pack(fill="x", padx=12, pady=(0, 10))
        self._treg(webhook_card, bg="surface")

        card_title = tk.Frame(webhook_card, bg=C.surface)
        card_title.pack(fill="x", padx=16, pady=(10, 4))
        tk.Label(card_title, text="📡  Webhook 地址配置", bg=C.surface, fg=C.text,
                 font=(FONT_FAMILY, 11, "bold")).pack(side="left")

        r1 = tk.Frame(webhook_card, bg=C.surface)
        r1.pack(fill="x", padx=16, pady=(4, 4))
        tk.Label(r1, text="📌  钉钉机器人", bg=C.surface, fg=C.text,
                 font=(FONT_FAMILY, 10, "bold"), width=16, anchor="w").pack(side="left")
        self._rs_dingtalk_var = tk.StringVar(value=cfg.get("dingtalk_url", ""))
        ttk.Entry(r1, textvariable=self._rs_dingtalk_var, style="Flat.TEntry",
                  font=(FONT_FAMILY, 10)).pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._rs_dingtalk_test_btn = FlatButton(
            r1, "🔔 测试", command=lambda: self._rs_test_send("dingtalk"),
            bg="#0EA5E9", fg="white", height=30, width=80, font=(FONT_FAMILY, 10, "bold"))
        self._rs_dingtalk_test_btn.pack(side="left")

        r2 = tk.Frame(webhook_card, bg=C.surface)
        r2.pack(fill="x", padx=16, pady=(4, 4))
        tk.Label(r2, text="💬  企业微信机器人", bg=C.surface, fg=C.text,
                 font=(FONT_FAMILY, 10, "bold"), width=16, anchor="w").pack(side="left")
        self._rs_wechat_var = tk.StringVar(value=cfg.get("wechat_url", ""))
        ttk.Entry(r2, textvariable=self._rs_wechat_var, style="Flat.TEntry",
                  font=(FONT_FAMILY, 10)).pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._rs_wechat_test_btn = FlatButton(
            r2, "🔔 测试", command=lambda: self._rs_test_send("wechat"),
            bg="#22C55E", fg="white", height=30, width=80, font=(FONT_FAMILY, 10, "bold"))
        self._rs_wechat_test_btn.pack(side="left")

        strategy_card = tk.Frame(self.robot_sync_tab, bg=C.surface,
                                 highlightbackground=C.border, highlightthickness=1)
        strategy_card.pack(fill="x", padx=12, pady=(0, 10))
        self._treg(strategy_card, bg="surface")

        strat_title = tk.Frame(strategy_card, bg=C.surface)
        strat_title.pack(fill="x", padx=16, pady=(10, 6))
        tk.Label(strat_title, text="⏰  提醒策略", bg=C.surface, fg=C.text,
                 font=(FONT_FAMILY, 11, "bold")).pack(side="left")

        sr1 = tk.Frame(strategy_card, bg=C.surface)
        sr1.pack(fill="x", padx=16, pady=(0, 4))

        tk.Label(sr1, text="⏱  推送间隔", bg=C.surface, fg=C.text2,
                 font=(FONT_FAMILY, 10)).pack(side="left", padx=(0, 4))
        self._rs_interval_var = tk.IntVar(value=cfg.get("interval_minutes", 30))
        ttk.Entry(sr1, textvariable=self._rs_interval_var, width=5, style="Flat.TEntry",
                  font=(FONT_FAMILY, 11)).pack(side="left", padx=(0, 4))
        tk.Label(sr1, text="分钟", bg=C.surface, fg=C.text2,
                 font=(FONT_FAMILY, 10)).pack(side="left", padx=(0, 20))

        tk.Label(sr1, text="🔔  提前天数", bg=C.surface, fg=C.text2,
                 font=(FONT_FAMILY, 10)).pack(side="left", padx=(0, 4))
        self._rs_days_var = tk.IntVar(value=cfg.get("advance_days", 7))
        ttk.Entry(sr1, textvariable=self._rs_days_var, width=5, style="Flat.TEntry",
                  font=(FONT_FAMILY, 11)).pack(side="left", padx=(0, 4))
        tk.Label(sr1, text="天", bg=C.surface, fg=C.text2,
                 font=(FONT_FAMILY, 10)).pack(side="left", padx=(0, 20))

        self._rs_auto_start_var = tk.BooleanVar(value=cfg.get("auto_start", False))
        ttk.Checkbutton(sr1, text="启动时自动开启", variable=self._rs_auto_start_var,
                        style="Flat.TCheckbutton").pack(side="left")

        sr_at = tk.Frame(strategy_card, bg=C.surface)
        sr_at.pack(fill="x", padx=16, pady=(0, 4))
        tk.Label(sr_at, text="📞  @成员手机号", bg=C.surface, fg=C.text2,
                 font=(FONT_FAMILY, 10)).pack(side="left", padx=(0, 4))
        self._rs_at_mobiles_var = tk.StringVar(value=cfg.get("at_mobiles", ""))
        ttk.Entry(sr_at, textvariable=self._rs_at_mobiles_var, style="Flat.TEntry",
                  font=(FONT_FAMILY, 10)).pack(side="left", fill="x", expand=True, padx=(0, 12))
        self._rs_at_all_var = tk.BooleanVar(value=cfg.get("at_all", False))
        ttk.Checkbutton(sr_at, text="@所有人", variable=self._rs_at_all_var,
                        style="Flat.TCheckbutton").pack(side="left")

        sr2 = tk.Frame(strategy_card, bg=C.surface)
        sr2.pack(fill="x", padx=16, pady=(4, 12))

        self._rs_save_btn = FlatButton(
            sr2, "💾  保存配置", command=self._rs_save_config,
            bg=C.accent, fg="white", height=32, width=110, font=(FONT_FAMILY, 10, "bold"))
        self._rs_save_btn.pack(side="left", padx=(0, 8))

        self._rs_preview_btn = FlatButton(
            sr2, "👁  预览消息", command=self._rs_preview_message,
            bg="#0F766E", fg="white", height=32, width=110, font=(FONT_FAMILY, 10, "bold"))
        self._rs_preview_btn.pack(side="left", padx=(0, 8))

        self._rs_send_now_btn = FlatButton(
            sr2, "📤  立即推送", command=self._rs_send_now,
            bg="#7C3AED", fg="white", height=32, width=110, font=(FONT_FAMILY, 10, "bold"))
        self._rs_send_now_btn.pack(side="left", padx=(0, 8))

        self._rs_toggle_btn = FlatButton(
            sr2, "▶  开启定时推送", command=self._rs_toggle_schedule,
            bg="#16A34A", fg="white", height=32, width=150, font=(FONT_FAMILY, 10, "bold"))
        self._rs_toggle_btn.pack(side="left", padx=(0, 8))

        self._rs_status_var = tk.StringVar(value="定时推送：未开启")
        tk.Label(sr2, textvariable=self._rs_status_var, bg=C.surface, fg=C.text2,
                 font=(FONT_FAMILY, 10)).pack(side="left", padx=(8, 0))

        preview_card = tk.Frame(self.robot_sync_tab, bg=C.surface,
                                highlightbackground=C.border, highlightthickness=1)
        preview_card.pack(fill="both", expand=True, padx=12, pady=(0, 6))
        self._treg(preview_card, bg="surface")

        preview_header = tk.Frame(preview_card, bg=C.surface)
        preview_header.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(preview_header, text="📋  推送内容预览 / 发送记录", bg=C.surface, fg=C.text,
                 font=(FONT_FAMILY, 11, "bold")).pack(side="left")
        self._rs_clear_log_btn = FlatButton(
            preview_header, "清空", command=self._rs_clear_log,
            bg=C.btn2, fg="white", height=26, width=60, font=(FONT_FAMILY, 9))
        self._rs_clear_log_btn.pack(side="right")

        log_cols = ("时间", "平台", "状态", "内容摘要")
        self._rs_log_tv = ttk.Treeview(
            preview_card, columns=log_cols, show="headings", height=12, selectmode="browse")
        for c, w, a in [("时间", 140, "center"), ("平台", 90, "center"),
                         ("状态", 70, "center"), ("内容摘要", 580, "w")]:
            self._rs_log_tv.heading(c, text=c)
            self._rs_log_tv.column(c, width=w, anchor=a)
        self._rs_log_tv.tag_configure("ok", background=C.ok_bg, foreground=C.ok)
        self._rs_log_tv.tag_configure("fail", background=C.danger_bg, foreground=C.danger)
        self._rs_log_tv.tag_configure("preview", background=C.info_bg, foreground=C.info)
        self._rs_log_tv.pack(fill="both", expand=True, padx=12, pady=(0, 12), side="left")
        self._rs_log_vsb = ttk.Scrollbar(
            preview_card, orient="vertical", command=self._rs_log_tv.yview)
        self._rs_log_vsb.pack(side="right", fill="y", pady=(0, 12))
        self._rs_log_tv.configure(yscrollcommand=self._rs_log_vsb.set)

        self._rs_schedule_id = None
        self._rs_schedule_running = False

        if cfg.get("auto_start", False):
            dingtalk_url = cfg.get("dingtalk_url", "").strip()
            wechat_url = cfg.get("wechat_url", "").strip()
            if dingtalk_url or wechat_url:
                self.after(2000, self._rs_auto_start)

    def _rs_build_message(self):
        """根据分析结果构建推送文本，越临近越靠前。"""
        rows = getattr(self, "_result_detail_rows", [])
        if not rows:
            return None
        days_limit = self._rs_days_var.get()
        filtered = [r for r in rows if r["diff"] <= days_limit]
        if not filtered:
            return None

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [f"📦 发货提醒 ({now_str})", f"共 {len(filtered)} 条待处理：", ""]

        for i, r in enumerate(filtered, 1):
            if r["diff"] < 0:
                urgency = "🔴已过期"
            elif r["diff"] == 0:
                urgency = "🟠今天"
            elif r["diff"] <= 1:
                urgency = "🟡明天"
            elif r["diff"] <= 3:
                urgency = f"🟡{r['diff']}天内"
            else:
                urgency = f"🔵{r['diff']}天内"

            customer = r.get("customer") or "未知客户"
            date_str = r.get("date") or "未知日期"
            product = r.get("product") or "未知产品"
            qty = r.get("quantity")
            qty_str = f" x{qty}" if qty else ""

            line = f"{i}. [{urgency}] {customer} | {date_str} | {product}{qty_str}"
            lines.append(line)

        return "\n".join(lines)

    def _rs_send_to_platform(self, platform, message, is_test=False):
        """发送到指定平台（在工作线程中）。"""
        at_mobiles = parse_mobiles(self._rs_at_mobiles_var.get().strip())
        at_all = self._rs_at_all_var.get()

        if platform == "dingtalk":
            url = self._rs_dingtalk_var.get().strip()
        elif platform == "wechat":
            url = self._rs_wechat_var.get().strip()
        else:
            return

        if not url:
            self.after(0, lambda: self._rs_log_result(platform, False, "未配置 Webhook 地址"))
            return

        payload = build_webhook_payload(platform, message, at_mobiles, at_all)
        ok, resp_body = do_webhook_request(url, payload)
        success = check_response_success(platform, ok, resp_body)

        label = "测试" if is_test else "推送"
        summary = f"[{label}] 发送成功" if success else f"[{label}] 失败: {resp_body[:100]}"
        self.after(0, lambda: self._rs_log_result(platform, success, summary))
        log_debug(f"[SYNC] {platform} {label}: ok={success}, resp={resp_body[:200]}")

    def _rs_log_result(self, platform, success, summary):
        """在记录 Treeview 中追加一条。"""
        now_str = datetime.now().strftime("%H:%M:%S")
        plat_name = "钉钉" if platform == "dingtalk" else "企业微信"
        tag = "ok" if success else "fail"
        status = "✅" if success else "❌"
        self._rs_log_tv.insert("", "end", values=(now_str, plat_name, status, summary), tags=(tag,))
        children = self._rs_log_tv.get_children()
        if children:
            self._rs_log_tv.see(children[-1])
        self.status_var.set(summary)

    def _rs_clear_log(self):
        for item in self._rs_log_tv.get_children():
            self._rs_log_tv.delete(item)

    def _rs_save_config(self):
        """保存配置并提示。"""
        self._save_robot_sync_config()
        self.status_var.set("已保存")
        messagebox.showinfo("保存成功", "机器人同步配置已保存", parent=self)

    def _rs_test_send(self, platform):
        """测试发送。"""
        test_msg = ("🤖 到期提醒工具 — 机器人同步测试\n\n"
                    "如果你收到这条消息，说明 Webhook 配置正确！\n"
                    f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log_debug(f"[SYNC] 测试发送: {platform}")
        threading.Thread(target=self._rs_send_to_platform, args=(platform, test_msg, True),
                         daemon=True).start()

    def _rs_preview_message(self):
        """预览即将推送的消息内容。"""
        msg = self._rs_build_message()
        if msg is None:
            self._rs_log_tv.insert("", "end",
                values=(datetime.now().strftime("%H:%M:%S"), "预览", "\u26a0\ufe0f",
                        "没有需要提醒的待发货订单（请先加载 Excel 并执行分析）"),
                tags=("preview",))
            self.status_var.set("预览：无待提醒订单")
            return
        preview = msg[:500] + ("..." if len(msg) > 500 else "")
        line_count = msg.count("\n") + 1
        self._rs_log_tv.insert("", "end",
            values=(datetime.now().strftime("%H:%M:%S"), "预览", "\U0001f441",
                    f"共{line_count}行 | {preview}"),
            tags=("preview",))
        self._rs_show_preview_dialog(msg)

    def _rs_show_preview_dialog(self, msg):
        """弹窗显示完整预览消息。"""
        dlg = tk.Toplevel(self)
        dlg.title("推送内容预览")
        dlg.geometry("600x480")
        dlg.transient(self)
        dlg["bg"] = C.surface
        tk.Label(dlg, text="📋  以下是即将推送的消息内容", bg=C.surface, fg=C.text,
                 font=(FONT_FAMILY, 11, "bold")).pack(anchor="w", padx=16, pady=(12, 6))
        text_widget = tk.Text(dlg, wrap="word", bg=C.surface2, fg=C.text,
                              font=(FONT_FAMILY, 10), relief="flat", padx=12, pady=8)
        text_widget.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        text_widget.insert("1.0", msg)
        text_widget.config(state="disabled")
        btn_frame = tk.Frame(dlg, bg=C.surface)
        btn_frame.pack(fill="x", padx=16, pady=(0, 12))
        tk.Button(btn_frame, text="复制内容", command=lambda: (
            self.clipboard_clear(), self.clipboard_append(msg),
            self.status_var.set("已复制到剪贴板")),
                  bg=C.accent, fg="white", relief="flat", padx=16, pady=4,
                  font=(FONT_FAMILY, 10, "bold")).pack(side="left")
        tk.Button(btn_frame, text="关闭", command=dlg.destroy,
                  bg=C.btn2, fg="white", relief="flat", padx=16, pady=4,
                  font=(FONT_FAMILY, 10)).pack(side="right")

    def _rs_send_now(self):
        """立即推送一次到所有已配置平台。"""
        msg = self._rs_build_message()
        if msg is None:
            self.status_var.set("没有需要提醒的待发货订单")
            messagebox.showinfo("推送", "没有需要提醒的待发货订单\n请先加载 Excel 并执行分析", parent=self)
            return
        dingtalk_url = self._rs_dingtalk_var.get().strip()
        wechat_url = self._rs_wechat_var.get().strip()
        sent = False
        if dingtalk_url:
            threading.Thread(target=self._rs_send_to_platform, args=("dingtalk", msg, False),
                             daemon=True).start()
            sent = True
        if wechat_url:
            threading.Thread(target=self._rs_send_to_platform, args=("wechat", msg, False),
                             daemon=True).start()
            sent = True
        if not sent:
            self.status_var.set("请先配置 Webhook 地址")
            messagebox.showwarning("提示", "请先配置钉钉或企业微信的 Webhook 地址", parent=self)

    def _rs_toggle_schedule(self):
        if self._rs_schedule_running:
            self._rs_stop_schedule()
        else:
            self._rs_start_schedule()

    def _rs_start_schedule(self):
        dingtalk_url = self._rs_dingtalk_var.get().strip()
        wechat_url = self._rs_wechat_var.get().strip()
        if not dingtalk_url and not wechat_url:
            messagebox.showwarning("提示", "请先配置至少一个 Webhook 地址", parent=self)
            return
        self._save_robot_sync_config()
        self._rs_schedule_running = True
        self._rs_toggle_btn.config(text="⏹  停止定时推送", bg="#DC2626")
        interval = self._rs_interval_var.get()
        self._rs_status_var.set(f"定时推送：运行中（每 {interval} 分钟）")
        self._rs_schedule_tick()
        log_debug(f"[SYNC] 定时推送已开启, 间隔={interval}分钟")

    def _rs_stop_schedule(self):
        self._rs_schedule_running = False
        if self._rs_schedule_id is not None:
            self.after_cancel(self._rs_schedule_id)
            self._rs_schedule_id = None
        self._rs_toggle_btn.config(text="▶  开启定时推送", bg="#16A34A")
        self._rs_status_var.set("定时推送：已停止")
        log_debug("[SYNC] 定时推送已停止")

    def _rs_schedule_tick(self):
        """定时回调：发送通知 → 调度下一次。"""
        if not self._rs_schedule_running:
            return
        # 自动重新分析（后台模式不弹窗）
        if getattr(self, "_loaded_path", "") and not getattr(self, "_checking", False):
            self._run_analysis(show_dialog=False)
        msg = self._rs_build_message()
        if msg is not None:
            dingtalk_url = self._rs_dingtalk_var.get().strip()
            wechat_url = self._rs_wechat_var.get().strip()
            if dingtalk_url:
                threading.Thread(target=self._rs_send_to_platform, args=("dingtalk", msg, False),
                                 daemon=True).start()
            if wechat_url:
                threading.Thread(target=self._rs_send_to_platform, args=("wechat", msg, False),
                                 daemon=True).start()
        else:
            log_debug("[SYNC] 定时：无待提醒订单，跳过")
        interval_min = max(1, self._rs_interval_var.get())
        interval_ms = interval_min * 60 * 1000
        self._rs_schedule_id = self.after(interval_ms, self._rs_schedule_tick)

    def _rs_auto_start(self):
        """启动时自动开启定时推送。"""
        if not self._rs_schedule_running:
            dingtalk_url = self._rs_dingtalk_var.get().strip()
            wechat_url = self._rs_wechat_var.get().strip()
            if dingtalk_url or wechat_url:
                self._rs_start_schedule()
                log_debug("[SYNC] 自动启动定时推送")
