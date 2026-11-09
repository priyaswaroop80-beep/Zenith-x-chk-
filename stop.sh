#!/bin/bash
# Stop all RXP services
echo "🛑 Stopping all services..."

screen -S rxpbot          -X quit 2>/dev/null
screen -S stripe_api      -X quit 2>/dev/null
screen -S stripe_monitor  -X quit 2>/dev/null

pkill -f "python3 bot.py"     2>/dev/null
pkill -f "python3 stripe.py"  2>/dev/null
pkill -f "uvicorn"            2>/dev/null

echo "✅ All stopped"
