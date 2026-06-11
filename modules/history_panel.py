# -*- coding: utf-8 -*-
"""
到期提醒工具 — 历史记录 Mixin
"""

import os
import json
import uuid
import tkinter as tk
from tkinter import ttk, messagebox
from collections import Counter
from datetime import datetime, timedelta

from modules.config import C, HISTORY_FILE, FONT_FAMILY
from modules.utils import log_trace, log_debug


class HistoryPanelMixin:
    """历史快照管理：存储、列表、对比、恢复、清空。"""

    # -----------------------------------------------------------
    # IO
    # -----------------------------------------------------------

    def _load_history_entries(self):
        log_debug(f"[HIST] _load_history_entries: file_exists={os.path.exists(HISTORY_FILE)}")
        if not os.path.exists(HISTORY_FILE):
            return []
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save_history_entries(self):
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self._history_entries[:80], f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.status_var.set(f"历史记录保存失败：{e}")

    # -----------------------------------------------------------
    # 快照
    # -----------------------------------------------------------

    def _build_snapshot(self, days_ahead, detail_rows):
        counter = Counter()
        rows = []
        for r in detail_rows:
            tag = r["tag"]
            counter[tag] += 1
            rows.append({
                "row_num": r["row_num"],
                "customer": r["customer"],
                "product": r["product"],
                "order_status": r["order_status"],
                "note": r["note"],
                "date": r["date"],
                "diff": r["diff"],
                "status_text": r["status_text"],
                "tag": tag,
            })
        return {
            "id": str(uuid.uuid4()),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source_path": self._loaded_path,
            "source_name": os.path.basename(self._loaded_path),
            "days_ahead": days_ahead,
            "summary": {
                "total": len(rows),
                "expired": counter["expired"],
                "today": counter["today"],
                "soon": counter["soon3"] + counter["soon7"],
                "normal": counter["normal"],
            },
            "rows": rows,
        }

    def _find_latest_snapshot(self, source_path, exclude_id=None):
        for item in self._history_entries:
            if item.get("source_path") == source_path and item.get("id") != exclude_id:
                return item
        return None

    def _compare_snapshot_rows(self, old_rows, new_rows):
        old_map = {int(r["row_num"]): r for r in (old_rows or [])}
        new_map = {int(r["row_num"]): r for r in (new_rows or [])}
        diff_rows = []
        counts = Counter()
        all_keys = sorted(old_map.keys() | new_map.keys())
        for row_num in all_keys:
            old = old_map.get(row_num)
            new = new_map.get(row_num)
            if old is None:
                counts["新增"] += 1
                diff_rows.append({"type": "新增", "customer": new.get("customer", ""),
                                   "product": new.get("product", ""), "old_status": "",
                                   "new_status": new.get("order_status", ""), "date": new.get("date", "")})
            elif new is None:
                counts["移除"] += 1
                diff_rows.append({"type": "移除", "customer": old.get("customer", ""),
                                   "product": old.get("product", ""), "old_status": old.get("order_status", ""),
                                   "new_status": "", "date": old.get("date", "")})
            elif old.get("order_status") != new.get("order_status"):
                counts["订单状态变更"] += 1
                diff_rows.append({"type": "订单状态变更",
                                   "customer": new.get("customer", old.get("customer", "")),
                                   "product": new.get("product", old.get("product", "")),
                                   "old_status": old.get("order_status", ""),
                                   "new_status": new.get("order_status", ""),
                                   "date": new.get("date", old.get("date", ""))})
            elif old.get("status_text") != new.get("status_text") or old.get("diff") != new.get("diff"):
                counts["提醒变化"] += 1
                diff_rows.append({"type": "提醒变化",
                                   "customer": new.get("customer", old.get("customer", "")),
                                   "product": new.get("product", old.get("product", "")),
                                   "old_status": old.get("status_text", ""),
                                   "new_status": new.get("status_text", ""),
                                   "date": new.get("date", old.get("date", ""))})
        return {"counts": counts, "rows": diff_rows}

    def _format_compare_summary(self, compare):
        if not compare or not compare["rows"]:
            return "历史对比：与上次记录一致"
        c = compare["counts"]
        parts = []
        for label in ("新增", "移除", "订单状态变更", "提醒变化"):
            if c[label]:
                parts.append(f"{'状态变更' if label == '订单状态变更' else label} {c[label]}")
        return "历史对比：" + "，".join(parts)

    # -----------------------------------------------------------
    # 列表
    # -----------------------------------------------------------

    def _refresh_history_list(self):
        if not hasattr(self, "history_tv"):
            return
        for item in self.history_tv.get_children():
            self.history_tv.delete(item)
        self._history_item_map = {}
        keyword = ""
        if hasattr(self, "history_search_var"):
            keyword = self.history_search_var.get().strip().lower()
        filtered = []
        for entry in self._history_entries:
            if keyword:
                blob = " ".join([entry.get("source_name", ""), entry.get("created_at", ""),
                                 entry.get("source_path", "")]).lower()
                if keyword not in blob:
                    continue
            filtered.append(entry)
        for entry in filtered:
            s = entry.get("summary", {})
            overview = f"共{s.get('total', 0)}条 / 过期{s.get('expired', 0)} / 今天{s.get('today', 0)} / 即将{s.get('soon', 0)}"
            iid = self.history_tv.insert("", "end", values=(entry.get("created_at", ""),
                                           entry.get("source_name", ""), overview))
            self._history_item_map[iid] = entry
        self.history_info_var.set(
            f"历史记录：筛选 '{keyword}' 后 {len(filtered)} 条 / 共 {len(self._history_entries)} 条"
            if keyword else f"历史记录：共 {len(self._history_entries)} 条")
        self._sync_button_states()

    def _get_selected_snapshot(self):
        if not hasattr(self, "history_tv"):
            return None
        sel = self.history_tv.selection()
        return self._history_item_map.get(sel[0]) if sel else None

    def _fill_history_details(self, rows, summary_text):
        self.history_detail_var.set(summary_text)
        for item in self.history_detail_tv.get_children():
            self.history_detail_tv.delete(item)
        for row in rows:
            tag = row.get("type", "")
            self.history_detail_tv.insert("", "end", values=(row.get("type", ""), row.get("customer", ""),
                                          row.get("product", ""), row.get("old_status", ""),
                                          row.get("new_status", ""), row.get("date", "")),
                                          tags=(tag,) if tag else ())

    # -----------------------------------------------------------
    # 操作
    # -----------------------------------------------------------

    def _show_selected_history_snapshot(self):
        snapshot = self._get_selected_snapshot()
        if snapshot is None:
            self.history_detail_var.set("请选择左侧历史记录")
            self._sync_button_states()
            return
        rows = [{"type": "快照", "customer": r.get("customer", ""), "product": r.get("product", ""),
                 "old_status": r.get("order_status", ""), "new_status": r.get("status_text", ""),
                 "date": r.get("date", "")} for r in snapshot.get("rows", [])]
        s = snapshot.get("summary", {})
        self._fill_history_details(rows,
            f"时间：{snapshot.get('created_at', '')}    文件：{snapshot.get('source_name', '')}，"
            f"共 {s.get('total', 0)} 条，已过期 {s.get('expired', 0)}，今天到期 {s.get('today', 0)}，即将到期 {s.get('soon', 0)}")
        self._sync_button_states()

    def _compare_selected_history_with_current(self):
        log_trace("[HIST] 对比选中快照与当前数据")
        snapshot = self._get_selected_snapshot()
        if snapshot is None:
            messagebox.showwarning("提示", "请先选择一条历史记录"); return
        if not self._result_detail_rows:
            messagebox.showwarning("提示", "请先在分析页生成当前结果"); return
        if snapshot.get("source_path") != self._loaded_path:
            messagebox.showwarning("提示", "选中的历史记录与当前加载的文件不是同一个原始文件"); return
        current_rows = [{"row_num": r["row_num"], "customer": r["customer"], "product": r["product"],
                         "order_status": r["order_status"], "date": r["date"],
                         "diff": r["diff"], "status_text": r["status_text"]} for r in self._result_detail_rows]
        compare = self._compare_snapshot_rows(snapshot.get("rows", []), current_rows)
        self._fill_history_details(compare["rows"],
            f"快照：{snapshot.get('created_at', '')} / {snapshot.get('source_name', '')}，{self._format_compare_summary(compare)}")

    def _restore_selected_history(self):
        log_trace("[HIST] _restore_selected_history 调用")
        snapshot = self._get_selected_snapshot()
        if snapshot is None:
            messagebox.showwarning("提示", "请先选择一条历史记录"); return
        path = snapshot.get("source_path", "")
        if not path or not os.path.exists(path):
            messagebox.showerror("恢复失败", "原始文件不存在，无法恢复"); return
        if not messagebox.askyesno("确认恢复", f"将把快照中的订单状态恢复到原始文件：{os.path.basename(path)}，是否继续？"):
            return
        updates = {int(r["row_num"]): r.get("order_status", "")
                   for r in snapshot.get("rows", [])
                   if r.get("order_status")}
        log_debug(f"[HIST] 恢复快照: {len(updates)} 条状态更新, path={path}")
        self._write_status_updates(path, updates, "历史快照已恢复到原始文件", reload_if_current=True)

    def _delete_selected_history(self):
        log_trace("[HIST] _delete_selected_history 调用")
        sel = self.history_tv.selection() if hasattr(self, "history_tv") else ()
        if not sel:
            messagebox.showwarning("提示", "请先选择要删除的历史记录（可按住 Ctrl 多选）"); return
        target_ids = {self._history_item_map[iid].get("id") for iid in sel}
        target_ids.discard(None)
        if not target_ids:
            messagebox.showwarning("提示", "选中的记录无效"); return
        if not messagebox.askyesno("确认删除", f"将删除选中的 {len(target_ids)} 条历史快照，是否继续？\n（此操作不可恢复）"):
            return
        self._history_entries = [e for e in self._history_entries if e.get("id") not in target_ids]
        self._save_history_entries()
        self._refresh_history_list()
        self.history_info_var.set(f"历史记录：已删除 {len(target_ids)} 条，剩余 {len(self._history_entries)} 条")
        self.status_var.set(f"已删除 {len(target_ids)} 条历史快照")
        self._sync_button_states()

    def _clear_old_history(self, days=30):
        if not self._history_entries:
            messagebox.showinfo("提示", "当前没有历史记录"); return
        threshold = datetime.now() - timedelta(days=days)
        old, keep = [], []
        for e in self._history_entries:
            try:
                dt = datetime.strptime(e.get("created_at", ""), "%Y-%m-%d %H:%M:%S")
            except Exception:
                dt = None
            (old if dt and dt < threshold else keep).append(e)
        if not old:
            messagebox.showinfo("提示", f"没有 {days} 天前的快照可清理"); return
        if not messagebox.askyesno("确认清旧", f"将删除 {len(old)} 条 {days} 天前的快照，保留 {len(keep)} 条，是否继续？"):
            return
        self._history_entries = keep
        self._save_history_entries()
        self._refresh_history_list()
        self.status_var.set(f"已清理 {len(old)} 条 {days} 天前的快照")
        self._sync_button_states()

    def _clear_all_history(self):
        if not self._history_entries:
            messagebox.showinfo("提示", "当前没有历史记录"); return
        n = len(self._history_entries)
        if not messagebox.askyesno("⚠ 危险操作", f"将删除全部 {n} 条历史快照，是否继续？\n（此操作不可恢复）"):
            return
        confirm_win = tk.Toplevel(self)
        confirm_win.title("二次确认")
        confirm_win.geometry("420x180"); confirm_win["bg"] = C.bg
        confirm_win.transient(self); confirm_win.grab_set()
        tk.Label(confirm_win, text=f"将删除全部 {n} 条历史快照", bg=C.bg, fg=C.danger,
                 font=(FONT_FAMILY, 12, "bold")).pack(pady=(20, 6))
        tk.Label(confirm_win, text='请输入大写 "CLEAR" 以确认:', bg=C.bg, fg=C.text,
                 font=(FONT_FAMILY, 10)).pack()
        entry_var = tk.StringVar()
        ent = ttk.Entry(confirm_win, textvariable=entry_var, width=20, font=(FONT_FAMILY, 12), justify="center")
        ent.pack(pady=8); ent.focus_set()

        def do_confirm():
            if entry_var.get().strip() != "CLEAR":
                messagebox.showerror("错误", "输入不正确,操作已取消", parent=confirm_win); return
            self._history_entries = []
            self._save_history_entries()
            self._refresh_history_list()
            self.history_info_var.set("历史记录：已清空")
            self.status_var.set(f"已清空 {n} 条历史快照")
            self._sync_button_states()
            confirm_win.destroy()
        ent.bind("<Return>", lambda _: do_confirm())
        ent.bind("<Escape>", lambda _: confirm_win.destroy())
        FlatButton(confirm_win, "确认清空", command=do_confirm, bg=C.danger, fg="white",
                   height=30, width=100, font=(FONT_FAMILY, 11, "bold")).pack(side="left", padx=(60, 6), pady=8)
        FlatButton(confirm_win, "取消", command=confirm_win.destroy, bg=C.btn2, fg="white",
                   height=30, width=80).pack(side="left", pady=8)
        confirm_win.bind("<Return>", lambda _: do_confirm())
