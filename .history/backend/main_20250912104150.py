"""
Digital Wellbeing Tracker - FastAPI Backend
REST API for accessing wellbeing data and managing categories
"""

import json
import sqlite3
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import logging


# Pydantic Models for API
class UsageData(BaseModel):
    app_name: str
    category: str
    total_seconds: int
    percentage: float


class DailyUsageResponse(BaseModel):
    date: str
    total_screen_time: int
    categories: List[UsageData]
    top_apps: List[UsageData]


class WeeklyUsageResponse(BaseModel):
    start_date: str
    end_date: str
    daily_breakdown: List[DailyUsageResponse]
    weekly_totals: List[UsageData]


class TopAppsResponse(BaseModel):
    apps: List[UsageData]
    total_apps: int


class CategoryMapping(BaseModel):
    app_name: str
    category: str


class CategoryInfo(BaseModel):
    name: str
    apps: List[str]
    color: str
    description: str


class CategoriesResponse(BaseModel):
    categories: Dict[str, CategoryInfo]


class HourlyUsageData(BaseModel):
    hour: int
    total_seconds: int
    apps: List[UsageData]


class HourlyBreakdownResponse(BaseModel):
    date: str
    hourly_data: List[HourlyUsageData]


class ComponentStatus(BaseModel):
    name: str
    status: str
    details: Dict[str, Union[str, int, float, None, List[str]]]
    warnings: List[str] = []


class DiagnosticsResponse(BaseModel):
    timestamp: str
    components: List[ComponentStatus]
    warnings: List[str]


