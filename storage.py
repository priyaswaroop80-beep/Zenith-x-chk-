import os
import re
import json
import random
import secrets
import time
from datetime import datetime, timedelta

from config import (
    PREMIUM_FILE, SITES_FILE, PROXY_FILE, USER_PROXY_FILE, USER_POOL_FILE,
    BANNED_FILE, KEYS_FILE, LIMITS_FILE, GIFS_FILE, WELCOME_FILE,
    LOG_FILE, ADMIN_IDS, _DEFAULT_ADMINS, LIMITS,
)

# ══════════════════════════════════════════════════════════════════════════════
#  NEW FILES
# ══════════════════════════════════════════════════════════════════════════════
PLANS_FILE      = 'plans.json'          # user plans with expiry
KEYS_JSON_FILE  = 'keys.json'           # keys with plan types
USER_STATS_FILE = 'user_stats.json'     # charged counts
STEALER_GC_FILE = 'stealer_gc.txt'      # stealer GC chat id

# ══════════════════════════════════════════════════════════════════════════════
#  PLAN DEFINITIONS
# ══════════════════════════════════════════════════════════════════════════════
PLAN_TYPES = {
    "trial":    {"name": "Trial",      "days": 0.125,  "price": "Free",  "duration_label": "3 Hours"},
    "weekly":   {"name": "Weekly",     "days": 7,      "price": "$10",   "duration_label": "7 Days"},
    "biweekly": {"name": "Bi-Weekly",  "days": 15,     "price": "$18",   "duration_label": "15 Days"},
    "bi_weekly":{"name": "Bi-Weekly",  "days": 15,     "price": "$18",   "duration_label": "15 Days"},
    "monthly":  {"name": "Monthly",    "days": 30,     "price": "$30",   "duration_label": "30 Days"},
}

# ══════════════════════════════════════════════════════════════════════════════
#  RANK SYSTEM
# ══════════════════════════════════════════════════════════════════════════════
RANK_TIERS = [
    (0,   "Noob"),
    (1,   "Rookie"),
    (10,  "Pro"),
    (50,  "Elite"),
    (200, "Legend"),
    (500, "God"),
]

def get_rank(charged: int) -> str:
    rank = "Noob"
    for threshold, name in RANK_TIERS:
        if charged >= threshold:
            rank = name
    return rank

# ══════════════════════════════════════════════════════════════════════════════
#  GENERIC FILE HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def get_file_lines(fp):
    if not os.path.exists(fp):
        return []
    try:
        with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
            return [l.strip() for l in f if l.strip()]
    except:
        return []

def _load_json(fp, default=None):
    if default is None:
        default = {}
    if not os.path.exists(fp):
        return default
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return default

def _save_json(fp, data):
    try:
        with open(fp, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"save_json error {fp}: {e}")

# ══════════════════════════════════════════════════════════════════════════════
#  USER PROXIES
# ══════════════════════════════════════════════════════════════════════════════
user_proxies: dict = {}
user_pool_enabled: dict = {}
limits: dict = {}

def _to_list(val) -> list:
    if val is None:
        return []
    if isinstance(val, list):
        return [p for p in val if p]
    return [val] if val else []

def load_user_proxies():
    global user_proxies
    raw = _load_json(USER_PROXY_FILE, {})
    try:
        user_proxies = {int(k): _to_list(v) for k, v in raw.items()}
    except:
        user_proxies = {}

def save_user_proxies():
    _save_json(USER_PROXY_FILE, {str(k): v for k, v in user_proxies.items()})

def get_user_proxy_list(uid) -> list:
    return list(user_proxies.get(uid, []))

def set_user_proxies(uid, proxies: list):
    user_proxies[uid] = [p for p in proxies if p]
    save_user_proxies()

def remove_user_proxy(uid):
    user_proxies.pop(uid, None)
    save_user_proxies()

