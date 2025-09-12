"""
Digital Wellbeing Tracker - Data Processor
Processes raw activity data into hourly and daily aggregations
"""

import json
import sqlite3
import time
import logging
import signal
import sys
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ProcessorConfig:
    """Configuration for the data processor"""
    db_path: str
    categories_path: str
    process_interval: int = 60  # 1 minute
    batch_size: int = 1000


class CategoryManager:
    """Manages app-to-category mappings"""
    
    def __init__(self, categories_path: str):
        self.categories_path = Path(categories_path)
        self.categories = {}
        self.app_mappings = {}
        self.load_categories()
        
    def load_categories(self):
        """Load category mappings from JSON file"""
        try:
            if self.categories_path.exists():
                with open(self.categories_path, 'r') as f:
                    data = json.load(f)
                    self.categories = data.get('categories', {})
                    
                    # Build app name to category mapping
                    self.app_mappings = {}
                    for category, info in self.categories.items():
                        for app in info.get('apps', []):
                            self.app_mappings[app.lower()] = category
                            
                logging.info(f"Loaded {len(self.app_mappings)} app mappings across {len(self.categories)} categories")
            else:
                logging.warning(f"Categories file not found: {self.categories_path}")
                
        except Exception as e:
            logging.error(f"Error loading categories: {e}")
            
    def get_category(self, app_name: str) -> str:
        """Get category for an app name"""
        if not app_name:
            return "Other"
            
        app_lower = app_name.lower()
        
        # Direct match
        if app_lower in self.app_mappings:
            return self.app_mappings[app_lower]
            
        # Partial match (more robust)
        for app_pattern, category in self.app_mappings.items():
            if app_pattern in app_lower:
                return category
                
        return "Other"
        
    def update_category_mapping(self, app_name: str, category: str):
        """Update category mapping for an app"""
        self.app_mappings[app_name.lower()] = category
        
        # Also update the JSON file
        if category in self.categories:
            if app_name.lower() not in self.categories[category]['apps']:
                self.categories[category]['apps'].append(app_name.lower())
                self.save_categories()
                
    def save_categories(self):
        """Save categories to JSON file"""
        try:
            data = {
                'categories': self.categories,
                'rules': {
                    'default_category': 'Other',
                    'case_sensitive': False,
                    'match_strategy': 'partial'
                },
                'updated_at': datetime.now().isoformat()
            }
            
            with open(self.categories_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logging.error(f"Error saving categories: {e}")


class DataProcessor:
    """Processes raw activity data into aggregated statistics"""
    
    def __init__(self, config: ProcessorConfig):
        self.config = config
        self.running = True
        self.category_manager = CategoryManager(config.categories_path)
        
        # Setup logging
        log_dir = Path(__file__).parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / 'processor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        
    def _get_database_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        return sqlite3.connect(str(self.config.db_path))
        
    def _process_hourly_aggregations(self):
        """Process raw events into hourly aggregations"""
        try:
            conn = self._get_database_connection()
            cursor = conn.cursor()

            # Find the latest processed timestamp to minimize reprocessing
            cursor.execute("SELECT MAX(date || ' ' || printf('%02d', hour) || ':59:59') FROM hourly_usage")
            result = cursor.fetchone()
            # Go back 2 hours to be safe and recapture any late-arriving events
            last_processed_ts = result[0] if result[0] else '1970-01-01 00:00:00'
            start_processing_ts = (datetime.fromisoformat(last_processed_ts) - timedelta(hours=2)).isoformat()

            self.logger.debug(f"Processing hourly data since: {start_processing_ts}")

            # Get unprocessed events
            cursor.execute("""
                SELECT
                    STRFTIME('%Y-%m-%d', timestamp) as event_date,
                    CAST(STRFTIME('%H', timestamp) AS INTEGER) as event_hour,
                    device_type,
                    app_name,
                    website_url,
                    COUNT(*) as event_count,
                    SUM(duration_seconds) as total_seconds
                FROM events
                WHERE timestamp > ?
                GROUP BY event_date, event_hour, device_type, app_name, website_url
                ORDER BY event_date, event_hour
            """, (start_processing_ts,))

            hourly_data = cursor.fetchall()

            if not hourly_data:
                self.logger.debug("No new hourly data to process")
                conn.close()
                return

            # Delete old data for the hours we are about to update
            hours_to_update = set((row[0], row[1]) for row in hourly_data)
            for event_date, event_hour in hours_to_update:
                cursor.execute("DELETE FROM hourly_usage WHERE date = ? AND hour = ?", (event_date, event_hour))

            # Process each hourly group
            for row in hourly_data:
                event_date, event_hour, device_type, app_name, website_url, event_count, total_seconds = row
                
                category = self.category_manager.get_category(app_name)
                
                cursor.execute("""
                    INSERT INTO hourly_usage
                    (date, hour, device_type, app_name, website_url, category, total_seconds, event_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (event_date, event_hour, device_type, app_name, website_url, category, total_seconds, event_count))

            conn.commit()
            conn.close()

            self.logger.info(f"Processed {len(hourly_data)} hourly aggregations for {len(hours_to_update)} hour-slots.")

        except Exception as e:
            self.logger.error(f"Error processing hourly aggregations: {e}", exc_info=True)
            
    def _process_daily_aggregations(self):
        """Process hourly data into daily aggregations"""
        try:
            conn = self._get_database_connection()
            cursor = conn.cursor()

            # Find the latest processed date, then re-process the last 2 days for accuracy
            cursor.execute("SELECT MAX(date) FROM daily_usage")
            result = cursor.fetchone()
            last_processed_date = result[0] if result[0] else '1970-01-01'
            start_processing_date = (datetime.strptime(last_processed_date, "%Y-%m-%d").date() - timedelta(days=1)).isoformat()

            self.logger.debug(f"Processing daily data since: {start_processing_date}")

            # Get all hourly data to be re-processed
            cursor.execute("""
                SELECT
                    date,
                    device_type,
                    app_name,
                    website_url,
                    category,
                    SUM(total_seconds) as total_seconds,
                    SUM(event_count) as event_count
                FROM hourly_usage
                WHERE date >= ?
                GROUP BY date, device_type, app_name, website_url, category
                ORDER BY date
            """, (start_processing_date,))

            daily_data = cursor.fetchall()

            if not daily_data:
                self.logger.debug("No new daily data to process")
                conn.close()
                return

            # Delete old data for the dates we are about to update
            dates_to_update = sorted(list(set(row[0] for row in daily_data)))
            for event_date in dates_to_update:
                cursor.execute("DELETE FROM daily_usage WHERE date = ?", (event_date,))
                cursor.execute("DELETE FROM daily_category_usage WHERE date = ?", (event_date,))

            # Insert new daily usage data
            for row in daily_data:
                event_date, device_type, app_name, website_url, category, total_seconds, event_count = row
                cursor.execute("""
                    INSERT INTO daily_usage
                    (date, device_type, app_name, website_url, category, total_seconds, event_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (event_date, device_type, app_name, website_url, category, total_seconds, event_count))

            # Now, re-calculate daily category usage from the newly inserted daily_usage data
            cursor.execute("""
                SELECT
                    date,
                    device_type,
                    category,
                    SUM(total_seconds) as total_seconds
                FROM daily_usage
                WHERE date >= ?
                GROUP BY date, device_type, category
            """, (start_processing_date,))
            
            category_data = cursor.fetchall()

            for row in category_data:
                event_date, device_type, category, total_seconds = row
                cursor.execute("""
                    INSERT INTO daily_category_usage
                    (date, device_type, category, total_seconds)
                    VALUES (?, ?, ?, ?)
                """, (event_date, device_type, category, total_seconds))

            conn.commit()
            conn.close()

            self.logger.info(f"Processed {len(daily_data)} daily aggregations and {len(category_data)} category aggregations for {len(dates_to_update)} day(s).")

        except Exception as e:
            self.logger.error(f"Error processing daily aggregations: {e}", exc_info=True)
            
    def _update_app_categories_table(self):
        """Update the app_categories table from the JSON mappings"""
        try:
            conn = self._get_database_connection()
            cursor = conn.cursor()
            
            # Clear existing mappings
            cursor.execute("DELETE FROM app_categories")
            
            # Insert current mappings
            for app_name, category in self.category_manager.app_mappings.items():
                cursor.execute("""
                    INSERT INTO app_categories (app_name, category)
                    VALUES (?, ?)
                """, (app_name, category))
                
            conn.commit()
            conn.close()
            
            self.logger.debug(f"Updated {len(self.category_manager.app_mappings)} app category mappings in database")
            
        except Exception as e:
            self.logger.error(f"Error updating app categories table: {e}")
            
    def process_all(self):
        """Run all processing steps"""
        self.logger.info("Starting data processing cycle...")
        
        # Reload categories in case they were updated
        self.category_manager.load_categories()
        
        # Update app categories table
        self._update_app_categories_table()
        
        # Process aggregations
        self._process_hourly_aggregations()
        self._process_daily_aggregations()
        
        self.logger.info("Data processing cycle completed")
        
    def run_continuous(self):
        """Run processor continuously"""
        self.logger.info("Starting Digital Wellbeing Data Processor...")
        self.logger.info(f"Processing interval: {self.config.process_interval} seconds")
        
        while self.running:
            try:
                self.process_all()
                
                # Wait for next processing cycle
                time.sleep(self.config.process_interval)
                
            except KeyboardInterrupt:
                self.logger.info("Received keyboard interrupt, shutting down...")
                break
            except Exception as e:
                self.logger.error(f"Error in processing loop: {e}")
                time.sleep(self.config.process_interval)
                
        self.logger.info("Digital Wellbeing Data Processor stopped")
        
    def run_once(self):
        """Run processor once and exit"""
        self.logger.info("Running single data processing cycle...")
        self.process_all()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Digital Wellbeing Data Processor")
    parser.add_argument("--db", default="data/wellbeing.db", help="Database file path")
    parser.add_argument("--categories", default="data/app_categories.json", help="Categories JSON file path")
    parser.add_argument("--interval", type=int, default=300, help="Processing interval in seconds")
    parser.add_argument("--once", action="store_true", help="Run once and exit (useful for cron)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        
    # Create config
    config = ProcessorConfig(
        db_path=args.db,
        categories_path=args.categories,
        process_interval=args.interval
    )
    
    # Start processor
    processor = DataProcessor(config)
    
    if args.once:
        processor.run_once()
    else:
        processor.run_continuous()


if __name__ == "__main__":
    main()
