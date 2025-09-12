#!/bin/bash

# Digital Wellbeing Tracker - Stop All Services
# Stops all running components. This script is idempotent.

echo "🛑 Stopping Digital Wellbeing Tracker services..."

SESSION_NAME="wellbeing-tracker"

# Kill tmux session if it exists
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "📦 Killing tmux session: $SESSION_NAME"
    tmux kill-session -t "$SESSION_NAME"
    echo "✅ Tmux session stopped"
else
    echo "ℹ️  No active tmux session found."
fi

# Function to kill processes by pattern or port
kill_process() {
    local name="$1"
    local type="$2"
    local pattern="$3"
    local pids

    if [ "$type" == "pattern" ]; then
        pids=$(pgrep -f "$pattern" 2>/dev/null)
    elif [ "$type" == "port" ]; then
        pids=$(lsof -ti :"$pattern" 2>/dev/null)
    fi

    if [ -n "$pids" ]; then
        echo "🔪 Killing $name processes (PIDs: $pids)..."
        kill -9 $pids
        echo "✅ $name stopped."
    else
        echo "ℹ️  No running $name processes found."
    fi
}

echo "🔍 Checking for remaining processes..."

# Kill individual services
kill_process "Collector" "pattern" "collector/collector.py"
kill_process "Processor" "pattern" "processor/processor.py"
kill_process "Backend" "port" "8847"
kill_process "Frontend" "port" "3847"

echo ""
echo "🎉 All services have been stopped."
