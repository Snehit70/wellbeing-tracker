"""
Digital Wellbeing Tracker - Activity Collector
Tracks active window and application usage on Wayland/Hyprland
"""

import json
import sqlite3
import subprocess
import time
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class WindowInfo:
    """Data class for window information"""
    app_name: str
    window_title: str
    process_name: str
    website_url: Optional[str] = None


class HyprlandCollector:
    """Collects window activity data from Hyprland compositor"""
    
    def __init__(self, db_path: str = "data/wellbeing.db", interval: int = 5):
        self.db_path = Path(db_path)
        self.interval = interval
        self.running = True
        self.last_window_info = None
        
        # Setup logging
        log_dir = Path(__file__).parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / 'collector.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        
    def _execute_hyprctl(self, command: str) -> str:
        """Execute hyprctl command and return output"""
        try:
            result = subprocess.run(
                ['hyprctl', command],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                self.logger.error(f"hyprctl command failed: {result.stderr}")
                return ""
        except subprocess.TimeoutExpired:
            self.logger.error("hyprctl command timed out")
            return ""
        except FileNotFoundError:
            self.logger.error("hyprctl not found - are you running on Hyprland?")
            return ""
        except Exception as e:
            self.logger.error(f"Error executing hyprctl: {e}")
            return ""
            
    def _get_active_window_info(self) -> Optional[WindowInfo]:
        """Get information about the currently active window"""
        try:
            # Get active window info from Hyprland
            active_window_output = self._execute_hyprctl('activewindow')
            
            if not active_window_output:
                return None
                
            # Parse the output to extract window information
            lines = active_window_output.split('\n')
            window_info = {}
            
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    window_info[key.strip()] = value.strip()
            
            # Extract relevant information
            app_name = window_info.get('class', 'Unknown') or 'Unknown'
            window_title = window_info.get('title', 'Unknown')
            
            # Get process name if available
            process_name = app_name.lower()
            
            # Clean up app name (remove version numbers, etc.)
            app_name_clean = self._clean_app_name(app_name)

            # Extract website URL if the app is a browser
            website_url = None
            if app_name_clean in ['chrome', 'firefox']:
                website_url = self._extract_url_from_title(window_title)
            
            return WindowInfo(
                app_name=app_name_clean,
                window_title=window_title,
                process_name=process_name,
                website_url=website_url
            )
            
        except Exception as e:
            self.logger.error(f"Error getting active window info: {e}")
            return None
            
    def _clean_app_name(self, app_name: str) -> str:
        """Clean and normalize app names"""
        if not app_name or app_name == 'Unknown':
            return 'Unknown'
            
        # Convert to lowercase for consistency
        clean_name = app_name.lower()
        
        # Remove common suffixes and version numbers
        suffixes_to_remove = ['-bin', '-git', '-dev', '-nightly', '-stable']
        for suffix in suffixes_to_remove:
            if clean_name.endswith(suffix):
                clean_name = clean_name[:-len(suffix)]
                
        # Handle special cases
        if 'firefox' in clean_name:
            return 'firefox'
        elif 'chrome' in clean_name:
            return 'chrome'
        elif 'code' in clean_name or 'vscode' in clean_name:
            return 'code'
        elif 'terminal' in clean_name or 'konsole' in clean_name or 'alacritty' in clean_name:
            return 'terminal'
            
        return clean_name

    def _extract_url_from_title(self, title: str) -> Optional[str]:
        """Extracts a domain from the window title."""
        # This is a simple implementation. It could be improved with more sophisticated regex.
        # It tries to find something that looks like a domain name.
        import re
        # Look for patterns like 'github.com' or 'www.google.com'
        match = re.search(r'([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}', title)
        if match:
            # Let's try to clean it up a bit, removing common prefixes like 'www.'
            url = match.group(0)
            if url.startswith('www.'):
                return url[4:]
            return url
        
        # If no domain is found, we can try to extract it from the last part of the title if it's a browser
        parts = title.split(' - ')
        if len(parts) > 1:
            # E.g. "My Page - My Site" -> "My Site"
            # This is not a URL, but can be a good identifier.
            # For now, we only return what looks like a URL.
            pass

        return None
        
    def _init_database(self):
        """Initialize the database with schema"""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            conn = sqlite3.connect(str(self.db_path))
            
            # Read and execute schema
            schema_path = Path(__file__).parent.parent / "data" / "schema.sql"
            if schema_path.exists():
                with open(schema_path, 'r') as f:
                    schema = f.read()
                conn.executescript(schema)
            else:
                self.logger.error(f"Schema file not found: {schema_path}")
                
            conn.commit()
            conn.close()
            
            self.logger.info("Database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
            raise
            
    def _save_event(self, window_info: WindowInfo):
        """Save window activity event to database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO events (timestamp, device_type, app_name, window_title, process_name, duration_seconds, website_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                'desktop',
                window_info.app_name,
                window_info.window_title,
                window_info.process_name,
                self.interval,
                window_info.website_url
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.debug(f"Saved event: {window_info.app_name} - {window_info.window_title}")
            
        except Exception as e:
            self.logger.error(f"Error saving event to database: {e}")
            
    def run(self):
        """Main collection loop"""
        self.logger.info("Starting Digital Wellbeing Collector...")
        self.logger.info(f"Collection interval: {self.interval} seconds")
        
        # Initialize database
        self._init_database()
        
        while self.running:
            try:
                # Get current active window
                current_window = self._get_active_window_info()
                
                if current_window:
                    # Only log if the window changed or this is the first run
                    if (self.last_window_info is None or 
                        current_window.app_name != self.last_window_info.app_name or
                        current_window.window_title != self.last_window_info.window_title or
                        current_window.website_url != self.last_window_info.website_url):
                        
                        self.logger.info(f"Active: {current_window.app_name} - {current_window.window_title} - {current_window.website_url}")
                    
                    # Save the event
                    self._save_event(current_window)
                    self.last_window_info = current_window
                else:
                    self.logger.warning("Could not get active window information")
                    
                # Wait for next collection cycle
                time.sleep(self.interval)
                
            except KeyboardInterrupt:
                self.logger.info("Received keyboard interrupt, shutting down...")
                break
            except Exception as e:
                self.logger.error(f"Error in collection loop: {e}")
                time.sleep(self.interval)
                
        self.logger.info("Digital Wellbeing Collector stopped")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Digital Wellbeing Activity Collector")
    parser.add_argument("--db", default="data/wellbeing.db", help="Database file path")
    parser.add_argument("--interval", type=int, default=10, help="Collection interval in seconds")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        
    # Start collector
    collector = HyprlandCollector(db_path=args.db, interval=args.interval)
    collector.run()


if __name__ == "__main__":
    main()