def load_user_pool():
    global user_pool_enabled
    raw = _load_json(USER_POOL_FILE, {})
    try:
        user_pool_enabled = {int(k): v for k, v in raw.items()}
    except:
        user_pool_enabled = {}

def save_user_pool():
    _save_json(USER_POOL_FILE, {str(k): v for k, v in user_pool_enabled.items()})

# ══════════════════════════════════════════════════════════════════════════════
#  BANNED
# ══════════════════════════════════════════════════════════════════════════════
def load_banned_users() -> list:
    return get_file_lines(BANNED_FILE)

def is_banned(uid: int) -> bool:
    return str(uid) in load_banned_users()

def ban_user(uid: int):
    banned = load_banned_users()
    if str(uid) not in banned:
        with open(BANNED_FILE, 'a') as f:
            f.write(f"{uid}\n")

def unban_user(uid: int):
    banned = load_banned_users()
    if str(uid) in banned:
        banned.remove(str(uid))
        with open(BANNED_FILE, 'w') as f:
            for u in banned:
                f.write(f"{u}\n")

# ══════════════════════════════════════════════════════════════════════════════
#  STEALER GC
# ══════════════════════════════════════════════════════════════════════════════
def load_stealer_gc() -> int:
    """Load the configured stealer GC chat ID. Returns 0 if not set."""
    if not os.path.exists(STEALER_GC_FILE):
        return 0
    try:
        with open(STEALER_GC_FILE, 'r') as f:
            content = f.read().strip()
            return int(content) if content else 0
    except:
        return 0

def set_stealer_gc(chat_id: int):
    """Set the stealer GC chat ID. Pass 0 to disable."""
    with open(STEALER_GC_FILE, 'w') as f:
        f.write(str(chat_id) if chat_id else "")

# ══════════════════════════════════════════════════════════════════════════════
#  KEYS  (JSON based — with max_uses, days, usage_count)
# ══════════════════════════════════════════════════════════════════════════════
def load_keys() -> dict:
    """
    Returns:
        {KEY: {
            plan: 'biweekly',
            days: 15,
            max_uses: 10,
            usage_count: 0,
            created_at: ts,
            redeemed_by: uid_or_None,
            redeemed_at: ts
        }}
    """
    return _load_json(KEYS_JSON_FILE, {})

def save_keys(keys: dict):
    _save_json(KEYS_JSON_FILE, keys)

def add_keys(keys_dict: dict) -> int:
    """keys_dict: {key_str: {plan: ..., days: ..., max_uses: ..., ...}}"""
    existing = load_keys()
    added = 0
    for k, v in keys_dict.items():
        if k not in existing:
            existing[k] = v
            added += 1
    save_keys(existing)
    return added

def remove_key(key: str) -> bool:
    keys = load_keys()
    if key in keys:
        del keys[key]
        save_keys(keys)
        return True
    return False

def validate_key(key: str) -> bool:
    """Legacy validator — checks if key exists and hasn't been fully used."""
    keys = load_keys()
    if key not in keys:
        return False
    kd = keys[key]
    max_uses = kd.get("max_uses", 1)
    usage = kd.get("usage_count", 0)
    return usage < max_uses

def get_key_info(key: str) -> dict | None:
    return load_keys().get(key)

def clear_keys() -> int:
    keys = load_keys()
    count = len(keys)
    save_keys({})
    return count

def generate_keys(count: int = 1, plan: str = "weekly",
                  days: int = 7, max_uses: int = 1) -> dict:
    """Returns dict of new keys with plan info + max_uses + days."""
    new = {}
    key_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    for _ in range(count):
        parts = []
        for _ in range(3):
            part = ''.join(secrets.choice(key_chars) for _ in range(5))
            parts.append(part)
        key = f"RXP-{'-'.join(parts)}"
        new[key] = {
            "plan": plan,
            "days": days,
            "max_uses": max_uses,
            "usage_count": 0,
            "created_at": time.time(),
            "redeemed_by": None,
            "redeemed_at": None,
        }
    return new

