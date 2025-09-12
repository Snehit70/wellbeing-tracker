-- Digital Wellbeing Tracker Database Schema
-- Designed for extensibility to include mobile data in the future

-- Raw activity events table
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    device_type TEXT NOT NULL DEFAULT 'desktop', -- 'desktop' or 'mobile' for future extension
    app_name TEXT NOT NULL,
    window_title TEXT,
    website_url TEXT, -- To store the URL for browser activity
    website_title TEXT, -- To store a user-friendly name for the website
    process_name TEXT,
    duration_seconds INTEGER NOT NULL DEFAULT 10,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Hourly aggregated data
CREATE TABLE IF NOT EXISTS hourly_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    hour INTEGER NOT NULL, -- 0-23
    device_type TEXT NOT NULL DEFAULT 'desktop',
    app_name TEXT NOT NULL,
    website_url TEXT,
    category TEXT,
    total_seconds INTEGER NOT NULL DEFAULT 0,
    event_count INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, hour, device_type, app_name, website_url)
);

-- Daily aggregated data
CREATE TABLE IF NOT EXISTS daily_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    device_type TEXT NOT NULL DEFAULT 'desktop',
    app_name TEXT NOT NULL,
    website_url TEXT,
    category TEXT,
    total_seconds INTEGER NOT NULL DEFAULT 0,
    event_count INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, device_type, app_name, website_url)
);

-- Category-wise daily aggregations
CREATE TABLE IF NOT EXISTS daily_category_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    device_type TEXT NOT NULL DEFAULT 'desktop',
    category TEXT NOT NULL,
    total_seconds INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, device_type, category)
);

-- App category mappings (also stored as JSON file for easy editing)
CREATE TABLE IF NOT EXISTS app_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_app_name ON events(app_name);
CREATE INDEX IF NOT EXISTS idx_events_device_type ON events(device_type);

CREATE INDEX IF NOT EXISTS idx_hourly_date_hour ON hourly_usage(date, hour);
CREATE INDEX IF NOT EXISTS idx_hourly_app ON hourly_usage(app_name);
CREATE INDEX IF NOT EXISTS idx_hourly_category ON hourly_usage(category);

CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_usage(date);
CREATE INDEX IF NOT EXISTS idx_daily_app ON daily_usage(app_name);
CREATE INDEX IF NOT EXISTS idx_daily_category ON daily_usage(category);

CREATE INDEX IF NOT EXISTS idx_daily_cat_date ON daily_category_usage(date);
CREATE INDEX IF NOT EXISTS idx_daily_cat_category ON daily_category_usage(category);
