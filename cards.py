from config import OWNER_NAME, OWNER_USERNAME
from emojis import SEP, pe


# ══════════════════════════════════════════════════════════════════════════════
#  ▸ RESPONSE CLEANER  (bold unicode)
# ══════════════════════════════════════════════════════════════════════════════
def _clean_response(msg: str) -> str:
    m = (msg or "").lower()
    if 'payment captured' in m or 'payment was successful' in m or 'captured successfully' in m:
        return '𝙿𝚊𝚢𝚖𝚎𝚗𝚝 𝚠𝚊𝚜 𝚜𝚞𝚌𝚌𝚎𝚜𝚜𝚏𝚞𝚕'
    if 'auth' in m and ('approved' in m or 'success' in m):
        return '𝙰𝚞𝚝𝚑 𝚊𝚙𝚙𝚛𝚘𝚟𝚎𝚍'
    if 'approved' in m and '3ds not required' in m:
        return '𝙰𝚙𝚙𝚛𝚘𝚟𝚎𝚍 — 𝚗𝚘 𝟹𝙳𝚂'
    if 'approved' in m and '3ds' not in m:
        return '𝙲𝚊𝚛𝚍 𝚊𝚙𝚙𝚛𝚘𝚟𝚎𝚍'
    if 'insufficient' in m or 'not enough' in m or 'low balance' in m:
        return '𝙸𝚗𝚜𝚞𝚏𝚏𝚒𝚌𝚒𝚎𝚗𝚝 𝙵𝚞𝚗𝚍𝚜 — 𝙲𝚊𝚛𝚍 𝙻𝚒𝚟𝚎'
    if 'do not honor' in m or 'do not honour' in m:
        return '𝙳𝚘 𝚗𝚘𝚝 𝚑𝚘𝚗𝚘𝚛'
    if 'card_declined' in m or 'card was declined' in m or 'card has been declined' in m or 'transaction declined' in m:
        return '𝙲𝚊𝚛𝚍 𝙳𝚎𝚌𝚕𝚒𝚗𝚎𝚍'
    if 'declined' in m:
        return '𝙳𝚎𝚌𝚕𝚒𝚗𝚎𝚍'
    if 'otp_required' in m or '3d secure' in m or '3ds' in m or 'authentication required' in m or 'otp required' in m:
        return '𝟹𝙳𝚂 𝚁𝚎𝚚𝚞𝚒𝚛𝚎𝚍'
    if 'invalid card' in m or 'invalid number' in m:
        return '𝙸𝚗𝚟𝚊𝚕𝚒𝚍 𝙲𝚊𝚛𝚍'
    if 'expired' in m:
        return '𝙲𝚊𝚛𝚍 𝙴𝚡𝚙𝚒𝚛𝚎𝚍'
    if 'incorrect cvc' in m or 'invalid cvc' in m or 'security code' in m:
        return '𝙸𝚗𝚟𝚊𝚕𝚒𝚍 𝙲𝚅𝚅'
    if 'lost' in m:
        return '𝙲𝚊𝚛𝚍 𝚁𝚎𝚙𝚘𝚛𝚝𝚎𝚍 𝙻𝚘𝚜𝚝'
    if 'stolen' in m:
        return '𝙲𝚊𝚛𝚍 𝚁𝚎𝚙𝚘𝚛𝚝𝚎𝚍 𝚂𝚝𝚘𝚕𝚎𝚗'
    if 'pickup' in m:
        return '𝙲𝚊𝚛𝚍 𝙿𝚒𝚌𝚔𝚞𝚙 𝚁𝚎𝚚𝚞𝚒𝚛𝚎𝚍'
    if 'limit' in m or 'exceeded' in m:
        return '𝙻𝚒𝚖𝚒𝚝 𝙴𝚡𝚌𝚎𝚎𝚍𝚎𝚍'
    if 'captcha' in m:
        return '𝙲𝙰𝙿𝚃𝙲𝙷𝙰 𝚁𝚎𝚚𝚞𝚒𝚛𝚎𝚍'
    if 'throttled' in m:
        return '𝚃𝚑𝚛𝚘𝚝𝚝𝚕𝚎𝚍'
    if 'checkpoint' in m:
        return '𝙲𝚑𝚎𝚌𝚔𝚙𝚘𝚒𝚗𝚝 𝙳𝚎𝚗𝚒𝚎𝚍'
    if 'mismatched_bill' in m or 'mismatched bill' in m:
        return '𝙼𝚒𝚜𝚖𝚊𝚝𝚌𝚑𝚎𝚍 𝙱𝚒𝚕𝚕'
    if 'payment_failed' in m or 'payment failed' in m:
        return '𝙿𝚊𝚢𝚖𝚎𝚗𝚝 𝙵𝚊𝚒𝚕𝚎𝚍'
    if 'site requires login' in m:
        return '𝚂𝚒𝚝𝚎 𝚁𝚎𝚚𝚞𝚒𝚛𝚎𝚜 𝙻𝚘𝚐𝚒𝚗'
    if 'site not supported' in m:
        return '𝚂𝚒𝚝𝚎 𝙽𝚘𝚝 𝚂𝚞𝚙𝚙𝚘𝚛𝚝𝚎𝚍'
    if 'payment method not available' in m:
        return '𝙿𝚊𝚢𝚖𝚎𝚗𝚝 𝙼𝚎𝚝𝚑𝚘𝚍 𝙽𝚘𝚝 𝙰𝚟𝚊𝚒𝚕𝚊𝚋𝚕𝚎'
    if 'change proxy' in m:
        return '𝙲𝚑𝚊𝚗𝚐𝚎 𝙿𝚛𝚘𝚡𝚢 𝚘𝚛 𝚂𝚒𝚝𝚎'
    if 'application not found' in m or '404' in m:
        return '𝙰𝙿𝙸 𝙴𝚛𝚛𝚘𝚛 — 𝟺𝟶𝟺'
    if 'timeout' in m or 'timed out' in m:
        return '𝚁𝚎𝚚𝚞𝚎𝚜𝚝 𝚃𝚒𝚖𝚎𝚘𝚞𝚝'
    return msg[:80] if msg and len(msg) > 80 else (msg or "-")