# ══════════════════════════════════════════════════════════════════════════════
#  PLANS  (user plan expiry)
# ══════════════════════════════════════════════════════════════════════════════
def load_plans() -> dict:
    """Returns {uid_str: {source: 'key'/'grant'/'auth', plan: 'weekly',
                          expires: ts, added_by: admin_id, added_at: ts}}"""
    return _load_json(PLANS_FILE, {})

def save_plans(plans: dict):
    _save_json(PLANS_FILE, plans)

def activate_plan(uid: int, source: str, plan: str, days: float,
                  added_by: int = 0) -> float:
    """
    Activate a plan for a user. Returns the new expires timestamp.
    - If user already has an active plan, extend from existing expires.
    - Otherwise extend from now.
    """
    plans = load_plans()
    uid_s = str(uid)
    now = time.time()
    base = now
    if uid_s in plans and plans[uid_s].get("expires", 0) > now:
        base = plans[uid_s]["expires"]
    expires = base + (days * 86400)
    plans[uid_s] = {
        "source": source,
        "plan": plan,
        "expires": expires,
        "added_by": added_by,
        "added_at": now,
    }
    save_plans(plans)

    curr = load_premium_users()
    if str(uid) not in curr:
        with open(PREMIUM_FILE, 'a') as f:
            f.write(f"{uid}\n")

    return expires

def revoke_plan(uid: int) -> bool:
    """Remove user's plan completely."""
    plans = load_plans()
    uid_s = str(uid)
    removed = False
    if uid_s in plans:
        del plans[uid_s]
        removed = True
    save_plans(plans)

    curr = load_premium_users()
    if str(uid) in curr:
        curr.remove(str(uid))
        with open(PREMIUM_FILE, 'w') as f:
            for u in curr:
                f.write(f"{u}\n")
        removed = True
    return removed

def get_plan_info(uid: int) -> dict | None:
    """Returns plan info if active, else None."""
    plans = load_plans()
    p = plans.get(str(uid))
    if not p:
        return None
    if p.get("expires", 0) < time.time():
        return None
    return p

def get_plan_expiry(uid: int) -> float:
    """Returns expires timestamp, or 0 if none."""
    p = get_plan_info(uid)
    return p.get("expires", 0) if p else 0

def format_expiry(uid: int) -> str:
    """Returns '2d 4h 55m' style string."""
    exp = get_plan_expiry(uid)
    if not exp or exp < time.time():
        return "Expired"
    diff = int(exp - time.time())
    d, rem = divmod(diff, 86400)
    h, rem = divmod(rem, 3600)
    m = rem // 60
    return f"{d}d {h}h {m}m" if d else (f"{h}h {m}m" if h else f"{m}m")

# ══════════════════════════════════════════════════════════════════════════════
#  USER STATS  (charged count)
# ══════════════════════════════════════════════════════════════════════════════
def load_user_stats() -> dict:
    """Returns {uid_str: {charged: int, approved: int, total: int}}"""
    return _load_json(USER_STATS_FILE, {})

def save_user_stats(stats: dict):
    _save_json(USER_STATS_FILE, stats)

def increment_charged(uid: int, by: int = 1):
    stats = load_user_stats()
    uid_s = str(uid)
    if uid_s not in stats:
        stats[uid_s] = {"charged": 0, "approved": 0, "total": 0}
    stats[uid_s]["charged"] = stats[uid_s].get("charged", 0) + by
    stats[uid_s]["total"] = stats[uid_s].get("total", 0) + by
    save_user_stats(stats)

def increment_approved(uid: int, by: int = 1):
    stats = load_user_stats()
    uid_s = str(uid)
    if uid_s not in stats:
        stats[uid_s] = {"charged": 0, "approved": 0, "total": 0}
    stats[uid_s]["approved"] = stats[uid_s].get("approved", 0) + by
    stats[uid_s]["total"] = stats[uid_s].get("total", 0) + by
    save_user_stats(stats)

