# Digital Wellbeing Tracker

A comprehensive personal digital wellbeing tracker for Linux desktop environments, specifically optimized for Wayland/Hyprland. Track your screen time, analyze usage patterns, and gain insights into your digital habits.

## Features

- **🔍 Real-time Activity Tracking**: Monitors active window and application usage every 10 seconds
- **📊 Rich Analytics**: Daily, weekly, and hourly usage breakdowns with interactive charts  
- **🏷️ Smart Categorization**: Organize apps into meaningful categories (Work, Entertainment, etc.)
- **⚡ Live Dashboard**: Real-time React frontend with beautiful visualizations
- **🔒 Privacy First**: All data stored locally - no cloud services required
- **🚀 Easy Setup**: Automated scripts for quick deployment
- **📱 Future Ready**: Database schema designed for smartphone integration

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Collector     │    │    Processor     │    │   Backend API   │
│  (Python)       │    │   (Python)       │    │   (FastAPI)     │
│                 │    │                  │    │                 │
│ Tracks active   │───▶│ Aggregates raw   │───▶│ REST endpoints  │
│ window/app      │    │ data into        │    │ for frontend    │
│ every 10s       │    │ hourly & daily   │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     SQLite Database                             │
│  • Raw events (timestamp, app, window title, duration)         │
│  • Hourly aggregations (app usage per hour)                    │  
│  • Daily aggregations (app usage per day)                      │
│  • Category mappings (app → category relationships)            │
└─────────────────────────────────────────────────────────────────┘
                               ▲
                               │
                ┌─────────────────────────┐
                │     Frontend            │
                │   (React + Vite)        │
                │                         │
                │ • Overview Dashboard    │
                │ • Trends & Analytics    │
                │ • Category Management   │
                │ • Settings & Config     │
                └─────────────────────────┘
```

## Quick Start

### Prerequisites

- **Linux with Wayland/Hyprland** (other compositors may work but are not tested)
- **Python 3.8+** with pip
- **Node.js 16+** with npm
- **SQLite3** (usually pre-installed)
- **tmux** (for the convenience start script)
- **uv** (optional, for faster Python package management - will fallback to venv if not available)

### Installation

1. **Clone and setup:**
   ```bash
   git clone <repository-url>
   cd wellbeing-tracker
   chmod +x scripts/*.sh
   ./scripts/setup.sh
   ```

2. **Start all services:**
   ```bash
   ./scripts/start.sh
   ```

3. **Access the dashboard:**
   Open http://localhost:3847 in your browser

### Manual Setup (Alternative)

If you prefer to run components individually:

```bash
# First, activate the virtual environment
source .venv/bin/activate

# Terminal 1: Start collector
python collector/collector.py

# Terminal 2: Start processor  
python processor/processor.py

# Terminal 3: Start backend
cd backend && python main.py

# Terminal 4: Start frontend
cd frontend && npm run dev
```

## Usage

### Dashboard Overview

- **📈 Overview Page**: Current day statistics, screen time breakdown, top apps
- **📊 Trends Page**: Weekly trends, hourly activity patterns, time series charts
- **🏷️ Categories Page**: Manage app categorizations, add/remove apps from categories
- **⚙️ Settings Page**: System configuration, database info, service status

### Key Metrics

- **Total Screen Time**: Cumulative active time per day/week
- **Category Breakdown**: Time distribution across Work, Entertainment, Communication, etc.
- **App Rankings**: Most used applications with usage percentages
- **Hourly Patterns**: Activity heatmaps showing productivity cycles
- **Weekly Trends**: Usage patterns and habit formation insights

### Customizing Categories

The system includes predefined categories, but you can customize them:

1. **Via Web Interface**: Use the Categories page to add/remove apps
2. **Via JSON File**: Edit `data/app_categories.json` directly
3. **Via API**: Use REST endpoints to programmatically update mappings

## API Endpoints

The FastAPI backend provides comprehensive REST endpoints:

### Usage Data
- `GET /usage/daily?date=YYYY-MM-DD` - Daily usage statistics
- `GET /usage/weekly?start=YYYY-MM-DD` - Weekly usage data  
- `GET /usage/hourly?date=YYYY-MM-DD` - Hourly breakdown
- `GET /apps/top?limit=N&days=N` - Top N most used apps

### Configuration  
- `GET /categories` - List all categories and app mappings
- `POST /categories/{category}/apps` - Add app to category
- `DELETE /categories/{category}/apps/{app}` - Remove app from category

### Analytics
- `GET /stats/summary?days=N` - Summary statistics for N days

Full API documentation available at: http://localhost:8847/docs

## Configuration

### Collector Settings

Edit `collector/collector.py` to modify:
- **Collection interval** (default: 10 seconds)
- **Database path** (default: `data/wellbeing.db`)
- **Logging level and output**

### Processor Settings

Edit `processor/processor.py` to modify:
- **Processing interval** (default: 5 minutes)  
- **Batch size** for database operations
- **Aggregation rules**

### Port Configuration

- **Backend API**: Port 8847 (configurable in `backend/main.py`)
- **Frontend**: Port 3847 (configurable in `frontend/vite.config.ts`)

## Data Storage

### Database Schema

```sql
-- Raw activity events
events (id, timestamp, device_type, app_name, window_title, process_name, duration_seconds)

-- Aggregated data  
hourly_usage (date, hour, device_type, app_name, category, total_seconds, event_count)
daily_usage (date, device_type, app_name, category, total_seconds, event_count)
daily_category_usage (date, device_type, category, total_seconds)

-- Configuration
app_categories (app_name, category, updated_at)
```

### Data Files

- **`data/wellbeing.db`** - Main SQLite database
- **`data/app_categories.json`** - Category mappings and configuration
- **`collector/collector.log`** - Collector service logs
- **`processor/processor.log`** - Processor service logs

## System Integration

### Systemd Services (Optional)

For automatic startup, install as systemd services:

```bash
sudo cp wellbeing-*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable wellbeing-collector wellbeing-processor wellbeing-backend
sudo systemctl start wellbeing-collector wellbeing-processor wellbeing-backend
```

### Cron Alternative

Run the processor via cron instead of as a service:

```bash
# Add to crontab for processing every 5 minutes
*/5 * * * * cd /path/to/wellbeing-tracker && python3 processor/processor.py --once
```

## Development

### Project Structure

```
wellbeing-tracker/
├── collector/          # Data collection service
│   ├── collector.py    # Main collector script
│   └── requirements.txt
├── processor/          # Data processing service  
│   ├── processor.py    # Aggregation and categorization
│   └── requirements.txt
├── backend/            # FastAPI REST API
│   ├── main.py         # API server
│   └── requirements.txt
├── frontend/           # React dashboard
│   ├── src/            # React components and pages
│   ├── package.json    # Node.js dependencies
│   └── vite.config.ts  # Build configuration
├── data/               # Database and configuration
│   ├── schema.sql      # Database schema
│   └── app_categories.json # Category mappings
└── scripts/            # Setup and utility scripts
    ├── setup.sh        # Initial setup
    ├── start.sh        # Start all services
    └── stop.sh         # Stop all services
