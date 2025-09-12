#!/bin/bash

# Digital Wellbeing Tracker - Health Check Script
# Comprehensive system health check

set -e

echo "🏥 Digital Wellbeing Tracker Health Check"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check functions
check_ok() {
    echo -e "${GREEN}✅ $1${NC}"
}

check_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

check_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if port is open
check_port() {
    nc -z localhost $1 2>/dev/null
}

errors=0
warnings=0

echo
echo "🔍 System Dependencies"
echo "====================="

# Python check
if command_exists python3; then
    python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
    check_ok "Python3: $python_version"
else
    check_error "Python3 not found"
    ((errors++))
fi

# Node.js check
if command_exists node; then
    node_version=$(node --version 2>&1)
    check_ok "Node.js: $node_version"
else
    check_error "Node.js not found"
    ((errors++))
fi

# npm check
if command_exists npm; then
    npm_version=$(npm --version 2>&1)
    check_ok "npm: v$npm_version"
else
    check_error "npm not found"
    ((errors++))
fi

# uv check
if command_exists uv; then
    uv_version=$(uv --version 2>&1)
    check_ok "uv: $uv_version"
else
    check_warn "uv not found (optional, will use pip)"
    ((warnings++))
fi

# tmux check
if command_exists tmux; then
    tmux_version=$(tmux -V 2>&1)
    check_ok "tmux: $tmux_version"
else
    check_error "tmux not found (required for start.sh)"
    ((errors++))
fi

# Hyprland check
if [ -n "$HYPRLAND_INSTANCE_SIGNATURE" ]; then
    check_ok "Running on Hyprland"
elif command_exists hyprctl; then
    check_ok "Hyprland tools available"
else
    check_error "Hyprland not detected - collector will not work"
    ((errors++))
fi

echo
echo "📁 Project Structure"
echo "=================="

# Check directories
for dir in "data" "collector" "processor" "backend" "frontend" "scripts"; do
    if [ -d "$dir" ]; then
        check_ok "Directory: $dir/"
    else
        check_error "Missing directory: $dir/"
        ((errors++))
    fi
done

# Check key files
declare -a key_files=(
    "data/schema.sql"
    "data/app_categories.json"
    "collector/collector.py"
    "collector/requirements.txt"
    "processor/processor.py"
    "processor/requirements.txt"
    "backend/main.py"
    "backend/requirements.txt"
    "frontend/package.json"
    "frontend/src/App.tsx"
    "scripts/setup.sh"
    "scripts/start.sh"
    "scripts/stop.sh"
)

for file in "${key_files[@]}"; do
    if [ -f "$file" ]; then
        check_ok "File: $file"
    else
        check_error "Missing file: $file"
        ((errors++))
    fi
done

echo
echo "🐍 Python Environment"
echo "==================="

# Virtual environment check
if [ -d ".venv" ]; then
    check_ok "Virtual environment exists"
    
    if [ -f ".venv/bin/activate" ]; then
        check_ok "Activation script exists"
        
        # Check Python packages
        source .venv/bin/activate 2>/dev/null || true
        
        packages=("fastapi" "uvicorn" "pydantic" "psutil")
        for package in "${packages[@]}"; do
            if python -c "import $package" 2>/dev/null; then
                check_ok "Python package: $package"
            else
                check_error "Missing Python package: $package"
                ((errors++))
            fi
        done
    else
        check_error "Activation script missing"
        ((errors++))
    fi
else
    check_error "Virtual environment not found"
    check_info "Run ./scripts/setup.sh to create it"
    ((errors++))
fi

echo
echo "📦 Node.js Dependencies"
echo "====================="

if [ -d "frontend/node_modules" ]; then
    check_ok "Node modules installed"
    
    if [ -f "frontend/package-lock.json" ]; then
        check_ok "Package lock file exists"
    else
        check_warn "No package-lock.json (consider running npm install)"
        ((warnings++))
    fi
else
    check_error "Node modules not installed"
    check_info "Run 'npm install' in frontend directory"
    ((errors++))
fi

echo
echo "💾 Database Status"
echo "================"

if [ -f "data/wellbeing.db" ]; then
    check_ok "Database file exists"
    
    # Check if we can connect to SQLite
    if command_exists sqlite3; then
        table_count=$(sqlite3 data/wellbeing.db "SELECT count(name) FROM sqlite_master WHERE type='table';" 2>/dev/null || echo "0")
        if [ "$table_count" -gt 0 ]; then
            check_ok "Database has $table_count tables"
            
            # Check for recent events
            event_count=$(sqlite3 data/wellbeing.db "SELECT COUNT(*) FROM events WHERE DATE(timestamp) = DATE('now', 'localtime');" 2>/dev/null || echo "0")
            if [ "$event_count" -gt 0 ]; then
                check_ok "Today's events: $event_count"
            else
                check_warn "No events recorded today"
                ((warnings++))
            fi
        else
            check_error "Database has no tables"
            ((errors++))
        fi
    else
        check_warn "sqlite3 command not available for database inspection"
        ((warnings++))
    fi
else
    check_warn "Database file doesn't exist yet (will be created by collector)"
    ((warnings++))
fi

echo
echo "🌐 Service Status"
echo "==============="

# Check if services are running
if check_port 8847; then
    check_ok "Backend API is running (port 8847)"
    
    # Try to hit health endpoint
    if command_exists curl; then
        if curl -s http://localhost:8847/ >/dev/null 2>&1; then
            check_ok "Backend health check passed"
        else
            check_error "Backend not responding to requests"
            ((errors++))
        fi
    fi
else
    check_warn "Backend API not running (port 8847)"
    ((warnings++))
fi

if check_port 3847; then
    check_ok "Frontend is running (port 3847)"
else
    check_warn "Frontend not running (port 3847)"
    ((warnings++))
fi

# Check for tmux session
if tmux has-session -t wellbeing-tracker 2>/dev/null; then
    check_ok "Tmux session 'wellbeing-tracker' exists"
else
    check_info "Tmux session not found (services not started with start.sh)"
fi

echo
echo "📊 Summary"
echo "=========="

if [ $errors -eq 0 ] && [ $warnings -eq 0 ]; then
    check_ok "All checks passed! System is healthy."
    exit_code=0
elif [ $errors -eq 0 ]; then
    check_warn "$warnings warning(s) found. System should work but may have issues."
    exit_code=1
else
    check_error "$errors error(s) and $warnings warning(s) found. System needs attention."
    exit_code=2
fi

echo
echo "🛠️  Next Steps"
echo "============="

if [ $errors -gt 0 ]; then
    echo "1. Fix the errors listed above"
    echo "2. Run ./scripts/setup.sh if environment is not set up"
    echo "3. Run ./scripts/start.sh to start services"
elif [ $warnings -gt 0 ]; then
    echo "1. Address warnings if needed"
    echo "2. Run ./scripts/start.sh to start services if not running"
else
    echo "System is healthy! Services should be working properly."
fi

echo "4. Check http://localhost:3847 for the dashboard"
echo "5. Check http://localhost:8847/diagnostics/status for detailed diagnostics"

exit $exit_code
