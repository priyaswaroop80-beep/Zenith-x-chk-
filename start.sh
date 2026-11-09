#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
#  RXP Checker Bot — Startup Script (Portable / Self-Contained)
#  - Stripe Auth API (port 9000) via stripe.py
#  - Telegram Bot (bot.py)
#  - Auto-restart on crash / Max retries — runs FOREVER (lifetime)
#  Usage: bash start.sh
# ══════════════════════════════════════════════════════════════════════════════

# ── Auto-detect script directory (jahan start.sh rakhi hai) ──────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || { echo "❌ Cannot cd to $SCRIPT_DIR"; exit 1; }

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${GREEN}🚀 Starting RXP Checker Bot...${NC}"
echo -e "${CYAN}📁 Working directory: $SCRIPT_DIR${NC}"

# ══════════════════════════════════════════════════════════════════════════════
#  1. KILL OLD PROCESSES (sirf isi folder ke)
# ══════════════════════════════════════════════════════════════════════════════
echo -e "${YELLOW}🧹 Cleaning old processes...${NC}"
pkill -f "$SCRIPT_DIR/bot.py"        2>/dev/null
pkill -f "$SCRIPT_DIR/stripe.py"     2>/dev/null
pkill -f "python3 bot.py"            2>/dev/null
pkill -f "python3 stripe.py"         2>/dev/null
pkill -f "uvicorn"                   2>/dev/null
screen -S rxpbot          -X quit    2>/dev/null
screen -S stripe_api      -X quit    2>/dev/null
screen -S stripe_monitor  -X quit    2>/dev/null
sleep 2

# ══════════════════════════════════════════════════════════════════════════════
#  2. START STRIPE API (stripe.py) — LIFETIME AUTO-RESTART
# ══════════════════════════════════════════════════════════════════════════════
if [ -f "$SCRIPT_DIR/stripe.py" ]; then
    echo -e "${GREEN}💳 Starting Stripe Auth API (port 9000)...${NC}"
    screen -dmS stripe_api bash -c "cd '$SCRIPT_DIR' && while true; do python3 stripe.py >> stripe.log 2>&1; echo '[$(date +%H:%M:%S)] stripe.py crashed — restarting in 5s' >> stripe.log; sleep 5; done"
    sleep 6

    STRIPE_CHECK=$(curl -s -m 5 "http://localhost:9000/" 2>/dev/null)
    if echo "$STRIPE_CHECK" | grep -q "Stripe Auth API"; then
        echo -e "${GREEN}✅ Stripe API is LIVE${NC}"
    else
        echo -e "${RED}❌ Stripe API failed — check stripe.log${NC}"
        tail -20 "$SCRIPT_DIR/stripe.log" 2>/dev/null
    fi
else
    echo -e "${YELLOW}⚠️  stripe.py not found — skipping${NC}"
fi

# ══════════════════════════════════════════════════════════════════════════════
#  3. START TELEGRAM BOT (bot.py) — LIFETIME AUTO-RESTART
# ══════════════════════════════════════════════════════════════════════════════
if [ -f "$SCRIPT_DIR/bot.py" ]; then
    echo -e "${GREEN}🤖 Starting Telegram Bot (bot.py)...${NC}"
    rm -rf "$SCRIPT_DIR/__pycache__" 2>/dev/null
    rm -f  "$SCRIPT_DIR/checker_bot.session-journal" 2>/dev/null
    screen -dmS rxpbot bash -c "cd '$SCRIPT_DIR' && while true; do python3 bot.py >> bot.log 2>&1; echo '[$(date +%H:%M:%S)] bot.py crashed — restarting in 5s' >> bot.log; sleep 5; done"
    sleep 8

    if tail -30 "$SCRIPT_DIR/bot.log" 2>/dev/null | grep -q "started successfully"; then
        echo -e "${GREEN}✅ Telegram Bot is LIVE${NC}"
    else
        echo -e "${YELLOW}⚠️  Bot status unknown — check bot.log${NC}"
        tail -20 "$SCRIPT_DIR/bot.log" 2>/dev/null
    fi
else
    echo -e "${RED}❌ bot.py not found in $SCRIPT_DIR — skipping${NC}"
fi

# ══════════════════════════════════════════════════════════════════════════════
#  4. STRIPE MONITOR — auto-restart if "Max retries" / API down (FOREVER)
# ══════════════════════════════════════════════════════════════════════════════
echo -e "${GREEN}👁️  Starting Stripe monitor (60s interval)...${NC}"
screen -dmS stripe_monitor bash -c "
cd '$SCRIPT_DIR'
while true; do
    sleep 60
    RESP=\$(curl -s -m 15 'http://localhost:9000/stripe_auth?cc=4111111111111111|12|25|123' 2>/dev/null)

    if [ -z \"\$RESP\" ]; then
        echo \"[\$(date +%H:%M:%S)] ❌ API down — restarting...\" >> stripe_monitor.log
        pkill -f 'python3 stripe.py' 2>/dev/null
        screen -S stripe_api -X quit 2>/dev/null
        sleep 3
        screen -dmS stripe_api bash -c \"cd '$SCRIPT_DIR' && while true; do python3 stripe.py >> stripe.log 2>&1; sleep 5; done\"
        sleep 8
        continue
    fi

    if echo \"\$RESP\" | grep -q 'Max retries'; then
        if [ -f /tmp/stripe_maxretry_count ]; then
            COUNT=\$(cat /tmp/stripe_maxretry_count)
            COUNT=\$((COUNT + 1))
        else
            COUNT=1
        fi
        echo \"\$COUNT\" > /tmp/stripe_maxretry_count
        echo \"[\$(date +%H:%M:%S)] ⚠️  Max retries (\$COUNT/3)\" >> stripe_monitor.log

        if [ \"\$COUNT\" -ge 3 ]; then
            echo \"[\$(date +%H:%M:%S)] 🔄 Restarting Stripe API (hCaptcha likely expired)\" >> stripe_monitor.log
            pkill -f 'python3 stripe.py' 2>/dev/null
            screen -S stripe_api -X quit 2>/dev/null
            sleep 3
            screen -dmS stripe_api bash -c \"cd '$SCRIPT_DIR' && while true; do python3 stripe.py >> stripe.log 2>&1; sleep 5; done\"
            rm -f /tmp/stripe_maxretry_count
            sleep 10
        fi
    else
        rm -f /tmp/stripe_maxretry_count 2>/dev/null
    fi
done
"

echo -e "${GREEN}✅ All services started!${NC}"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}📁 Folder:${NC} $SCRIPT_DIR"
echo ""
echo -e "${GREEN}📺 Screens:${NC}"
echo -e "   ${YELLOW}rxpbot${NC}          — Telegram Bot (lifetime auto-restart)"
echo -e "   ${YELLOW}stripe_api${NC}      — Stripe API (port 9000, lifetime auto-restart)"
echo -e "   ${YELLOW}stripe_monitor${NC}  — Health monitor (60s)"
echo ""
echo -e "${GREEN}📋 Logs:${NC}"
echo -e "   $SCRIPT_DIR/bot.log"
echo -e "   $SCRIPT_DIR/stripe.log"
echo -e "   $SCRIPT_DIR/stripe_monitor.log"
echo ""
echo -e "${GREEN}🛑 Stop all:${NC}"
echo -e "   screen -S rxpbot -X quit; screen -S stripe_api -X quit; screen -S stripe_monitor -X quit"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"