```

### Adding New Features

1. **New Metrics**: Extend database schema and update processor aggregations
2. **New Visualizations**: Add React components using Recharts library  
3. **New Platforms**: Implement platform-specific window detection in collector
4. **Mobile Integration**: Leverage existing device_type field in database schema

### Technology Stack

- **Backend**: Python, FastAPI, SQLite, Pydantic
- **Frontend**: React, TypeScript, Vite, TailwindCSS, Recharts
- **Data Collection**: Hyprland/Wayland APIs, subprocess calls
- **Data Processing**: Pandas-style aggregations, JSON configuration
- **Deployment**: Systemd services, tmux sessions, shell scripts

## Privacy & Security

- **🔒 Local Storage**: All data remains on your device
- **🚫 No Telemetry**: No external network requests or tracking
- **👤 User Control**: Full control over data collection and retention
- **🛡️ Minimal Permissions**: Only requires access to active window information
- **📊 Transparent**: Open source code for full transparency

## Troubleshooting

### Common Issues

**Collector not detecting windows:**
- Ensure you're running Hyprland/Wayland
- Check that `hyprctl` command is available
- Verify collector has proper permissions

**No data in dashboard:**  
- Wait 5-10 minutes after starting for data to accumulate
- Check that collector and processor services are running
- Verify database file exists: `data/wellbeing.db`

**API connection errors:**
- Confirm backend is running on port 8847
- Check for port conflicts with other services
- Verify firewall settings if accessing remotely

**Frontend build errors:**
- Ensure Node.js 16+ is installed  
- Run `npm install` in frontend directory
- Check for TypeScript compilation errors

### Log Files

- **Collector**: `collector/collector.log`
- **Processor**: `processor/processor.log`  
- **Backend**: Console output or configure logging
- **Frontend**: Browser developer console

### Support

For issues, feature requests, or contributions:
1. Check the troubleshooting section above
2. Review log files for error details
3. Open an issue with system information and error logs

## Future Enhancements

- **📱 Mobile Integration**: Android/iOS companion apps
- **☁️ Backup & Sync**: Optional cloud synchronization  
- **🎯 Goal Setting**: Daily/weekly screen time goals
- **🔔 Smart Notifications**: Usage alerts and break reminders
- **📈 Advanced Analytics**: Machine learning insights and predictions
- **🔌 Integrations**: Calendar apps, task managers, and productivity tools
- **🎨 Themes**: Customizable dashboard themes and layouts

---

**Digital Wellbeing Tracker** - Take control of your digital habits with comprehensive, privacy-focused activity tracking.
