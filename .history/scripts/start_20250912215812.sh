#!/bin/bash

# Digital Wellbeing Tracker - Start All Services
# Convenience script to start all components. This script is idempotent.

set -e

echo "🚀 Starting Digital Wellbeing Tracker..."

# Make this script idempotent by stopping existing services first
echo "Ensuring all services are stopped before starting..."
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
"$SCRIPT_DIR/stop.sh"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check dependencies
echo "🔍 Checking dependencies..."

if ! command_exists python3; then
    echo "❌ Python3 not found. Please install Python 3.8+"
    exit 1
fi

if ! command_exists node; then
    echo "❌ Node.js not found. Please install Node.js 16+"
    exit 1
fi

if ! command_exists npm; then
    echo "❌ npm not found. Please install npm"
    exit 1
fi

# Check for virtual environment
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Please run ./scripts/setup.sh first"
    exit 1
fi

echo "🐍 Activating Python virtual environment..."
source .venv/bin/activate

# Verify Python dependencies are installed
echo "🔍 Checking Python dependencies..."
missing_deps=()

# Check for FastAPI
if ! python -c "import fastapi" 2>/dev/null; then
    missing_deps+=("backend")
fi

# Check for psutil
if ! python -c "import psutil" 2>/dev/null; then
    missing_deps+=("collector")
fi

# Install missing dependencies
if [ ${#missing_deps[@]} -gt 0 ]; then
    echo "📦 Missing dependencies detected. Installing..."
    
    if command -v uv &> /dev/null; then
        echo "Using uv for package installation..."
        for dep in "${missing_deps[@]}"; do
            echo "Installing $dep dependencies..."
            uv pip install -r $dep/requirements.txt
        done
    else
        echo "Using pip for package installation..."
        for dep in "${missing_deps[@]}"; do
            echo "Installing $dep dependencies..."
            pip install -r $dep/requirements.txt
        done
    fi
    echo "✅ Dependencies installed successfully"
else
    echo "✅ All Python dependencies are installed"
fi

# Check Node.js dependencies
echo "🔍 Checking Node.js dependencies..."
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing Node.js dependencies..."
    cd frontend
    npm install
    cd ..
    echo "✅ Node.js dependencies installed"
else
    echo "✅ Node.js dependencies are installed"
fi

# Check if we're on Hyprland
if [ "$XDG_CURRENT_DESKTOP" != "Hyprland" ] && [ -z "$HYPRLAND_INSTANCE_SIGNATURE" ]; then
    echo "⚠️  Warning: Not running on Hyprland. Collector may not work properly."
fi

echo "✅ All dependency checks passed"

# Create tmux session for running all services
SESSION_NAME="wellbeing-tracker"

echo "📦 Creating tmux session: $SESSION_NAME"

# Create new session with first window
if ! tmux new-session -d -s $SESSION_NAME -n 'collector'; then
    echo "❌ Failed to create tmux session"
    exit 1
fi

echo "🚀 Starting individual services..."

# Window 1: Collector
echo "  📊 Starting collector service..."
tmux send-keys -t $SESSION_NAME:collector 'cd '"$(pwd)"' && echo "=== COLLECTOR STARTING ===" && source .venv/bin/activate && python collector/collector.py' C-m

# Window 2: Processor  
echo "  ⚙️  Starting processor service..."
if ! tmux new-window -t $SESSION_NAME -n 'processor'; then
    echo "❌ Failed to create processor window"
    exit 1
fi
tmux send-keys -t $SESSION_NAME:processor 'cd '"$(pwd)"' && echo "=== PROCESSOR STARTING ===" && source .venv/bin/activate && python processor/processor.py' C-m

# Window 3: Backend
echo "  🌐 Starting backend API service..."
if ! tmux new-window -t $SESSION_NAME -n 'backend'; then
    echo "❌ Failed to create backend window"
    exit 1
fi
tmux send-keys -t $SESSION_NAME:backend 'cd '"$(pwd)"'/backend && echo "=== BACKEND API STARTING ===" && source ../.venv/bin/activate && python main.py' C-m

# Window 4: Frontend
echo "  💻 Starting frontend service..."
if ! tmux new-window -t $SESSION_NAME -n 'frontend'; then
    echo "❌ Failed to create frontend window"
    exit 1
fi
tmux send-keys -t $SESSION_NAME:frontend 'cd '"$(pwd)"'/frontend && echo "=== FRONTEND STARTING ===" && npm run dev' C-m

# Go back to first window
tmux select-window -t $SESSION_NAME:collector

echo ""
echo "🚀 Services starting in background..."

# Wait for services to initialize
echo "⏳ Waiting for services to initialize..."
sleep 5

# Function to check if port is open
check_port() {
    nc -z localhost $1 2>/dev/null
}

# Check service status
echo "🔍 Checking service status..."

backend_ready=false
frontend_ready=false

# Check backend (with retry)
for i in {1..10}; do
    if check_port 8847; then
        echo "✅ Backend API is running (http://localhost:8847)"
        backend_ready=true
        break
    fi
    if [ $i -eq 10 ]; then
        echo "❌ Backend API failed to start (port 8847)"
        echo "   Check tmux window 'backend': tmux attach -t $SESSION_NAME"
    else
        echo "⏳ Backend starting... (attempt $i/10)"
        sleep 2
    fi
done

# Check frontend (with retry)
for i in {1..10}; do
    if check_port 3847; then
        echo "✅ Frontend is running (http://localhost:3847)"
        frontend_ready=true
        break
    fi
    if [ $i -eq 10 ]; then
        echo "❌ Frontend failed to start (port 3847)"
        echo "   Check tmux window 'frontend': tmux attach -t $SESSION_NAME"
    else
        echo "⏳ Frontend starting... (attempt $i/10)"
        sleep 2
    fi
done

echo ""
if [ "$backend_ready" = true ] && [ "$frontend_ready" = true ]; then
    echo "🎉 All services are running successfully!"
elif [ "$backend_ready" = true ] || [ "$frontend_ready" = true ]; then
    echo "⚠️  Some services are running, check the failed ones above"
else
    echo "❌ Services failed to start. Check tmux session for errors."
fi

echo ""
echo "📋 Access:"
echo "   • Dashboard: http://localhost:3847"
echo "   • API: http://localhost:8847"
echo "   • API Docs: http://localhost:8847/docs"
echo ""
echo "🔧 Tmux commands:"
echo "   • Attach to session: tmux attach -t $SESSION_NAME"
echo "   • List windows: Ctrl+b, w"
echo "   • Switch windows: Ctrl+b, [0-3]"
echo "   • Kill session: tmux kill-session -t $SESSION_NAME"
echo ""
echo "📊 Data collection will begin immediately!"
echo "⏱️  Allow 5-10 minutes for data to appear in dashboard."

# Optionally attach to the session
read -p "🤔 Attach to tmux session now? [y/N]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    tmux attach -t $SESSION_NAME
fi