def _is_insufficient(msg: str) -> bool:
    m = (msg or "").lower()
    return 'insufficient' in m or 'not enough' in m or 'low balance' in m


# ══════════════════════════════════════════════════════════════════════════════
#  ▸ RAW API STATUS LABEL  (bold unicode)
#  Shows the exact API response code, converted to bold sans-serif.
# ══════════════════════════════════════════════════════════════════════════════
def _raw_status_label(result: dict) -> str:
    """
    Returns the raw API response code in bold unicode.

    Examples:
        ORDER_PLACED     → 𝙾𝚁𝙳𝙴𝚁 𝙿𝙻𝙰𝙲𝙴𝙳
        CARD_DECLINED    → 𝙲𝙰𝚁𝙳 𝙳𝙴𝙲𝙻𝙸𝙽𝙴𝙳
        OTP_REQUIRED     → 𝙾𝚃𝙿 𝚁𝙴𝚀𝚄𝙸𝚁𝙴𝙳
    """
    # Try to get raw_response from result (set by check_engine)
    raw = result.get('raw_response') or result.get('message') or 'UNKNOWN'
    raw = str(raw).strip()
    if not raw:
        return '𝚄𝙽𝙺𝙽𝙾𝚆𝙽'
    return _to_bold_upper(raw)


# ══════════════════════════════════════════════════════════════════════════════
#  ▸ BOLD UPPER CONVERTER  (ASCII → Mathematical Bold Sans-Serif uppercase)
# ══════════════════════════════════════════════════════════════════════════════
_BOLD_UPPER_MAP = {
    'A': '𝙰', 'B': '𝙱', 'C': '𝙲', 'D': '𝙳', 'E': '𝙴', 'F': '𝙵', 'G': '𝙶',
    'H': '𝙷', 'I': '𝙸', 'J': '𝙹', 'K': '𝙺', 'L': '𝙻', 'M': '𝙼', 'N': '𝙽',
    'O': '𝙾', 'P': '𝙿', 'Q': '𝚀', 'R': '𝚁', 'S': '𝚂', 'T': '𝚃', 'U': '𝚄',
    'V': '𝚅', 'W': '𝚆', 'X': '𝚇', 'Y': '𝚈', 'Z': '𝚉',
    '0': '𝟶', '1': '𝟷', '2': '𝟸', '3': '𝟹', '4': '𝟺',
    '5': '𝟻', '6': '𝟼', '7': '𝟽', '8': '𝟾', '9': '𝟿',
    ' ': ' ', '_': ' ', '-': ' ', '.': '.', '!': '!',
}


