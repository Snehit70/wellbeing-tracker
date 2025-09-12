#!/bin/bash

# Digital Wellbeing Tracker - Stop All Services
# Stops all running components

echo "🛑 Stopping Digital Wellbeing Tracker services..."

SESSION_NAME="wellbeing-tracker"

# Kill tmux session if it exists
if tmux has-session -t $SESSION_NAME 2>/dev/null; then
    echo "📦 Killing tmux session: $SESSION_NAME"
    tmux kill-session -t $SESSION_NAME
    echo "✅ Tmux session stopped"
else
    echo "ℹ️  No tmux session found"
fi

# Kill any remaining processes
echo "🔍 Checking for remaining processes..."

# Kill collector processes (both venv and system python)
COLLECTOR_PIDS=$(pgrep -f "collector/collector.py\|\.venv.*collector\.py" || true)
if [ ! -z "$COLLECTOR_PIDS" ]; then
    echo "🔪 Killing collector processes: $COLLECTOR_PIDS"
    echo $COLLECTOR_PIDS | xargs kill -TERM
fi

# Kill processor processes (both venv and system python)
PROCESSOR_PIDS=$(pgrep -f "processor/processor.py\|\.venv.*processor\.py" || true)
if [ ! -z "$PROCESSOR_PIDS" ]; then
    echo "🔪 Killing processor processes: $PROCESSOR_PIDS"
    echo $PROCESSOR_PIDS | xargs kill -TERM
fi

# Kill backend processes on port 8847
BACKEND_PIDS=$(lsof -ti:8847 || true)
if [ ! -z "$BACKEND_PIDS" ]; then
    echo "🔪 Killing backend processes: $BACKEND_PIDS"
    echo $BACKEND_PIDS | xargs kill -TERM
fi

# Kill frontend processes on port 3847
FRONTEND_PIDS=$(lsof -ti:3847 || true)
if [ ! -z "$FRONTEND_PIDS" ]; then
    echo "🔪 Killing frontend processes: $FRONTEND_PIDS"
    echo $FRONTEND_PIDS | xargs kill -TERM
fi

echo "✅ All services stopped"
