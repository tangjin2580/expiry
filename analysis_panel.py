# -*- coding: utf-8 -*-
"""
到期提醒工具 — 分析 & 树渲染 Mixin
"""

import threading
import traceback
import tkinter as tk
from tkinter import ttk, messagebox
from collections import defaultdict
from datetime import datetime

from config import C, FONT_FAMILY
from widgets import FlatButton
from utils import parse_date, check_expiry, _row_value, send_notify, log_error, log_trace, log_debug


class AnalysisPanelMixin:
    """到期分析、Treeview 渲染、失败查看。"""

    # -----------------------------------------------------------
    # 分析
    # -----------------------------------------------------------

    def _on_date_col_change(self, *_):
        if getattr(self, '_suppress_date_col_change', False):
            return
        self.hint_var.set(f"已切换：{self.date_col_cb.get()}")

    def _on_view_mode_change(self, *_):
        log_trace(f"[VIEW] 视图切换 → {self.view_mode_var.get()}")
        self._refresh_result_tree()

    def _do_check(self):
        log_debug("[ANALYSIS] _do_check 调用 (用户点击重新分析)")
        self._run_analysis(show_dialog=True)

    def _build_detail_rows(self, days_ahead, col_idx, pending_only):
        log_debug(f"[ANALYSIS] _build_detail_rows: days={days_ahead}, col_idx={col_idx}, pending_only={pending_only}, sheet_rows={len(self._sheet_rows)}")
        detail_rows = []
        skip = {}
        failed_rows = []
        expired_count = today_count = soon_count = 0
        ci_customer = self._col_map["customer"]
        ci_product = self._col_map["product"]
        ci_status = self._col_map["order_status"]
        ci_note = self._col_map["note"]
        ci_quantity = self._col_map.get("quantity")
        _today = datetime.today().date()  # 预计算，避免循环中重复获取
        for row_rec in self._sheet_rows:
            row = row_rec["values"]
            row_num = row_rec["excel_row"]
            order_status = str(_row_value(row, ci_status) or "").strip()
            if pending_only and order_status and order_status not in ("待发货",):
                continue
            raw_val = _row_value(row, col_idx)
            d, err = parse_date(raw_val)
            if d is None:
                skip[err] = skip.get(err, 0) + 1
                if err != "空值":
                    rec = {"row_num": row_num, "raw_value": str(raw_val) if raw_val is not None else "", "reason": err}
                    if err == "非日期":
                        rec["customer"] = str(_row_value(row, ci_customer) or "")
                        rec["product"] = str(_row_value(row, ci_product) or "")
                        rec["order_status"] = str(_row_value(row, ci_status) or "")
                    failed_rows.append(rec)
                continue
            status_text, diff = check_expiry(d, days_ahead, _today=_today)
            if diff < 0:
                tag = "expired"; expired_count += 1
            elif diff == 0:
                tag = "today"; today_count += 1
            elif diff <= 3:
                tag = "soon3"; soon_count += 1
            else:
                tag = "soon7"; soon_count += 1
            customer = str(_row_value(row, ci_customer) or "")
            product = str(_row_value(row, ci_product) or "")
            note = str(_row_value(row, ci_note) or "")
            quantity = str(_row_value(row, ci_quantity) or "") if ci_quantity is not None else ""
            date_str = d.strftime("%Y-%m-%d")
            values = (status_text, diff, date_str, customer, product, order_status, note)
            detail_rows.append({
                "row_num": row_num, "status_text": status_text, "diff": diff,
                "date": date_str, "customer": customer, "product": product,
                "quantity": quantity,
                "order_status": order_status, "note": note, "tag": tag, "values": values,
            })
        detail_rows.sort(key=lambda x: self._priority_key(x["diff"]))
        log_debug(f"[ANALYSIS] _build_detail_rows 结果: detail={len(detail_rows)}, expired={expired_count}, today={today_count}, soon={soon_count}, failed={len(failed_rows)}, skip={skip}")
        return detail_rows, skip, expired_count, today_count, soon_count, failed_rows

    def _run_analysis(self, show_dialog=True):
        log_trace(f"[ANALYSIS] _run_analysis show_dialog={show_dialog} loaded={bool(self._loaded_path)} checking={self._checking}")
        if self._loading:
            messagebox.showinfo("提示", "文件仍在加载，请稍候"); return
        if self._checking:
            messagebox.showinfo("提示", "正在分析中，请稍候"); return
        if not self._loaded_path:
            messagebox.showwarning("提示", "请先选择 Excel 文件"); return
        if not self.date_col_cb.get():
            messagebox.showwarning("提示", "请先选择日期列"); return
        # 清空搜索关键词
        if hasattr(self, "_search_var"):
            self._search_var.set("")
        idx = self.date_col_cb.current()
        if idx >= len(self._date_cols):
            messagebox.showwarning("提示", "日期列索引无效"); return
        days_ahead = max(1, self.days_var.get())
        col_idx = self._date_cols[idx]["index"]
        pending_only = self.pending_only.get()
        log_debug(f"[ANALYSIS] 参数: days={days_ahead}, col_idx={col_idx}, pending_only={pending_only}, date_col={self.date_col_cb.get()}")
        self._checking = True
        self._result_rows = []
        self._result_detail_rows = []
        self._failed_rows = []
        self._skip_info = {}
        self._cached_full_tree_data = None  # 清除树缓存，确保用新数据渲染
        self._sync_button_states()
        self.go_btn.config(text="分析中…")
        self.status_var.set("正在分析…")
        self.tv.delete(*self.tv.get_children())

        def worker():
            try:
                detail_rows, skip, expired_count, today_count, soon_count, failed_rows = \
                    self._build_detail_rows(days_ahead, col_idx, pending_only)

                def update():
                    self._result_detail_rows = detail_rows
                    self._failed_rows = failed_rows
                    self._skip_info = skip
                    self._result_rows = [row["values"] for row in detail_rows]

                    def finish():
                        log_debug("[ANALYSIS] finish() 开始")
                        self._checking = False
                        self.go_btn.config(text="▶  重新分析")
                        compare = None
                        if self._loaded_path:
                            previous = self._find_latest_snapshot(self._loaded_path)
                            snapshot = self._build_snapshot(days_ahead, detail_rows)
                            compare = self._compare_snapshot_rows(previous["rows"], snapshot["rows"]) if previous else None
                            self._history_entries.insert(0, snapshot)
                            self._current_snapshot_id = snapshot["id"]
                            self._save_history_entries()
                            self._refresh_history_list()
                        self.compare_var.set(
                            self._format_compare_summary(compare) if compare else "历史对比：首次生成记录")
                        self.status_var.set(
                            f"共 {len(detail_rows)} 条  ·  ❌已过期 {expired_count}  ·  🔴今天 {today_count}  ·  🟡即将到期 {soon_count}")
                        self._sync_button_states()
                        self._refresh_shipping_tab()
                        # ── 恢复待定的 Treeview 选中（由 _write_to_workbook 设置） ──
                        pending = getattr(self, "_pending_selection_restore", None)
                        log_debug(f"[ANALYSIS] finish() 检查 _pending_selection_restore: {pending}, tree_items={len(self._tree_item_map)}")
                        if pending is not None:
                            self._pending_selection_restore = None
                            iids_to_select = []
                            for iid, payload in self._tree_item_map.items():
                                if payload and payload.get("kind") == "detail":
                                    if payload["row"]["row_num"] in pending:
                                        iids_to_select.append(iid)
                            if iids_to_select:
                                self.tv.selection_set(iids_to_select)
                                self.tv.see(iids_to_select[0])
                                log_debug(f"[RESTORE] 已恢复 Treeview 选中: {len(iids_to_select)} 行")
                            else:
                                log_debug(f"[RESTORE] 未找到匹配的行 (pending={pending})")
                        log_debug("[ANALYSIS] finish() 完成")
                        if show_dialog:
                            cnt = expired_count + today_count + soon_count
                            if cnt:
                                parts = []
                                if expired_count: parts.append(f"已过期{expired_count}条")
                                if today_count: parts.append(f"今天{today_count}条")
                                if soon_count: parts.append(f"即将到期{soon_count}条")
                                send_notify("到期提醒", " | ".join(parts))
                                msg = f"共 {cnt} 条需要关注：" + " | ".join(parts)
                                if skip:
                                    msg += f"\n跳过：{', '.join(f'{k}×{v}' for k, v in skip.items())}"
                                messagebox.showinfo("到期提醒", msg)
                            else:
                                messagebox.showinfo("到期提醒", "✅ 所有订单均正常")
                    tree_rows = self._prepare_tree_rows(detail_rows)
                    self._render_tree_rows_in_batches(tree_rows, finish)
                self.after(0, update)
            except Exception as e:
                def show_error():
                    self._checking = False
                    self.go_btn.config(text="▶ 重新分析")
                    self.status_var.set("分析失败")
                    self._pending_selection_restore = None
                    self._sync_button_states()
                    self._show_analysis_failure(e)
                self.after(0, show_error)
        threading.Thread(target=worker, daemon=True).start()

    # -----------------------------------------------------------
    # Tree 渲染
    # -----------------------------------------------------------

    def _prepare_tree_rows(self, detail_rows):
        rows = []
        if self.view_mode_var.get() != "聚合":
            for item in detail_rows:
                rows.append({"key": f"detail:{item['row_num']}", "parent": "",
                              "text": f"第 {item['row_num']} 行", "values": item["values"],
                              "tag": item["tag"], "open": False, "payload": {"kind": "detail", "row": item}})
            return rows

        customer_map = defaultdict(lambda: defaultdict(list))
        for item in detail_rows:
            customer_map[item["customer"] or "未命名客户"][item["product"] or "未命名产品"].append(item)

        for customer, product_map in sorted(customer_map.items(),
            key=lambda p: self._priority_key(self._nearest_detail(
                [r for pr in p[1].values() for r in pr])["diff"])):
            customer_rows = [r for product_rows in product_map.values() for r in product_rows]
            nearest = self._nearest_detail(customer_rows)
            ck = f"customer:{customer}"
            rows.append({"key": ck, "parent": "", "text": customer,
                "values": (self._summarize_alert(customer_rows), nearest["diff"], nearest["date"],
                           customer, f"共 {len(customer_rows)} 条 / {len(product_map)} 种",
                           self._summarize_order_status(customer_rows), "客户汇总"),
                "tag": "group_customer", "open": True, "payload": {"kind": "customer", "rows": customer_rows}})
            for product, product_rows in sorted(product_map.items(),
                key=lambda item: self._priority_key(self._nearest_detail(item[1])["diff"])):
                nearest_p = self._nearest_detail(product_rows)
                pk = f"{ck}|product:{product}"
                rows.append({"key": pk, "parent": ck, "text": product,
                    "values": (self._summarize_alert(product_rows), nearest_p["diff"], nearest_p["date"],
                               customer, f"{product} × {len(product_rows)}",
                               self._summarize_order_status(product_rows), f"{len(product_rows)} 条明细"),
                    "tag": "group_product", "open": False, "payload": {"kind": "product", "rows": product_rows}})
                for detail in product_rows:
                    rows.append({"key": f"{pk}|detail:{detail['row_num']}", "parent": pk,
                        "text": f"第 {detail['row_num']} 行", "values": detail["values"],
                        "tag": detail["tag"], "open": False, "payload": {"kind": "detail", "row": detail}})
        return rows

    def _render_tree_rows_in_batches(self, rows, on_done, inserted=None, start=0, batch_size=200):
        if inserted is None:
            inserted = {}
            self._tree_item_map = {}
        end = min(start + batch_size, len(rows))
        for row in rows[start:end]:
            parent = inserted.get(row["parent"], "")
            iid = self.tv.insert(parent, "end", text=row["text"], values=row["values"],
                                 open=row["open"], tags=(row["tag"],))
            inserted[row["key"]] = iid
            self._tree_item_map[iid] = row["payload"]
        if end < len(rows):
            self.status_var.set(f"正在渲染结果… {end}/{len(rows)}")
            self.after(1, lambda: self._render_tree_rows_in_batches(rows, on_done, inserted, end, batch_size))
        else:
            on_done()

    def _filter_result_tree(self, keyword):
        log_debug(f"[FILTER] _filter_result_tree: keyword={keyword!r}, detail_rows={len(self._result_detail_rows)}")
        self.tv.delete(*self.tv.get_children())
        self._tree_item_map = {}
        if not self._result_detail_rows:
            self._sync_button_states()
            return
        rows = self._result_detail_rows
        if keyword:
            rows = [r for r in rows if
                    keyword in r.get("customer", "").lower() or
                    keyword in r.get("product", "").lower() or
                    keyword in r.get("order_status", "").lower() or
                    keyword in r.get("note", "").lower()]
        # 无关键词时复用缓存的全量树结构，避免重复构建分组
        if not keyword and hasattr(self, "_cached_full_tree_data") and self._cached_full_tree_data:
            data = self._cached_full_tree_data
        else:
            data = self._prepare_tree_rows(rows)
            if not keyword:
                self._cached_full_tree_data = data
        if keyword:
            self.status_var.set(f"筛选结果：{len(rows)} 条匹配「{keyword}」")
        self._render_tree_rows_in_batches(data, self._sync_button_states)

    def _refresh_result_tree(self):
        log_debug("[VIEW] _refresh_result_tree 调用")
        keyword = getattr(self, "_search_var", None)
        keyword = keyword.get().strip().lower() if keyword else ""
        self._filter_result_tree(keyword)

    def _expand_all_rows(self):
        log_debug("[VIEW] _expand_all_rows 调用")
        def _expand_recursive(item):
            self.tv.item(item, open=True)
            for child in self.tv.get_children(item):
                _expand_recursive(child)
        for item in self.tv.get_children():
            _expand_recursive(item)

    def _collapse_all_rows(self):
        log_debug("[VIEW] _collapse_all_rows 调用")
        def _collapse_recursive(item):
            self.tv.item(item, open=False)
            for child in self.tv.get_children(item):
                _collapse_recursive(child)
        for item in self.tv.get_children():
            _collapse_recursive(item)

    # -----------------------------------------------------------
    # 失败 & 错误弹窗
    # -----------------------------------------------------------

    def _show_failed_rows(self):
        failed = getattr(self, "_failed_rows", [])
        skip = getattr(self, "_skip_info", {})
        if not failed and not skip:
            messagebox.showinfo("查看失败", "本次分析没有解析失败或跳过的行"); return
        other_errors = [r for r in failed if r.get("reason") != "非日期"]
        nondate_rows = [r for r in failed if r.get("reason") == "非日期"]
        win = tk.Toplevel(self)
        win.title("解析失败与跳过记录"); win.geometry("820x560"); win["bg"] = C.bg
        hdr = tk.Frame(win, bg=C.surface); hdr.pack(fill="x", padx=12, pady=(12, 0))
        total_skip = sum(skip.values())
        tk.Label(hdr, text=f"共 {len(other_errors)+len(nondate_rows)+total_skip} 条未纳入（失败 {len(other_errors)} / 非日期 {len(nondate_rows)} / 跳过 {total_skip}）",
                 bg=C.surface, fg=C.text, font=(FONT_FAMILY, 11, "bold")).pack(side="left")
        tk.Frame(win, bg=C.border, height=1).pack(fill="x", padx=12, pady=(10, 0))
        nb = ttk.Notebook(win); nb.pack(fill="both", expand=True, padx=12, pady=12)

        def _make_tab(nb, title, cols, height=10):
            tab = tk.Frame(nb, bg=C.surface); nb.add(tab, text=title)
            tbl = tk.Frame(tab, bg=C.surface); tbl.pack(fill="both", expand=True)
            tv = ttk.Treeview(tbl, columns=cols, show="headings", height=height)
            vsb = ttk.Scrollbar(tbl, orient="vertical", command=tv.yview)
            tv.configure(yscrollcommand=vsb.set)
            tv.pack(side="left", fill="both", expand=True); vsb.pack(side="right", fill="y")
            return tv, tab

        tv1, tab1 = _make_tab(nb, f"解析失败（{len(other_errors)}）", ("行号", "原始值", "失败原因"))
        tv1.column("行号", width=80, anchor="center"); tv1.column("原始值", width=280, anchor="w"); tv1.column("失败原因", width=380, anchor="w")
        for r in other_errors:
            tv1.insert("", "end", values=(r["row_num"], r["raw_value"], r["reason"]))
        if not other_errors:
            tk.Label(tab1, text="无解析失败的行", bg=C.surface, fg=C.text2, font=(FONT_FAMILY, 11)).pack(expand=True)

        tv2, tab2 = _make_tab(nb, f"非日期数据（{len(nondate_rows)}）", ("行号", "日期列值", "客户", "产品", "订单状态"))
        tv2.column("行号", width=60, anchor="center"); tv2.column("日期列值", width=150, anchor="w"); tv2.column("客户", width=140, anchor="w"); tv2.column("产品", width=260, anchor="w"); tv2.column("订单状态", width=100, anchor="center")
        for r in nondate_rows:
            tv2.insert("", "end", values=(r["row_num"], r.get("raw_value", ""), r.get("customer", ""), r.get("product", ""), r.get("order_status", "")))
        if not nondate_rows:
            tk.Label(tab2, text="无非日期跳过记录", bg=C.surface, fg=C.text2, font=(FONT_FAMILY, 11)).pack(expand=True)

        tv3, tab3 = _make_tab(nb, f"跳过统计（{len(skip)} 类）", ("跳过原因", "数量"))
        tv3.column("跳过原因", width=560, anchor="w"); tv3.column("数量", width=180, anchor="center")
        for reason, count in sorted(skip.items(), key=lambda x: -x[1]):
            tv3.insert("", "end", values=(reason, count))
        if not skip:
            tk.Label(tab3, text="无跳过记录", bg=C.surface, fg=C.text2, font=(FONT_FAMILY, 11)).pack(expand=True)

        btn_frame = tk.Frame(win, bg=C.surface2, height=46)
        btn_frame.pack(fill="x", side="bottom"); btn_frame.pack_propagate(False)
        tk.Frame(btn_frame, bg=C.border, height=1).pack(side="top", fill="x")
        FlatButton(btn_frame, "关闭", command=win.destroy, bg=C.btn2, fg="white", height=30, width=80).pack(side="right", padx=12, pady=8)

    def _show_analysis_failure(self, error):
        err_msg = str(error)
        err_tb = traceback.format_exc()
        log_error(f"分析失败: {err_msg}\n{err_tb}")
        win = tk.Toplevel(self)
        win.title("分析失败"); win.geometry("820x600"); win["bg"] = C.bg
        win.transient(self); win.grab_set()
        hdr = tk.Frame(win, bg=C.danger_bg, height=64); hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text="❌  分析失败", bg=C.danger_bg, fg=C.danger,
                 font=(FONT_FAMILY, 16, "bold")).pack(side="left", padx=20, pady=14)
        info = tk.Frame(win, bg=C.surface); info.pack(fill="x", padx=16, pady=(16, 8))
        tk.Label(info, text="▌错误信息", bg=C.surface, fg=C.text, font=(FONT_FAMILY, 11, "bold"), anchor="w").pack(fill="x")
        err_box = tk.Frame(info, bg=C.danger_bg, highlightbackground=C.danger, highlightthickness=1)
        err_box.pack(fill="x", pady=(4, 0))
        err_text = tk.Text(err_box, height=4, font=("Consolas", 10), wrap="word", bg=C.danger_bg, fg=C.danger, relief="flat", bd=0, padx=10, pady=8)
        err_text.insert("1.0", err_msg or "(无错误信息)"); err_text.config(state="disabled"); err_text.pack(fill="x")
        sol = tk.Frame(win, bg=C.surface); sol.pack(fill="x", padx=16, pady=(0, 8))
        tk.Label(sol, text="▌💡 解决建议", bg=C.surface, fg=C.text, font=(FONT_FAMILY, 11, "bold"), anchor="w").pack(fill="x")
        tk.Label(sol, text="1. 检查 Excel 文件是否被其他程序打开\n2. 确认日期列是否正确\n3. 检查文件是否完整未损坏\n4. 如果是 xls，尝试另存为 xlsx\n5. 点下方「复制错误信息」发给开发者",
                 bg=C.surface, fg=C.text2, font=(FONT_FAMILY, 10), justify="left", anchor="w").pack(fill="x", pady=(4, 0))
        btn_frame = tk.Frame(win, bg=C.surface2, height=48)
        btn_frame.pack(fill="x", side="bottom"); btn_frame.pack_propagate(False)
        tk.Frame(btn_frame, bg=C.border, height=1).pack(side="top", fill="x")
        def copy_all():
            payload = f"分析失败\n文件：{self._loaded_path or '(未加载)'}\n错误：{err_msg}\n堆栈：\n{err_tb}"
            self._copy_to_clipboard(payload, "✅ 错误信息已复制")
        FlatButton(btn_frame, "复制错误信息", command=copy_all, bg="#0F766E", fg="white", height=30, width=120).pack(side="left", padx=12, pady=9)
        FlatButton(btn_frame, "关闭", command=win.destroy, bg=C.btn2, fg="white", height=30, width=80).pack(side="right", padx=12, pady=9)

    def _copy_to_clipboard(self, text, toast=None):
        try:
            self.clipboard_clear(); self.clipboard_append(text); self.update()
        except Exception:
            pass
        if toast:
            self.status_var.set(toast)
