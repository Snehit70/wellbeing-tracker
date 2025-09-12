#!/bin/bash

# Digital Wellbeing Tracker - Setup Script
# This script initializes the database and sets up the environment

set -e

echo "🔧 Setting up Digital Wellbeing Tracker..."

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data
mkdir -p logs

# Initialize database
echo "🗄️  Initializing database..."
if [ -f "data/wellbeing.db" ]; then
    echo "⚠️  Database already exists. Creating backup..."
    cp data/wellbeing.db data/wellbeing.db.backup.$(date +%Y%m%d_%H%M%S)
fi

# Run schema
sqlite3 data/wellbeing.db < data/schema.sql
echo "✅ Database schema created"

# Setup Python virtual environment and install dependencies
echo "📦 Setting up Python virtual environment..."

# Check if uv is available
if command -v uv &> /dev/null; then
    echo "Using uv for virtual environment management..."
    
    # Create virtual environment with uv
    if [ ! -d ".venv" ]; then
        echo "Creating virtual environment with uv..."
        uv venv .venv
    fi
    
    # Activate virtual environment
    source .venv/bin/activate
    
    # Install dependencies with uv
    echo "Installing collector dependencies..."
    uv pip install -r collector/requirements.txt
    
    echo "Installing processor dependencies..."
    uv pip install -r processor/requirements.txt
    
    echo "Installing backend dependencies..."
    uv pip install -r backend/requirements.txt
    
    echo "✅ Python dependencies installed with uv"
    echo "🔧 To activate venv later: source .venv/bin/activate"
    
else
    echo "uv not found, falling back to pip..."
    
    # Create virtual environment with standard venv
    if [ ! -d ".venv" ]; then
        echo "Creating virtual environment with python3 -m venv..."
        python3 -m venv .venv
    fi
    
    # Activate virtual environment
    source .venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install dependencies
    echo "Installing collector dependencies..."
    pip install -r collector/requirements.txt
    
    echo "Installing processor dependencies..."
    pip install -r processor/requirements.txt
    
    echo "Installing backend dependencies..."
    pip install -r backend/requirements.txt
    
    echo "✅ Python dependencies installed with pip"
    echo "🔧 To activate venv later: source .venv/bin/activate"
fi

# Install Node.js dependencies for frontend
echo "📦 Installing Node.js dependencies..."
cd frontend
npm install
cd ..
echo "✅ Node.js dependencies installed"

# Create systemd service files
echo "🔧 Creating systemd service files..."

# Collector service
cat > wellbeing-collector.service << EOF
[Unit]
Description=Digital Wellbeing Tracker - Data Collector
After=graphical-session.target
Wants=graphical-session.target

[Service]
Type=simple
User=$USER
Environment=DISPLAY=:0
Environment=PATH=$(pwd)/.venv/bin:\$PATH
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/.venv/bin/python $(pwd)/collector/collector.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=graphical-session.target
EOF

# Processor service
cat > wellbeing-processor.service << EOF
[Unit]
Description=Digital Wellbeing Tracker - Data Processor
After=multi-user.target

[Service]
Type=simple
User=$USER
Environment=PATH=$(pwd)/.venv/bin:\$PATH
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/.venv/bin/python $(pwd)/processor/processor.py
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Backend service
cat > wellbeing-backend.service << EOF
[Unit]
Description=Digital Wellbeing Tracker - API Backend
After=network.target

[Service]
Type=simple
User=$USER
Environment=PATH=$(pwd)/.venv/bin:\$PATH
WorkingDirectory=$(pwd)/backend
ExecStart=$(pwd)/.venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Systemd service files created"

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Install systemd services (optional):"
echo "   sudo cp wellbeing-*.service /etc/systemd/system/"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl enable wellbeing-collector wellbeing-processor wellbeing-backend"
echo ""
echo "2. Start services manually:"
echo "   # Activate virtual environment first"
echo "   source .venv/bin/activate"
echo ""
echo "   # Terminal 1: Start collector"
echo "   python collector/collector.py"
echo ""
echo "   # Terminal 2: Start processor" 
echo "   python processor/processor.py"
echo ""
echo "   # Terminal 3: Start backend"
echo "   cd backend && python main.py"
echo ""
echo "   # Terminal 4: Start frontend"
echo "   cd frontend && npm run dev"
echo ""
echo "3. Access the dashboard at: http://localhost:3847"
echo ""
echo "📊 The tracker will start collecting data immediately!"
echo "⏱️  Wait a few minutes for initial data to appear."