def _to_bold_upper(text: str) -> str:
    """Convert ASCII to bold uppercase unicode. Preserves non-ASCII."""
    if not text:
        return text
    out = []
    for ch in text:
        out.append(_BOLD_UPPER_MAP.get(ch.upper(), ch))
    return ''.join(out)


# ══════════════════════════════════════════════════════════════════════════════
#  ▸ CHECKER LINE  (legacy helper)
# ══════════════════════════════════════════════════════════════════════════════
def checker_line(uid: int, display_name: str) -> str:
    return f'[⌯] 𝗖𝗵𝗲𝗰𝗸𝗲𝗿 ⌁ 🔰 {display_name}'


def _result_header(status: str) -> tuple[str, str]:
    if status == 'Charged':  return ("[⌯] 𝗖𝗵𝗮𝗿𝗴𝗲𝗱 𝗦𝘂𝗰𝗰𝗲𝘀𝘀 ⌁ 💎",  "𝙲𝚑𝚊𝚛𝚐𝚎𝚍 𝚂𝚞𝚌𝚌𝚎𝚜𝚜𝚏𝚞𝚕𝚕𝚢")
    if status == 'Approved': return ("[⌯] 𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱 ⌁ ✅",           "𝙰𝚙𝚙𝚛𝚘𝚟𝚎𝚍")
    if status == '3DS':      return ("[⌯] 𝟯𝗗𝗦 𝗥𝗲𝗾𝘂𝗶𝗿𝗲𝗱 ⌁ ⚠️",         "𝟹𝙳𝚂 𝚁𝚎𝚚𝚞𝚒𝚛𝚎𝚍")
    return ("[⌯] 𝙳𝚎𝚌𝚕𝚒𝚗𝚎𝚍 ⌁ ❌", "𝙳𝚎𝚌𝚕𝚒𝚗𝚎𝚍")