# Database Manager
class DatabaseManager:
    """Manages database connections and queries"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        if not self.db_path.exists():
            raise HTTPException(status_code=500, detail="Database not found. Run the collector first.")
        return sqlite3.connect(str(self.db_path))
        
    def execute_query(self, query: str, params: tuple = ()) -> List[tuple]:
        """Execute query and return results"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            results = cursor.fetchall()
            conn.close()
            return results
        except Exception as e:
            logger.error(f"Database query failed. Query: {query}, Params: {params}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    def table_exists(self, table: str) -> bool:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            exists = cursor.fetchone() is not None
            conn.close()
            return exists
        except Exception:
            return False


# Category Manager
class CategoryManager:
    """Manages app-to-category mappings"""
    
    def __init__(self, categories_path: str):
        self.categories_path = Path(categories_path)
        
    def load_categories(self) -> Dict:
        """Load categories from JSON file"""
        try:
            if self.categories_path.exists():
                with open(self.categories_path, 'r') as f:
                    return json.load(f)
            else:
                return {"categories": {}}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error loading categories: {str(e)}")
            
    def save_categories(self, categories_data: Dict):
        """Save categories to JSON file"""
        try:
            categories_data['updated_at'] = datetime.now().isoformat()
            with open(self.categories_path, 'w') as f:
                json.dump(categories_data, f, indent=2)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error saving categories: {str(e)}")


# Configuration
DB_PATH = "data/wellbeing.db"
CATEGORIES_PATH = "data/app_categories.json"

# Initialize FastAPI app
APP_START_TIME = datetime.now(timezone.utc)()

app = FastAPI(
    title="Digital Wellbeing Tracker API",
    description="REST API for personal digital wellbeing tracking and analytics",
    version="1.0.0"
)

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3847", "http://127.0.0.1:3847"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize managers
db_manager = DatabaseManager(DB_PATH)
category_manager = CategoryManager(CATEGORIES_PATH)

# Setup logging
log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'backend.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# Dependency injection
def get_db_manager() -> DatabaseManager:
    return db_manager


def get_category_manager() -> CategoryManager:
    return category_manager


# API Routes

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Digital Wellbeing Tracker API", "status": "healthy"}


@app.get("/usage/daily", response_model=DailyUsageResponse)
async def get_daily_usage(
    date_param: str = Query(..., alias="date", description="Date in YYYY-MM-DD format"),
    db: DatabaseManager = Depends(get_db_manager)
):
    """Get daily usage statistics for a specific date"""
    
    try:
        # Validate date format
        target_date = datetime.strptime(date_param, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    has_daily_usage = db.table_exists('daily_usage')
    has_daily_category = db.table_exists('daily_category_usage')
    fallback_used = False

    categories: List[UsageData] = []
    top_apps: List[UsageData] = []
    total_screen_time = 0

    if has_daily_usage and has_daily_category:
        try:
            category_query = """
                SELECT category, SUM(total_seconds) as total_seconds
                FROM daily_category_usage
                WHERE date = ? AND device_type = 'desktop'
                GROUP BY category
                ORDER BY total_seconds DESC
            """
            category_results = db.execute_query(category_query, (str(target_date),))
            total_screen_time = sum(row[1] for row in category_results)
            for category, seconds in category_results:
                percentage = (seconds / total_screen_time * 100) if total_screen_time > 0 else 0
                categories.append(UsageData(
                    app_name="",
                    category=category or 'Uncategorized',
                    total_seconds=seconds,
                    percentage=round(percentage, 2)
                ))
            apps_query = """
                SELECT app_name, category, total_seconds
                FROM daily_usage
                WHERE date = ? AND device_type = 'desktop'
                ORDER BY total_seconds DESC
                LIMIT 10
            """
            apps_results = db.execute_query(apps_query, (str(target_date),))
            for app_name, category, seconds in apps_results:
                percentage = (seconds / total_screen_time * 100) if total_screen_time > 0 else 0
                top_apps.append(UsageData(
                    app_name=app_name,
                    category=category or 'Uncategorized',
                    total_seconds=seconds,
                    percentage=round(percentage, 2)
                ))
        except HTTPException:
            # Fall back if queries failed
            has_daily_usage = False
            has_daily_category = False
    
    if not has_daily_usage or not has_daily_category:
        # Fallback: compute from raw events to avoid 500s when processor hasn't run yet
        fallback_used = True
        try:
            events_query = """
                SELECT app_name, SUM(duration_seconds) as total_seconds
                FROM events
                WHERE DATE(timestamp)=? AND device_type='desktop'
                GROUP BY app_name
                ORDER BY total_seconds DESC
            """
            raw = db.execute_query(events_query, (str(target_date),))
            total_screen_time = sum(r[1] for r in raw)
            # Top apps (limit 10)
            for app_name, seconds in raw[:10]:
                perc = (seconds / total_screen_time * 100) if total_screen_time > 0 else 0
                top_apps.append(UsageData(
                    app_name=app_name,
                    category='Uncategorized',
                    total_seconds=seconds,
                    percentage=round(perc, 2)
                ))
            # Single pseudo-category if we have any data
            if total_screen_time > 0:
                categories.append(UsageData(
                    app_name="",
                    category="Uncategorized",
                    total_seconds=total_screen_time,
                    percentage=100.0
                ))
        except HTTPException:
            pass
    
    return DailyUsageResponse(
        date=str(target_date),
        total_screen_time=total_screen_time,
        categories=categories,
        top_apps=top_apps
    )


@app.get("/usage/weekly", response_model=WeeklyUsageResponse)
async def get_weekly_usage(
    start: str = Query(..., description="Start date in YYYY-MM-DD format"),
    db: DatabaseManager = Depends(get_db_manager)
):
    """Get weekly usage statistics starting from a specific date"""
    
    try:
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
        end_date = start_date + timedelta(days=6)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Get daily breakdown
    daily_breakdown = []
    current_date = start_date
    
    while current_date <= end_date:
        try:
            daily_data = await get_daily_usage(str(current_date), db)
            daily_breakdown.append(daily_data)
        except HTTPException:
            # Add empty day if no data
            daily_breakdown.append(DailyUsageResponse(
                date=str(current_date),
                total_screen_time=0,
                categories=[],
                top_apps=[]
            ))
        current_date += timedelta(days=1)
    
    # Calculate weekly totals
    weekly_totals_query = """
        SELECT category, SUM(total_seconds) as total_seconds
        FROM daily_category_usage
        WHERE date BETWEEN ? AND ? AND device_type = 'desktop'
        GROUP BY category
        ORDER BY total_seconds DESC
    """
    weekly_results = db.execute_query(weekly_totals_query, (str(start_date), str(end_date)))
    
    total_weekly_time = sum(row[1] for row in weekly_results)
    weekly_totals = []
    
    for category, seconds in weekly_results:
        percentage = (seconds / total_weekly_time * 100) if total_weekly_time > 0 else 0
        weekly_totals.append(UsageData(
            app_name="",
            category=category,
            total_seconds=seconds,
            percentage=round(percentage, 2)
        ))
    
    return WeeklyUsageResponse(
        start_date=str(start_date),
        end_date=str(end_date),
        daily_breakdown=daily_breakdown,
        weekly_totals=weekly_totals
    )


@app.get("/apps/top", response_model=TopAppsResponse)
async def get_top_apps(
    limit: int = Query(default=10, description="Number of top apps to return"),
    days: int = Query(default=7, description="Number of days to look back"),
    db: DatabaseManager = Depends(get_db_manager)
):
    """Get top N most used apps over the specified period"""
    
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")
    
    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 365")
    
    end_date = date.today()
    start_date = end_date - timedelta(days=days-1)
    
    # Check if daily_usage table exists, use fallback if not
    use_fallback = not db.table_exists('daily_usage')
    apps = []
    
    if not use_fallback:
        try:
            query = """
                SELECT app_name, category, SUM(total_seconds) as total_seconds
                FROM daily_usage
                WHERE date BETWEEN ? AND ? AND device_type = 'desktop'
                GROUP BY app_name, category
                ORDER BY total_seconds DESC
                LIMIT ?
            """
            
            results = db.execute_query(query, (str(start_date), str(end_date), limit))
            
            # Calculate total time for percentages
            total_time_query = """
                SELECT SUM(total_seconds) as total_time
                FROM daily_usage
                WHERE date BETWEEN ? AND ? AND device_type = 'desktop'
            """
            total_time_result = db.execute_query(total_time_query, (str(start_date), str(end_date)))
            total_time = total_time_result[0][0] if total_time_result and total_time_result[0][0] else 0
            
            for app_name, category, seconds in results:
                percentage = (seconds / total_time * 100) if total_time > 0 else 0
                apps.append(UsageData(
                    app_name=app_name,
                    category=category or 'Uncategorized',
                    total_seconds=seconds,
                    percentage=round(percentage, 2)
                ))
        except HTTPException:
            use_fallback = True
    
    if use_fallback:
        # Fallback: compute from raw events
        try:
            fallback_query = """
                SELECT app_name, SUM(duration_seconds) as total_seconds
                FROM events
                WHERE DATE(timestamp) BETWEEN ? AND ? AND device_type='desktop'
                GROUP BY app_name
                ORDER BY total_seconds DESC
                LIMIT ?
            """
            results = db.execute_query(fallback_query, (str(start_date), str(end_date), limit))
            
            # Calculate total from events
            total_time_query = """
                SELECT SUM(duration_seconds) FROM events
                WHERE DATE(timestamp) BETWEEN ? AND ? AND device_type='desktop'
            """
            total_time_result = db.execute_query(total_time_query, (str(start_date), str(end_date)))
            total_time = total_time_result[0][0] if total_time_result and total_time_result[0][0] else 0
            
            for app_name, seconds in results:
                percentage = (seconds / total_time * 100) if total_time > 0 else 0
                apps.append(UsageData(
                    app_name=app_name,
                    category='Uncategorized',
                    total_seconds=seconds,
                    percentage=round(percentage, 2)
                ))
        except HTTPException:
            pass  # Return empty list if even events query fails
    
    return TopAppsResponse(apps=apps, total_apps=len(apps))


@app.get("/usage/hourly", response_model=HourlyBreakdownResponse)
async def get_hourly_usage(
    date_param: str = Query(..., alias="date", description="Date in YYYY-MM-DD format"),
    db: DatabaseManager = Depends(get_db_manager)
):
    """Get hourly usage breakdown for a specific date"""
    
    try:
        target_date = datetime.strptime(date_param, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    query = """
        SELECT hour, app_name, category, total_seconds
        FROM hourly_usage
        WHERE date = ? AND device_type = 'desktop'
        ORDER BY hour, total_seconds DESC
    """
    
    results = db.execute_query(query, (str(target_date),))
    
    # Group by hour
    hourly_data = {}
    for hour, app_name, category, seconds in results:
        if hour not in hourly_data:
            hourly_data[hour] = {"total_seconds": 0, "apps": []}
        
        hourly_data[hour]["total_seconds"] += seconds
        hourly_data[hour]["apps"].append(UsageData(
            app_name=app_name,
            category=category,
            total_seconds=seconds,
            percentage=0  # Will calculate later
        ))
    
    # Calculate percentages and format response
    formatted_hourly_data = []
    for hour in range(24):
        if hour in hourly_data:
            hour_total = hourly_data[hour]["total_seconds"]
            apps = hourly_data[hour]["apps"]
            
            # Calculate percentages
            for app in apps:
                app.percentage = round((app.total_seconds / hour_total * 100) if hour_total > 0 else 0, 2)
            
            formatted_hourly_data.append(HourlyUsageData(
                hour=hour,
                total_seconds=hour_total,
                apps=apps
            ))
        else:
            formatted_hourly_data.append(HourlyUsageData(
                hour=hour,
                total_seconds=0,
                apps=[]
            ))
    
    return HourlyBreakdownResponse(
        date=str(target_date),
        hourly_data=formatted_hourly_data
    )


@app.get("/categories", response_model=CategoriesResponse)
async def get_categories(cat_manager: CategoryManager = Depends(get_category_manager)):
    """Get all app categories and their configurations"""
    
    categories_data = cat_manager.load_categories()
    categories_dict = {}
    
    for name, info in categories_data.get("categories", {}).items():
        categories_dict[name] = CategoryInfo(
            name=name,
            apps=info.get("apps", []),
            color=info.get("color", "#9CA3AF"),
            description=info.get("description", "")
        )
    
    return CategoriesResponse(categories=categories_dict)


@app.post("/categories/{category_name}/apps")
async def add_app_to_category(
    category_name: str,
    mapping: CategoryMapping,
    cat_manager: CategoryManager = Depends(get_category_manager)
):
    """Add an app to a specific category"""
    
    categories_data = cat_manager.load_categories()
    
    if category_name not in categories_data.get("categories", {}):
        raise HTTPException(status_code=404, detail="Category not found")
    
    app_name_lower = mapping.app_name.lower()
    
    # Remove from other categories first
    for cat_name, cat_info in categories_data["categories"].items():
        if app_name_lower in cat_info.get("apps", []):
            cat_info["apps"].remove(app_name_lower)
    
    # Add to target category
    if app_name_lower not in categories_data["categories"][category_name]["apps"]:
        categories_data["categories"][category_name]["apps"].append(app_name_lower)
    
    cat_manager.save_categories(categories_data)
    
    return {"message": f"App '{mapping.app_name}' added to category '{category_name}'"}


@app.delete("/categories/{category_name}/apps/{app_name}")
async def remove_app_from_category(
    category_name: str,
    app_name: str,
    cat_manager: CategoryManager = Depends(get_category_manager)
):
    """Remove an app from a specific category"""
    
    categories_data = cat_manager.load_categories()
    
    if category_name not in categories_data.get("categories", {}):
        raise HTTPException(status_code=404, detail="Category not found")
    
    app_name_lower = app_name.lower()
    
    if app_name_lower in categories_data["categories"][category_name]["apps"]:
        categories_data["categories"][category_name]["apps"].remove(app_name_lower)
        cat_manager.save_categories(categories_data)
        return {"message": f"App '{app_name}' removed from category '{category_name}'"}
    else:
        raise HTTPException(status_code=404, detail="App not found in category")


@app.get("/stats/summary")
async def get_summary_stats(
    days: int = Query(default=30, description="Number of days to summarize"),
    db: DatabaseManager = Depends(get_db_manager)
):
    """Get summary statistics for the specified period"""
    
    end_date = date.today()
    start_date = end_date - timedelta(days=days-1)
    
    # Determine if aggregated table exists; fallback to raw events if missing
    use_fallback = not db.table_exists('daily_category_usage')
    if not use_fallback:
        try:
            total_time_query = """
                SELECT SUM(total_seconds) as total_time
                FROM daily_category_usage
                WHERE date BETWEEN ? AND ? AND device_type = 'desktop'
            """
            total_time_result = db.execute_query(total_time_query, (str(start_date), str(end_date)))
            total_time = total_time_result[0][0] if total_time_result and total_time_result[0][0] else 0
        except HTTPException:
            use_fallback = True
            total_time = 0
    if use_fallback:
        # Approximate from events
        events_total_query = """
            SELECT SUM(duration_seconds) FROM events
            WHERE DATE(timestamp) BETWEEN ? AND ? AND device_type='desktop'
        """
        try:
            res = db.execute_query(events_total_query, (str(start_date), str(end_date)))
            total_time = res[0][0] if res and res[0] and res[0][0] else 0
        except HTTPException:
            total_time = 0
    
    # Average daily screen time
    avg_daily_time = total_time / days if days > 0 else 0
    
    # Most productive day (assuming 'Work' category indicates productivity)
    productive_result = None
    if not use_fallback:
        try:
            most_productive_query = """
                SELECT date, total_seconds
                FROM daily_category_usage
                WHERE date BETWEEN ? AND ? AND device_type = 'desktop' AND category = 'Work'
                ORDER BY total_seconds DESC
                LIMIT 1
            """
            productive_result = db.execute_query(most_productive_query, (str(start_date), str(end_date)))
        except HTTPException:
            productive_result = None
    
    # Total unique apps used
    unique_apps = 0
    if not use_fallback and db.table_exists('daily_usage'):
        try:
            unique_apps_query = """
                SELECT COUNT(DISTINCT app_name) as unique_apps
                FROM daily_usage
                WHERE date BETWEEN ? AND ? AND device_type = 'desktop'
            """
            unique_apps_result = db.execute_query(unique_apps_query, (str(start_date), str(end_date)))
            unique_apps = unique_apps_result[0][0] if unique_apps_result else 0
        except HTTPException:
            unique_apps = 0
    else:
        # Fallback from events
        try:
            events_unique_query = """
                SELECT COUNT(DISTINCT app_name) FROM events
                WHERE DATE(timestamp) BETWEEN ? AND ? AND device_type='desktop'
            """
            res = db.execute_query(events_unique_query, (str(start_date), str(end_date)))
            unique_apps = res[0][0] if res else 0
        except HTTPException:
            unique_apps = 0
    
    return {
        "period": {
            "start_date": str(start_date),
            "end_date": str(end_date),
            "days": days
        },
        "totals": {
            "screen_time_seconds": total_time,
            "screen_time_hours": round(total_time / 3600, 2),
            "average_daily_seconds": round(avg_daily_time),
            "average_daily_hours": round(avg_daily_time / 3600, 2)
        },
        "insights": {
            "unique_apps_used": unique_apps,
            "most_productive_day": {
                "date": productive_result[0][0] if productive_result else None,
                "work_seconds": productive_result[0][1] if productive_result else 0
            }
    },
    "fallback": use_fallback
    }


@app.get("/debug/overview-check")
async def debug_overview(date_param: str = Query(default=None, alias="date"), db: DatabaseManager = Depends(get_db_manager)):
    """Detailed breakdown for the overview page to pinpoint failing segment."""
    if not date_param:
        date_param = datetime.now(timezone.utc)().strftime('%Y-%m-%d')
    issues: List[str] = []
    tables = {}
    for t in ["events", "hourly_usage", "daily_usage", "daily_category_usage"]:
        tables[t] = db.table_exists(t)
        if not tables[t]:
            issues.append(f"Missing table: {t}")
    details = {}
    # Try each query independently
    try:
        details['daily_category_usage'] = db.execute_query("SELECT COUNT(*) FROM daily_category_usage WHERE date=?", (date_param,))[0][0] if tables['daily_category_usage'] else None
    except HTTPException as e:
        issues.append(f"daily_category_usage query error: {e.detail}")
    try:
        details['daily_usage_rows'] = db.execute_query("SELECT COUNT(*) FROM daily_usage WHERE date=?", (date_param,))[0][0] if tables['daily_usage'] else None
    except HTTPException as e:
        issues.append(f"daily_usage query error: {e.detail}")
    try:
        details['events_today'] = db.execute_query("SELECT COUNT(*) FROM events WHERE DATE(timestamp)=?", (date_param,))[0][0] if tables['events'] else None
    except HTTPException as e:
        issues.append(f"events query error: {e.detail}")
    return {
        "date": date_param,
        "tables": tables,
        "details": details,
        "issues": issues,
        "hint": "If aggregated tables are missing run processor. If events is 0 ensure collector running."}


@app.get("/diagnostics/status", response_model=DiagnosticsResponse)
async def diagnostics_status(db: DatabaseManager = Depends(get_db_manager), cat_manager: CategoryManager = Depends(get_category_manager)):
    """Return pipeline health & diagnostic information to aid debugging."""
    warnings: List[str] = []

    def one(query: str, params: tuple = (), default=None):
        try:
            res = db.execute_query(query, params)
            if res and res[0] and res[0][0] is not None:
                return res[0][0]
            return default
        except HTTPException:
            return default
        except Exception:
            return default

    # Basic DB stats
    last_event_ts = one("SELECT MAX(timestamp) FROM events WHERE device_type='desktop'")
    events_today = one("SELECT COUNT(*) FROM events WHERE DATE(timestamp)=DATE('now','localtime') AND device_type='desktop'", default=0)
    distinct_apps = one("SELECT COUNT(DISTINCT app_name) FROM events WHERE device_type='desktop'", default=0)
    last_hourly_created = one("SELECT MAX(created_at) FROM hourly_usage WHERE device_type='desktop'")
    last_daily_created = one("SELECT MAX(created_at) FROM daily_usage WHERE device_type='desktop'")

    # DB file info
    db_path = Path(DB_PATH)
    db_exists = db_path.exists()
    db_size = db_path.stat().st_size if db_exists else 0

    # Uptime
    uptime_seconds = (datetime.now(timezone.utc)() - APP_START_TIME).total_seconds()

    # Collector status heuristic
    collector_status = "unknown"
    last_event_age_seconds = None
    if last_event_ts:
        try:
            last_event_dt = datetime.fromisoformat(last_event_ts)
            last_event_age_seconds = (datetime.now(timezone.utc)() - last_event_dt).total_seconds()
            if last_event_age_seconds < 60:
                collector_status = "ok"
            elif last_event_age_seconds < 300:
                collector_status = "stale"
                warnings.append("Collector data older than 1 minute")
            else:
                collector_status = "offline"
                warnings.append("Collector appears offline (no recent events)")
        except ValueError:
            collector_status = "error"
            warnings.append("Unable to parse last event timestamp")
    else:
        collector_status = "no-data"
        warnings.append("No events recorded yet. Is the collector running?")

    # Processor status heuristic: based on time since last_hourly_created
    processor_status = "unknown"
    last_hourly_age_seconds = None
    if last_hourly_created:
        try:
            last_hourly_dt = datetime.fromisoformat(last_hourly_created)
            last_hourly_age_seconds = (datetime.now(timezone.utc)() - last_hourly_dt).total_seconds()
            if last_hourly_age_seconds < 600:  # 10 min
                processor_status = "ok"
            elif last_hourly_age_seconds < 1800:
                processor_status = "stale"
                warnings.append("Processor has not updated hourly_usage in >10 minutes")
            else:
                processor_status = "offline"
                warnings.append("Processor appears offline (no hourly updates >30 minutes)")
        except ValueError:
            processor_status = "error"
            warnings.append("Unable to parse last hourly aggregation timestamp")
    else:
        processor_status = "no-data"
        warnings.append("No hourly aggregation rows yet. Has the processor run?")

    # Daily aggregation freshness (only warn if last_daily_created older than today)
    daily_status = "unknown"
    if last_daily_created:
        try:
            last_daily_dt = datetime.fromisoformat(last_daily_created)
            if last_daily_dt.date() == datetime.now(timezone.utc)().date():
                daily_status = "ok"
            else:
                daily_status = "stale"
                warnings.append("Daily aggregation not updated today yet")
        except ValueError:
            daily_status = "error"
            warnings.append("Unable to parse last daily aggregation timestamp")
    else:
        daily_status = "no-data"
        warnings.append("No daily aggregation rows found")

    # Category coverage
    uncategorized = []
    try:
        raw_uncat = db.execute_query(
            """
            SELECT app_name, SUM(total_seconds) as ts
            FROM daily_usage
            WHERE (category IS NULL OR category='') AND device_type='desktop'
            GROUP BY app_name
            ORDER BY ts DESC
            LIMIT 30
            """
        )
        uncategorized = [r[0] for r in raw_uncat]
    except Exception:
        pass

    categories_data = cat_manager.load_categories()
    total_categories = len(categories_data.get("categories", {}))
    apps_with_category = one("SELECT COUNT(*) FROM app_categories", default=0)

    component_list: List[ComponentStatus] = []
    component_list.append(ComponentStatus(
        name="backend",
        status="ok",
        details={"uptime_seconds": round(uptime_seconds, 2), "version": app.version}
    ))
    component_list.append(ComponentStatus(
        name="database",
        status="ok" if db_exists else "missing",
        details={
            "path": str(db_path),
            "exists": db_exists,
            "size_bytes": db_size,
            "last_event_timestamp": last_event_ts,
            "events_today": events_today,
            "distinct_apps": distinct_apps
        }
    ))
    component_list.append(ComponentStatus(
        name="collector",
        status=collector_status,
        details={"last_event_age_seconds": last_event_age_seconds, "last_event_timestamp": last_event_ts}
    ))
    component_list.append(ComponentStatus(
        name="processor_hourly",
        status=processor_status,
        details={"last_hourly_created": last_hourly_created, "age_seconds": last_hourly_age_seconds}
    ))
    component_list.append(ComponentStatus(
        name="processor_daily",
        status=daily_status,
        details={"last_daily_created": last_daily_created}
    ))
    component_list.append(ComponentStatus(
        name="categories",
        status="ok",
        details={
            "total_categories": total_categories,
            "mapped_apps": apps_with_category,
            "uncategorized_sample": uncategorized
        },
        warnings=["Uncategorized apps present" ] if uncategorized else []
    ))

    # Merge component warnings
    for c in component_list:
        for w in c.warnings:
            if w not in warnings:
                warnings.append(w)

    return DiagnosticsResponse(
        timestamp=datetime.now(timezone.utc)().isoformat(),
        components=component_list,
        warnings=warnings
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8847,
        reload=True,
        log_level="info"
    )