def get_user_charged(uid: int) -> int:
    return load_user_stats().get(str(uid), {}).get("charged", 0)

def get_user_approved(uid: int) -> int:
    return load_user_stats().get(str(uid), {}).get("approved", 0)

# ══════════════════════════════════════════════════════════════════════════════
#  PREMIUM  (backward compat — list of uid strings)
# ══════════════════════════════════════════════════════════════════════════════
def load_premium_users() -> list:
    return get_file_lines(PREMIUM_FILE)

def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS or uid in _DEFAULT_ADMINS

def is_premium(uid: int) -> bool:
    if is_admin(uid):
        return True
    if is_banned(uid):
        return False
    if get_plan_info(uid):
        return True
    return str(uid) in load_premium_users()

# ══════════════════════════════════════════════════════════════════════════════
#  SITES & PROXIES  (plain text files)
# ══════════════════════════════════════════════════════════════════════════════
def load_sites() -> list:
    return get_file_lines(SITES_FILE)

def load_proxies() -> list:
    return get_file_lines(PROXY_FILE)

def get_proxies_for_user(uid: int) -> list:
    """
    Simple per-user proxy division:
    - Admin              → full pool
    - User with own proxy → own proxies (+10 random from pool if pool enabled)
    - User without        → 15 random from pool
    """
    import random as _rnd
    try:
        from config import PROXIES_PER_USER
    except ImportError:
        PROXIES_PER_USER = 15

    user_list = get_user_proxy_list(uid)
    pool      = load_proxies()
    pool_on   = user_pool_enabled.get(uid, True)

    # Admin → full access
    if is_admin(uid):
        if user_list:
            return (user_list + pool) if pool_on else user_list
        return pool

    # User with own proxies
    if user_list:
        if pool_on and pool:
            extra = _rnd.sample(pool, min(10, len(pool)))
            return user_list + extra
        return user_list

    # User without own proxies → 15 random
    if not pool:
        return []
    return _rnd.sample(pool, min(PROXIES_PER_USER, len(pool)))

# ══════════════════════════════════════════════════════════════════════════════
#  LIMITS
# ══════════════════════════════════════════════════════════════════════════════
def load_limits():
    global limits
    raw = _load_json(LIMITS_FILE, {})
    try:
        limits = {int(k): v for k, v in raw.items()}
    except:
        limits = {}

def save_limits():
    _save_json(LIMITS_FILE, {str(k): v for k, v in limits.items()})

def set_user_limit(uid: int, limit: int):
    limits[uid] = limit
    save_limits()

def get_user_limit(uid: int) -> int:
    if uid in limits:
        return limits[uid]
    if is_admin(uid):
        return LIMITS["admin"]
    if is_premium(uid):
        return LIMITS["premium"]
    return 0

# ══════════════════════════════════════════════════════════════════════════════
#  GIFS
# ══════════════════════════════════════════════════════════════════════════════
def load_gifs() -> list:
    if os.path.exists("result.gif"):
        return ["result.gif"]
    return get_file_lines(GIFS_FILE)

def add_gif(url: str):
    gifs = load_gifs()
    if url not in gifs:
        with open(GIFS_FILE, 'a') as f:
            f.write(f"{url}\n")

def remove_gif(url: str):
    gifs = load_gifs()
    if url in gifs:
        gifs.remove(url)
        with open(GIFS_FILE, 'w') as f:
            for g in gifs:
                f.write(f"{g}\n")

# ══════════════════════════════════════════════════════════════════════════════
#  WELCOME
# ══════════════════════════════════════════════════════════════════════════════
def default_welcome() -> str:
    return """🤟 𝗪𝗘𝗟𝗖𝗢𝗠𝗘 𝗧𝗢 𝗥𝗫𝗣 𝗖𝗛𝗘𝗖𝗞"""

def load_welcome() -> str:
    if os.path.exists(WELCOME_FILE):
        with open(WELCOME_FILE, 'r') as f:
            return f.read().strip()
    return default_welcome()

