import asyncio
import json
import threading
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from config import BOT_TOKEN, OWNER_USERNAME, OWNER_ID
from emojis import BUTTON_CUSTOM_EMOJIS, _btn_icon_id, _clean_btn_text

_BTN_STYLES = ["primary", "success", "danger"]
_style_idx = 0
_style_lock = threading.Lock()


def _next_style() -> str:
    global _style_idx
    with _style_lock:
        s = _BTN_STYLES[_style_idx % len(_BTN_STYLES)]
        _style_idx += 1
        return s


def _color_kb(rows: list) -> dict:
    colored = []
    for row in rows:
        colored_row = []
        for btn in row:
            b = dict(btn)
            cb = b.get("callback_data", "")
            has_copy = "copy_text" in b
            has_url = "url" in b
            if ((cb and cb != "noop") or has_copy or has_url) and "style" not in b:
                b["style"] = _next_style()
            if cb == "noop" and has_copy:
                b.pop("callback_data", None)
            raw_text = b.get("text", "")
            if "icon_custom_emoji_id" not in b:
                icon_id = _btn_icon_id(raw_text)
                if icon_id:
                    b["icon_custom_emoji_id"] = icon_id
            b["text"] = _clean_btn_text(raw_text)
            colored_row.append(b)
        colored.append(colored_row)
    return {"inline_keyboard": colored}


def _strip_styles(markup: dict) -> dict:
    import copy
    m = copy.deepcopy(markup)
    for row in m.get("inline_keyboard", []):
        for btn in row:
            btn.pop("style", None)
    return m


def _strip_icons(markup: dict) -> dict:
    import copy
    m = copy.deepcopy(markup)
    for row in m.get("inline_keyboard", []):
        for btn in row:
            btn.pop("icon_custom_emoji_id", None)
    return m


_http_session = requests.Session()
_http_session.verify = False
_http_adapter = requests.adapters.HTTPAdapter(
    pool_connections=8, pool_maxsize=32, max_retries=1
)
_http_session.mount("https://", _http_adapter)
_http_session.mount("http://", _http_adapter)


import time as _rl_time
import threading as _rl_thread

# ══════════════════════════════════════════════════════════════════════════════
#  Rate limiter — max 25 req/sec to Telegram (safe under 30 limit)
# ══════════════════════════════════════════════════════════════════════════════
_rl_lock = _rl_thread.Lock()
_rl_tokens = [25]
_rl_last = [_rl_time.time()]

def _rate_limit():
    """Token bucket — 25 req/sec."""
    with _rl_lock:
        now = _rl_time.time()
        elapsed = now - _rl_last[0]
        _rl_tokens[0] = min(25, _rl_tokens[0] + elapsed * 25)
        _rl_last[0] = now
        if _rl_tokens[0] < 1:
            sleep_for = (1 - _rl_tokens[0]) / 25
            _rl_time.sleep(sleep_for)
            _rl_tokens[0] = 0
        else:
            _rl_tokens[0] -= 1


def _raw_post(url, payload):
    _rate_limit()
    p = dict(payload)
    if "reply_markup" in p and isinstance(p["reply_markup"], dict):
        p["reply_markup"] = json.dumps(p["reply_markup"], ensure_ascii=False)
    for _attempt in range(3):
        try:
            r = _http_session.post(url, json=p, timeout=10)
            resp = r.json()
            # ═══ Handle 429 rate limit ═══
            if not resp.get("ok") and resp.get("error_code") == 429:
                wait = resp.get("parameters", {}).get("retry_after", 3)
                print(f"[TG-429] retry_after={wait}s — waiting...")
                _rl_time.sleep(wait + 1)
                continue
            return resp
        except Exception as e:
            print(f"[TG-POST-ERR] {e}")
            _rl_time.sleep(0.5)
    return {"ok": False}


