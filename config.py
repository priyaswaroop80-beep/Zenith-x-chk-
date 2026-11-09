import os
import json

# ══════════════════════════════════════════════════════════════════════════════
#  ▸ TELEGRAM API CREDENTIALS
# ══════════════════════════════════════════════════════════════════════════════
API_ID    = int(os.environ.get('API_ID',    '23932993'))
API_HASH  =     os.environ.get('API_HASH',  '4337dc3f13c43f109509b4fae6dfdbaf')
BOT_TOKEN =     os.environ.get('BOT_TOKEN', '8447205866:AAFLtyMlfCl9j_mLkdoUFo2D8zApHsSH_BY')
TG_API    = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ══════════════════════════════════════════════════════════════════════════════
#  ▸ BOT BRANDING
# ══════════════════════════════════════════════════════════════════════════════
BOT_BRAND      = '𝑹𝑿𝑷 𝑪𝑯𝑬𝑪𝑲'
BOT_NAME       = '𝑹𝑿𝑷 𝑪𝑯𝑬𝑪𝑲'
OWNER_NAME     = '𝑼𝑵𝑴𝑶𝑵𝑬𝒀'
OWNER_USERNAME = 'realearning077'
OWNER_ID       = 8524509023
DEV_LINE       = f'🤖 𝐁𝐨𝐭 𝐃𝐞𝐯 ➜ 🥶⃤𝑹𝑿𝑷 𝑪𝑯𝑬𝑪𝑲 💀⃤'

# ══════════════════════════════════════════════════════════════════════════════
#  ▸ MASS CHECK — STABLE TUNING
# ══════════════════════════════════════════════════════════════════════════════
# WORKERS: 8 = stable, 12 = balanced, 20 = aggressive (more errors)
MASS_WORKERS = int(os.environ.get("MASS_WORKERS", "100"))  # per user  # per user  # safe per-user  # PER USER  # PER USER

# Timeout per card (seconds) — full checkout can take 60-120s
CARD_TIMEOUT = int(os.environ.get('CARD_TIMEOUT', '30'))

# Max retries per card on network error
MAX_RETRIES = int(os.environ.get('MAX_RETRIES', '3'))

# Rate limit window (seconds) — time between two checks on same card
CHECK_COOLDOWN = 0


# ══════════════════════════════════════════════════════════════════════════════
# Delay between requests (seconds) — higher = safer, lower = faster
REQUEST_DELAY_MIN = 0.0
REQUEST_DELAY_MAX = 0.0

# Same site gap (seconds) — prevent hitting same site too fast
SITE_PROXY_GAP_S = 0.0

# ══════════════════════════════════════════════════════════════════════════════
#  ▸ LOG CHANNEL
# ══════════════════════════════════════════════════════════════════════════════
LOG_CHANNEL_ID = int(os.environ.get('LOG_CHANNEL_ID', '-1001234567890'))

# ══════════════════════════════════════════════════════════════════════════════
#  ▸ ADMIN MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════
_ADMIN_FILE     = os.path.join(os.path.dirname(__file__), 'admin.json')
_DEFAULT_ADMINS = (
    {int(x.strip()) for x in os.environ.get('ADMIN_ID', '').split(',') if x.strip().isdigit()}
    | ({OWNER_ID} if OWNER_ID else set())
)


def _load_admin_ids() -> set:
    try:
        with open(_ADMIN_FILE) as f:
            data = json.load(f)
            ids  = data.get('admin_ids', [])
            return set(ids) | _DEFAULT_ADMINS if ids else _DEFAULT_ADMINS
    except Exception:
        return _DEFAULT_ADMINS


def _save_admin_ids(ids: set):
    try:
        with open(_ADMIN_FILE) as f:
            data = json.load(f)
    except Exception:
        data = {}
    data['admin_ids'] = list(ids)
    with open(_ADMIN_FILE, 'w') as f:
        json.dump(data, f)


ADMIN_IDS = _load_admin_ids()
ADMIN_ID  = OWNER_ID

# ══════════════════════════════════════════════════════════════════════════════
#  ▸ FILES
# ══════════════════════════════════════════════════════════════════════════════
PREMIUM_FILE    = 'premium.txt'
SITES_FILE      = 'sites.txt'
PROXY_FILE      = 'proxy.txt'
USER_PROXY_FILE = 'user_proxies.json'
USER_POOL_FILE  = 'user_pool.json'
BANNED_FILE     = 'banned.txt'
KEYS_FILE       = 'keys.txt'
LIMITS_FILE     = 'limits.json'
VIDEOS_FILE     = 'videos.txt'
GIFS_FILE       = 'gifs.txt'
WELCOME_FILE    = 'welcome.txt'
LOG_FILE        = 'log_group.txt'

# ══════════════════════════════════════════════════════════════════════════════
#  ▸ LIMITS
# ══════════════════════════════════════════════════════════════════════════════
LIMITS = {
    "admin":   999999999999,
    "premium": 100000,
}


# ══════════════════════════════════════════════════════════════════════════════
#  ▸ PER-USER DIVISION (simple, no queue)
# ══════════════════════════════════════════════════════════════════════════════
PROXIES_PER_USER   = int(os.environ.get('PROXIES_PER_USER',   '15'))    # random from pool
SITES_PER_USER     = int(os.environ.get('SITES_PER_USER',     '0'))     # 0 = all sites


# ══════════════════════════════════════════════════════════════════════════════
#  ▸ MULTI-USER SAFETY
# ══════════════════════════════════════════════════════════════════════════════
MAX_USERS_CONCURRENT = int(os.environ.get('MAX_USERS_CONCURRENT', '3'))


# ══════════════════════════════════════════════════════════════════════════════
#  ▸ GLOBAL LOAD BALANCING (multi-user safety)
# ══════════════════════════════════════════════════════════════════════════════
GLOBAL_MAX_WORKERS    = int(os.environ.get('GLOBAL_MAX_WORKERS',    '250'))
MAX_CONCURRENT_CHECKS = int(os.environ.get('MAX_CONCURRENT_CHECKS', '3'))
LIGHT_LOAD_WORKERS    = int(os.environ.get('LIGHT_LOAD_WORKERS',    '100'))
MEDIUM_LOAD_WORKERS   = int(os.environ.get('MEDIUM_LOAD_WORKERS',   '70'))
HEAVY_LOAD_WORKERS    = int(os.environ.get('HEAVY_LOAD_WORKERS',    '50'))


# ══════════════════════════════════════════════════════════════════════════════
#  ▸ POOL SETTINGS
# ══════════════════════════════════════════════════════════════════════════════
POOL_ENABLED_FILE = 'pool_enabled.txt'   # "1" = ON, "0" = OFF
AUTO_CHECK_INTERVAL = 7200                # 2 hours in seconds