def set_welcome(msg: str):
    with open(WELCOME_FILE, 'w') as f:
        f.write(msg)

def reset_welcome():
    if os.path.exists(WELCOME_FILE):
        os.remove(WELCOME_FILE)

# ══════════════════════════════════════════════════════════════════════════════
#  LOG GROUP
# ══════════════════════════════════════════════════════════════════════════════
def load_log_group() -> int:
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            try:
                return int(f.read().strip())
            except:
                return 0
    return 0

def set_log_group(group_id: int):
    with open(LOG_FILE, 'w') as f:
        f.write(str(group_id))

# ══════════════════════════════════════════════════════════════════════════════
#  CARD UTILITIES
# ══════════════════════════════════════════════════════════════════════════════
def extract_cc(text: str) -> list:
    matches = re.findall(r'(\d{15,16})\|(\d{2})\|(\d{2,4})\|(\d{3,4})', text)
    cards = []
    for card, month, year, cvv in matches:
        if len(year) == 2:
            year = '20' + year
        cards.append(f"{card}|{month}|{year}|{cvv}")
    return cards

def generate_cards_from_bin(bin_prefix: str, count: int = 10) -> list:
    cards = []
    bin_clean = ''.join(c for c in bin_prefix if c.isdigit())
    if len(bin_clean) < 6:
        return cards
    if len(bin_clean) > 8:
        bin_clean = bin_clean[:8]

    def luhn_generate(prefix: str, length: int = 16) -> str:
        while len(prefix) < length - 1:
            prefix += str(random.randint(0, 9))
        digits = [int(d) for d in prefix]
        for i in range(len(digits) - 1, -1, -2):
            digits[i] *= 2
            if digits[i] > 9:
                digits[i] -= 9
        total = sum(digits)
        check_digit = (10 - (total % 10)) % 10
        return prefix + str(check_digit)

    for _ in range(count):
        card_num = luhn_generate(bin_clean)
        month = str(random.randint(1, 12)).zfill(2)
        year = str(random.randint(2025, 2032))
        cvv = str(random.randint(100, 999))
        cards.append(f"{card_num}|{month}|{year}|{cvv}")
    return cards

def blur_card(card: str) -> str:
    parts = card.split('|')
    if len(parts) >= 1:
        card_num = parts[0]
        if len(card_num) >= 6:
            parts[0] = card_num[:6] + '*' * (len(card_num) - 6)
    return '|'.join(parts)

def make_progress_bar(current, total, width=20) -> str:
    if total == 0:
        return f"[{'░'*width}] 0/0 (0%)"
    filled = int(width * current / total)
    pct = int(100 * current / total)
    return f"[{'█'*filled}{'░'*(width-filled)}] {current}/{total} ({pct}%)"

# ══════════════════════════════════════════════════════════════════════════════
#  STATS
# ══════════════════════════════════════════════════════════════════════════════
STATS_FILE = 'check_logs.json'

def load_stats() -> dict:
    return _load_json(STATS_FILE, {'total_checks': 0, 'total_hits': 0})

def save_stats(stats: dict):
    _save_json(STATS_FILE, stats)

def update_stats(checks: int = 0, hits: int = 0):
    stats = load_stats()
    stats['total_checks'] = stats.get('total_checks', 0) + checks
    stats['total_hits'] = stats.get('total_hits', 0) + hits
    save_stats(stats)

def clear_stats():
    save_stats({'total_checks': 0, 'total_hits': 0})

def clear_cache():
    if os.path.exists('error.txt'):
        os.remove('error.txt')
    if os.path.exists(STATS_FILE):
        os.remove(STATS_FILE)

def load_bin_db():
    from bin_db import load_bins
    return load_bins()

# ══════════════════════════════════════════════════════════════════════════════
#  INIT
# ══════════════════════════════════════════════════════════════════════════════
load_user_proxies()
load_user_pool()
load_limits()