async def raw_send(chat_id, text, kb_rows, parse_mode="HTML", reply_to=None):
    kb = _color_kb(kb_rows)
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id, "text": text,
        "parse_mode": parse_mode, "reply_markup": kb,
        "disable_web_page_preview": True,
    }
    if reply_to:
        payload["reply_to_message_id"] = reply_to
    resp = await asyncio.to_thread(_raw_post, url, payload)
    if resp.get("ok"):
        return resp["result"]["message_id"]
    payload["reply_markup"] = _strip_icons(kb)
    resp = await asyncio.to_thread(_raw_post, url, payload)
    if resp.get("ok"):
        return resp["result"]["message_id"]
    payload["reply_markup"] = _strip_styles(_strip_icons(kb))
    resp = await asyncio.to_thread(_raw_post, url, payload)
    if resp.get("ok"):
        return resp["result"]["message_id"]
    return None


async def raw_edit(chat_id, message_id, text, kb_rows, parse_mode="HTML"):
    kb = _color_kb(kb_rows)
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    payload = {
        "chat_id": chat_id, "message_id": message_id,
        "text": text, "parse_mode": parse_mode, "reply_markup": kb,
        "disable_web_page_preview": True,
    }
    resp = await asyncio.to_thread(_raw_post, url, payload)
    if resp.get("ok"):
        return resp
    payload["reply_markup"] = _strip_icons(kb)
    resp = await asyncio.to_thread(_raw_post, url, payload)
    if resp.get("ok"):
        return resp
    payload["reply_markup"] = _strip_styles(_strip_icons(kb))
    resp = await asyncio.to_thread(_raw_post, url, payload)
    return resp


async def nav_edit(chat_id, message_id, text, kb_rows, parse_mode="HTML"):
    kb = _color_kb(kb_rows)
    cap_payload = {
        "chat_id": chat_id, "message_id": message_id,
        "caption": text, "parse_mode": parse_mode, "reply_markup": kb,
    }
    resp = await asyncio.to_thread(
        _raw_post,
        f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageCaption",
        cap_payload,
    )
    if resp.get("ok"):
        return resp
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    txt_payload = {
        "chat_id": chat_id, "message_id": message_id,
        "text": text, "parse_mode": parse_mode, "reply_markup": kb,
        "disable_web_page_preview": True,
    }
    resp = await asyncio.to_thread(_raw_post, url, txt_payload)
    if resp.get("ok"):
        return resp
    txt_payload["reply_markup"] = _strip_icons(kb)
    resp = await asyncio.to_thread(_raw_post, url, txt_payload)
    if resp.get("ok"):
        return resp
    txt_payload["reply_markup"] = _strip_styles(_strip_icons(kb))
    resp = await asyncio.to_thread(_raw_post, url, txt_payload)
    return resp


# ══════════════════════════════════════════════════════════════════════════════
#  ▸ MAIN MENU
# ══════════════════════════════════════════════════════════════════════════════

def rows_main():
    return [
        [
            {"text": "💳  Checker",      "callback_data": "gates"},
            {"text": "Jio Hitter",       "callback_data": "jio_info", "icon_custom_emoji_id": "5445350406215465190"},
        ],
        [
            {"text": "⭐  Plans",         "callback_data": "plans"},
            {"text": "👑  Profile",       "callback_data": "profile"},
        ],
        [
            {"text": "⚙️  Commands",      "callback_data": "commands"},
            {"text": "💻  Contact",       "url": f"https://t.me/{OWNER_USERNAME}"},
        ],
        [
            {"text": "❌  Close",         "callback_data": "close"},
        ],
    ]


def rows_gates():
    return [
        [{"text": "🔑  Manage Proxy",  "callback_data": "manage_proxy"}],
        [{"text": "↪️  Back",          "callback_data": "back_start"}],
    ]


def rows_checker():
    return rows_gates()


# ══════════════════════════════════════════════════════════════════════════════
#  ▸ PLANS
# ══════════════════════════════════════════════════════════════════════════════

def rows_plans():
    return [
        [{"text": "🔑  Redeem Key",  "callback_data": "redeem_info"}],
        [{"text": "💻  Contact",     "url": f"https://t.me/{OWNER_USERNAME}"}],
        [{"text": "↪️  Back",        "callback_data": "back_start"}],
    ]


# ══════════════════════════════════════════════════════════════════════════════
#  ▸ PROFILE
# ══════════════════════════════════════════════════════════════════════════════

