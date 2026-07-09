# -*- coding: utf-8 -*-
"""
到期提醒工具 — 公共 Webhook 工具函数（notify_panel / robot_sync 共享）
"""

import json
import urllib.request
import urllib.error


def do_webhook_request(url, payload):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status == 200, body
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return False, str(e)


def build_webhook_payload(platform, message, at_mobiles, at_all):
    payload = {}
    if platform == "dingtalk":
        payload = {"msgtype": "text", "text": {"content": message}}
        if at_all:
            payload["at"] = {"atMobiles": at_mobiles, "isAtAll": True}
        elif at_mobiles:
            payload["at"] = {"atMobiles": at_mobiles, "isAtAll": False}
    elif platform == "wechat":
        payload = {"msgtype": "text", "text": {"content": message}}
        if at_all:
            payload["text"]["mentioned_list"] = ["all"]
            if at_mobiles:
                payload["text"]["mentioned_mobile_list"] = at_mobiles
        elif at_mobiles:
            payload["text"]["mentioned_mobile_list"] = at_mobiles
    return payload


def check_response_success(platform, ok, resp_body):
    try:
        resp_json = json.loads(resp_body)
        return ok and resp_json.get("errcode", -1) == 0
    except Exception:
        return ok


def load_json_config(filepath, default):
    import os
    if not os.path.exists(filepath):
        return dict(default)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return dict(default)
    if isinstance(data, dict):
        merged = dict(default)
        merged.update(data)
        return merged
    return dict(default)


def save_json_config(filepath, config_dict):
    import os
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(config_dict, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def parse_mobiles(raw_text):
    if not raw_text:
        return []
    return [p.strip() for p in raw_text.replace("，", ",").split(",") if p.strip()]