# ══════════════════════════════════════════════════════════════════════════════
#  ▸ BUILD RESULT CARD  (bold + [⌯] + raw API status)
# ══════════════════════════════════════════════════════════════════════════════
def build_result_card(result: dict, bin_info: tuple, uid: int, cname: str) -> str:
    """EXACT screenshot format — bold uppercase everywhere."""
    brand, btype, level, bank, country, flag = bin_info
    status = result.get('status', 'Dead')
    resp_clean = _clean_response(result.get('message', ''))

    # ═══ BOLD UPPERCASE MAP ═══════════════════════════════════════════════════
    # Handles A-Z, a-z, 0-9, spaces, hyphens, dots
    def _b(s):
        """Convert to Mathematical Bold Sans-Serif."""
        out = []
        for ch in str(s):
            c = ord(ch)
            if 65 <= c <= 90:          # A-Z
                out.append(chr(c - 65 + 0x1D5D4))
            elif 97 <= c <= 122:       # a-z
                out.append(chr(c - 97 + 0x1D5EE))
            elif 48 <= c <= 57:        # 0-9
                out.append(chr(c - 48 + 0x1D7EC))
            else:
                out.append(ch)         # spaces, dots, etc.
        return "".join(out)

    # ═══ HEADER + STATUS (exact screenshot) ══════════════════════════════════
    if status == 'Charged':
        header = "[⌯] 𝗖𝗵𝗮𝗿𝗴𝗲𝗱 ⌁ 💎"
        status_text = _b("Charged")
        status_emoji = "💎"
        result_line = _b("Payment was successful")
        result_emoji = "💎"
    elif status == 'Approved':
        header = "[⌯] 𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱 ⌁ ✅"
        status_text = _b("Approved")
        status_emoji = "✅"
        result_line = _b(resp_clean or "Payment Approved")
        result_emoji = "✅"
    elif status == '3DS':
        header = "[⌯] 𝟯𝗗𝗦 𝗥𝗲𝗾𝘂𝗶𝗿𝗲𝗱 ⌁ ⚠️"
        status_text = _b("3DS Required")
        status_emoji = "⚠️"
        result_line = _b("OTP Required")
        result_emoji = "⚠️"
    elif status == 'Live' or _is_insufficient(resp_clean):
        header = "[⌯] 𝗟𝗶𝘃𝗲 ⌁ 💳"
        status_text = _b("Live")
        status_emoji = "💳"
        result_line = _b("Insufficient Funds — Card Live")
        result_emoji = "💳"
    else:
        header = "[⌯] 𝗗𝗲𝗰𝗹𝗶𝗻𝗲𝗱 ⌁ ❌"
        status_text = _b("Declined")
        status_emoji = "❌"
        # ═══ Use REAL raw API message ═══
        _gw = str(result.get('gateway') or '')
        _raw_msg = str(result.get('message') or '').strip()
        if _raw_msg and _raw_msg not in ('-', '0', 'Unknown', 'N/A', 'None', 'null', 'Card Declined'):
            result_line = _b(_raw_msg)
        elif resp_clean and resp_clean not in ('-', '0', 'Unknown', 'N/A', 'None'):
            result_line = _b(resp_clean)
        else:
            result_line = _b("Card Declined")
        result_emoji = "❌"

    # ═══ BIN (bold uppercase, remove dots-spaces) ═════════════════════════════
    bin_parts_raw = " · ".join(p for p in [brand, btype, level] if p and p != '-') or "—"
    # Convert "·" to "·" and uppercase letters
    bin_parts = _b(bin_parts_raw)

    bank_b = _b(bank or "—") if bank and bank != '-' else "—"

    # ═══ Country (flag + bold uppercase) ══════════════════════════════════════
    country_clean = (country or "").strip()
    if flag and country_clean and country_clean != '-':
        country_str = f"{flag} {_b(country_clean)}"
    elif country_clean and country_clean != '-':
        country_str = _b(country_clean)
    else:
        country_str = "—"

    # ═══ Gateway (bold uppercase) ═════════════════════════════════════════════
    gateway = result.get('gateway', 'Shopify Payments') or 'Shopify Payments'
    gateway_b = _b(gateway)

    # ═══ Amount (bold uppercase) ══════════════════════════════════════════════
    price = result.get('price', '-')
    _p = str(price).replace('$', '').replace('£', '').replace('€', '').strip()
    _currency = "USD"
    _sym = "$"
    _raw_upper = (result.get('message') or '').upper() + str(price).upper()
    if 'GBP' in _raw_upper or '£' in str(price):
        _currency = "GBP"; _sym = "£"
    elif 'EUR' in _raw_upper or '€' in str(price):
        _currency = "EUR"; _sym = "€"

    if _p not in ('-', '', 'None', '0', '0.00', '0.0'):
        price_str = f"{_sym}{_b(_p)} {_b(_currency)} ⌁ ⚡"
    else:
        price_str = "—"

    # ═══ Time (bold uppercase) ════════════════════════════════════════════════
    t = result.get('time')
    if t is not None:
        # "9.6s" → bold digits + bold "s"
        _t_str = str(t)
        time_str = f"{_b(_t_str)}s ⌁ ⚡"
    else:
        time_str = "—"

    # ═══ Checker (user mention) ═══════════════════════════════════════════════
    checker_display = cname if cname else str(uid)

    # ═══ Card ════════════════════════════════════════════════════════════════
    card = result.get('card', '-')

    # ═══ BUILD ═══════════════════════════════════════════════════════════════
    text = (
        f"{header}\n"
        f"─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n"
        f"[⌯] 𝗖𝗖 ⌁ <code>{card}</code>\n"
        f"[⌯] 𝗦𝘁𝗮𝘁𝘂𝘀 ⌁ {status_text} {status_emoji}\n"
        f"[⌯] 𝗥𝗲𝘀𝘂𝗹𝘁 ⌁ {result_line} {result_emoji}\n"
        f"─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n"
        f"[⌯] 𝗕𝗜𝗡 ⌁ {bin_parts}\n"
        f"[⌯] 𝗕𝗮𝗻𝗸 ⌁ {bank_b}\n"
        f"[⌯] 𝗖𝗼𝘂𝗻𝘁𝗿𝘆 ⌁ {country_str}\n"
        f"─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n"
        f"[⌯] 𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⌁ {gateway_b}\n"
        + ("" if gateway == "Stripe Auth" else f"[⌯] 𝗔𝗺𝗼𝘂𝗻𝘁 ⌁ {price_str}\n")
        + f"[⌯] 𝗧𝗶𝗺𝗲 ⌁ {time_str}\n"
        f"─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n"
        f"[⌯] 𝗖𝗵𝗲𝗰𝗸𝗲𝗿 ⌁ 👾 {checker_display}"
    )

    return pe(text)