def rows_profile():
    return [
        [
            {"text": "⭐  Plans",   "callback_data": "plans"},
            {"text": "🔑  Redeem",  "callback_data": "redeem_info"},
        ],
        [{"text": "↪️  Back",       "callback_data": "back_start"}],
    ]


# ══════════════════════════════════════════════════════════════════════════════
#  ▸ COMMANDS
# ══════════════════════════════════════════════════════════════════════════════

def rows_commands():
    return [
        [{"text": "⚡  CC Commands",     "callback_data": "gates"}],
        [{"text": "🔑  Proxy Commands",  "callback_data": "manage_proxy"}],
        [{"text": "↪️  Back",            "callback_data": "back_start"}],
    ]


# ══════════════════════════════════════════════════════════════════════════════
#  ▸ PROXY MANAGER
# ══════════════════════════════════════════════════════════════════════════════

def rows_proxy(uid: int):
    from storage import user_pool_enabled
    pool_on = user_pool_enabled.get(uid, True) if uid else True
    pool_label = "🌟  Pool: ON" if pool_on else "🟣  Pool: OFF"

    return [
        [{"text": pool_label,           "callback_data": "toggle_pool"}],
        [
            {"text": "🔍  Test Proxy",  "callback_data": "test_proxy_btn"},
            {"text": "❌  Remove",      "callback_data": "remove_proxy_btn"},
        ],
        [{"text": "↪️  Back",           "callback_data": "gates"}],
    ]


# ══════════════════════════════════════════════════════════════════════════════
#  ▸ REDEEM INFO
# ══════════════════════════════════════════════════════════════════════════════

def rows_redeem_info():
    return [
        [{"text": "↪️  Back",  "callback_data": "plans"}],
    ]


# ══════════════════════════════════════════════════════════════════════════════
#  ▸ ADMIN PANEL
# ══════════════════════════════════════════════════════════════════════════════

def rows_admin():
    return [
        [
            {"text": "👥  Users",      "callback_data": "admin_users"},
            {"text": "🌐  Sites",      "callback_data": "admin_sites"},
        ],
        [
            {"text": "📢  Broadcast",  "callback_data": "admin_broadcast_info"},
            {"text": "⚙️  Proxy Pool", "callback_data": "admin_proxy_pool"},
        ],
        [{"text": "❌  Close",         "callback_data": "close"}],
    ]


# ══════════════════════════════════════════════════════════════════════════════
#  ▸ ADMIN ▸ USERS
# ══════════════════════════════════════════════════════════════════════════════

def rows_admin_users():
    return [
        [{"text": "📋  Premium List", "callback_data": "admin_list_users"}],
        [
            {"text": "✅  Add User",   "callback_data": "admin_add_user_info"},
            {"text": "❌  Remove",     "callback_data": "admin_rm_user_info"},
        ],
        [{"text": "🚫  Banned List",  "callback_data": "admin_banned_list"}],
        [{"text": "↪️  Back",         "callback_data": "admin_panel"}],
    ]


# ══════════════════════════════════════════════════════════════════════════════
#  ▸ ADMIN ▸ SITES
# ══════════════════════════════════════════════════════════════════════════════

def rows_admin_sites():
    return [
        [{"text": "📋  Site List",     "callback_data": "admin_list_sites_cb"}],
        [
            {"text": "✅  Add Site",   "callback_data": "admin_add_site_info"},
            {"text": "❌  Remove",     "callback_data": "admin_rm_site_info"},
        ],
        [{"text": "🔍  Health Check",  "callback_data": "admin_check_sites"}],
        [{"text": "↪️  Back",          "callback_data": "admin_panel"}],
    ]


# ══════════════════════════════════════════════════════════════════════════════
#  ▸ ADMIN ▸ PROXY POOL
# ══════════════════════════════════════════════════════════════════════════════

def rows_admin_proxy_pool():
    return [
        [{"text": "📋  View Pool",     "callback_data": "admin_list_proxy_cb"}],
        [
            {"text": "✅  Add Proxy",  "callback_data": "admin_add_proxy_info"},
            {"text": "❌  Remove",     "callback_data": "admin_rm_proxy_info"},
        ],
        [{"text": "🔍  Test Pool",     "callback_data": "admin_check_proxies"}],
        [{"text": "🧹  Clear Pool",    "callback_data": "admin_clear_proxy_cb"}],
        [{"text": "↪️  Back",          "callback_data": "admin_panel"}],
    ]


# ══════════════════════════════════════════════════════════════════════════════
#  ▸ ADMIN ▸ BROADCAST
# ══════════════════════════════════════════════════════════════════════════════

def rows_admin_broadcast():
    return [
        [{"text": "↪️  Back", "callback_data": "admin_panel"}],
    ]


# ══════════════════════════════════════════════════════════════════════════════
#  ▸ LEGACY HELPERS (purane bot.py handlers ke liye)
# ══════════════════════════════════════════════════════════════════════════════

def rows_features():
    return rows_commands()


def rows_admin_keys():
    return [
        [{"text": "🔑  Generate Keys", "callback_data": "admin_gen_keys"}],
        [{"text": "📋  View Keys",     "callback_data": "admin_view_keys"}],
        [{"text": "🗑️  Clear Keys",   "callback_data": "admin_clear_keys"}],
        [{"text": "↪️  Back",          "callback_data": "admin_panel"}],
    ]


def rows_admin_stats():
    return [
        [{"text": "📈  View Stats",   "callback_data": "admin_view_stats"}],
        [{"text": "🗑️  Clear Stats", "callback_data": "admin_clear_stats"}],
        [{"text": "↪️  Back",         "callback_data": "admin_panel"}],
    ]


def rows_admin_gifs():
    return [
        [{"text": "📋  GIF List",     "callback_data": "admin_gif_list"}],
        [
            {"text": "✅  Add GIF",   "callback_data": "admin_add_gif"},
            {"text": "❌  Remove",    "callback_data": "admin_rm_gif"},
        ],
        [{"text": "↪️  Back",         "callback_data": "admin_panel"}],
    ]


def rows_admin_logs():
    return [
        [{"text": "📢  Set Log Group", "callback_data": "admin_set_log"}],
        [{"text": "🔍  Check Log",     "callback_data": "admin_check_log"}],
        [{"text": "↪️  Back",          "callback_data": "admin_panel"}],
    ]


def rows_admin_welcome():
    return [
        [{"text": "💬  Set Welcome",   "callback_data": "admin_set_welcome"}],
        [{"text": "📋  View Welcome",  "callback_data": "admin_view_welcome"}],
        [{"text": "🔄  Reset Welcome", "callback_data": "admin_reset_welcome"}],
        [{"text": "↪️  Back",          "callback_data": "admin_panel"}],
    ]


def rows_admin_workers():
    return [
        [{"text": "🔧  Set Workers",  "callback_data": "admin_set_workers"}],
        [{"text": "↪️  Back",         "callback_data": "admin_panel"}],
    ]


def rows_admin_videos():
    return [
        [{"text": "📋  Video List",    "callback_data": "admin_video_list"}],
        [
            {"text": "✅  Add Video", "callback_data": "admin_add_video"},
            {"text": "❌  Remove",    "callback_data": "admin_rm_video"},
        ],
        [{"text": "↪️  Back",          "callback_data": "admin_panel"}],
    ]


def rows_stop():
    return [[{"text": "🛑  Stop", "callback_data": "stop_mass"}]]


def rows_back():
    return [[{"text": "↪️  Back", "callback_data": "back_start"}]]


def rows_admin_back():
    return [[{"text": "↪️  Back", "callback_data": "admin_panel"}]]


# ══════════════════════════════════════════════════════════════════════════════
#  ▸ NOTIFICATION HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _send_notification(chat_id, text) -> int | None:
    try:
        r = _raw_post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        })
        if r.get("ok"):
            return r["result"]["message_id"]
    except Exception:
        pass
    return None


def _pin_message_botapi(chat_id, message_id):
    try:
        _raw_post(f"https://api.telegram.org/bot{BOT_TOKEN}/pinChatMessage", {
            "chat_id": chat_id,
            "message_id": message_id,
            "disable_notification": False,
        })
    except Exception:
        pass