"""Digital Wellbeing Tracker - Flask Backend

"""
from __future__ import annotations

import json
from datetime import datetime, date, timedelta,timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
import sqlite3

from flask import Flask, jsonify, request
from flask_cors import CORS

# (Optional future) If we decide to leverage SQLAlchemy ORM models we created in models.py
# we can import them; for now we keep raw SQL for parity & minimal churn.
# from .database import SessionLocal
# from . import models as orm_models


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data/wellbeing.db"
CATEGORIES_PATH = PROJECT_ROOT / "data/app_categories.json"
APP_START_TIME = datetime.now()

log_dir = PROJECT_ROOT / "logs"
log_dir.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'backend.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("backend")

app = Flask(__name__)
CORS(app, origins=["http://localhost:3847", "http://127.0.0.1:3847"], supports_credentials=True)
app.config["API_VERSION"] = "1.0.0"


class HTTPError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


@app.errorhandler(HTTPError)
def handle_http_error(e: HTTPError):
    return jsonify({"detail": e.detail}), e.status_code


class DatabaseManager:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def get_connection(self) -> sqlite3.Connection:
        if not self.db_path.exists():
            raise HTTPError(500, "Database not found. Run the collector first.")
        return sqlite3.connect(str(self.db_path))

    def execute_query(self, query: str, params: tuple = ()) -> List[tuple]:
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute(query, params)
            rows = cur.fetchall()
            conn.close()
            return rows
        except HTTPError:
            raise
        except Exception as e:
            logger.exception("DB query failed")
            raise HTTPError(500, f"Database error: {e}")

    def table_exists(self, table: str) -> bool:
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            ok = cur.fetchone() is not None
            conn.close()
            return ok
        except Exception:
            return False


class CategoryManager:
    def __init__(self, path: Path):
        self.path = path

    def load_categories(self) -> Dict[str, Any]:
        try:
            if self.path.exists():
                with open(self.path, 'r') as f:
                    return json.load(f)
            return {"categories": {}}
        except Exception as e:
            raise HTTPError(500, f"Error loading categories: {e}")

    def save_categories(self, data: Dict[str, Any]):
        try:
            data['updated_at'] = datetime.now().isoformat()
            with open(self.path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            raise HTTPError(500, f"Error saving categories: {e}")


db_manager = DatabaseManager(DB_PATH)
category_manager = CategoryManager(CATEGORIES_PATH)


def _parse_date(date_str: str, field: str = "date") -> date:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPError(400, f"Invalid {field} format. Use YYYY-MM-DD")


@app.route("/")
def root():
    return {"message": "Digital Wellbeing Tracker API", "status": "healthy"}


@app.get("/usage/daily")
def daily_usage():
    date_param = request.args.get("date")
    if not date_param:
        raise HTTPError(400, "Missing required query param 'date'")
    target_date = _parse_date(date_param)

    has_daily_usage = db_manager.table_exists('daily_usage')
    has_daily_category = db_manager.table_exists('daily_category_usage')

    categories: List[Dict[str, Any]] = []
    top_apps: List[Dict[str, Any]] = []
    total_screen_time = 0

    if has_daily_usage and has_daily_category:
        try:
            cat_q = """
                SELECT category, SUM(total_seconds) as total_seconds
                FROM daily_category_usage
                WHERE date = ? AND device_type = 'desktop'
                GROUP BY category
                ORDER BY total_seconds DESC
            """
            cat_rows = db_manager.execute_query(cat_q, (str(target_date),))
            total_screen_time = sum(r[1] for r in cat_rows)
            for category, seconds in cat_rows:
                pct = (seconds / total_screen_time * 100) if total_screen_time else 0
                categories.append({
                    "app_name": "",
                    "category": category or 'Uncategorized',
                    "total_seconds": seconds,
                    "percentage": round(pct, 2),
                    "website_url": None
                })
            apps_q = """
                SELECT app_name, category, website_url, total_seconds
                FROM daily_usage
                WHERE date = ? AND device_type = 'desktop'
                ORDER BY total_seconds DESC
                LIMIT 10
            """
            apps_rows = db_manager.execute_query(apps_q, (str(target_date),))
            for app_name, category, website_url, seconds in apps_rows:
                pct = (seconds / total_screen_time * 100) if total_screen_time else 0
                top_apps.append({
                    "app_name": app_name,
                    "category": category or 'Uncategorized',
                    "total_seconds": seconds,
                    "percentage": round(pct, 2),
                    "website_url": website_url
                })
        except HTTPError:
            has_daily_usage = False
            has_daily_category = False

    if not has_daily_usage or not has_daily_category:
        # fallback raw events
        try:
            events_q = """
                SELECT app_name, SUM(duration_seconds) as total_seconds
                FROM events
                WHERE DATE(timestamp)=? AND device_type='desktop'
                GROUP BY app_name
                ORDER BY total_seconds DESC
            """
            raw_rows = db_manager.execute_query(events_q, (str(target_date),))
            total_screen_time = sum(r[1] for r in raw_rows)
            for app_name, seconds in raw_rows[:10]:
                pct = (seconds / total_screen_time * 100) if total_screen_time else 0
                top_apps.append({
                    "app_name": app_name,
                    "category": 'Uncategorized',
                    "total_seconds": seconds,
                    "percentage": round(pct, 2),
                    "website_url": None
                })
            if total_screen_time > 0:
                categories.append({
                    "app_name": "",
                    "category": "Uncategorized",
                    "total_seconds": total_screen_time,
                    "percentage": 100.0,
                    "website_url": None
                })
        except HTTPError:
            pass

    return {
        "date": str(target_date),
        "total_screen_time": total_screen_time,
        "categories": categories,
        "top_apps": top_apps
    }


@app.get("/usage/weekly")
def weekly_usage():
    start_param = request.args.get("start")
    if not start_param:
        raise HTTPError(400, "Missing required query param 'start'")
    start_date = _parse_date(start_param, 'start')
    end_date = start_date + timedelta(days=6)

    daily_breakdown: List[Dict[str, Any]] = []
    current = start_date
    while current <= end_date:
        try:
            # reuse logic by internal call
            with app.test_request_context(f"/usage/daily?date={current}"):
                daily_breakdown.append(daily_usage())
        except HTTPError:
            daily_breakdown.append({
                "date": str(current),
                "total_screen_time": 0,
                "categories": [],
                "top_apps": []
            })
        current += timedelta(days=1)

    weekly_q = """
        SELECT category, SUM(total_seconds) as total_seconds
        FROM daily_category_usage
        WHERE date BETWEEN ? AND ? AND device_type = 'desktop'
        GROUP BY category
        ORDER BY total_seconds DESC
    """
    rows = db_manager.execute_query(weekly_q, (str(start_date), str(end_date)))
    total_week = sum(r[1] for r in rows)
    weekly_totals = []
    for category, seconds in rows:
        pct = (seconds / total_week * 100) if total_week else 0
        weekly_totals.append({
            "app_name": "",
            "category": category,
            "total_seconds": seconds,
            "percentage": round(pct, 2),
            "website_url": None
        })

    return {
        "start_date": str(start_date),
        "end_date": str(end_date),
        "daily_breakdown": daily_breakdown,
        "weekly_totals": weekly_totals
    }


@app.get("/apps/top")
def top_apps():
    try:
        limit = int(request.args.get("limit", 10))
        days = int(request.args.get("days", 7))
    except ValueError:
        raise HTTPError(400, "Numeric query params invalid")
    if not (1 <= limit <= 100):
        raise HTTPError(400, "Limit must be between 1 and 100")
    if not (1 <= days <= 365):
        raise HTTPError(400, "Days must be between 1 and 365")

    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)
    use_fallback = not db_manager.table_exists('daily_usage')
    apps: List[Dict[str, Any]] = []
    if not use_fallback:
        try:
            q = """
                SELECT app_name, category, SUM(total_seconds) as total_seconds
                FROM daily_usage
                WHERE date BETWEEN ? AND ? AND device_type = 'desktop'
                GROUP BY app_name, category
                ORDER BY total_seconds DESC
                LIMIT ?
            """
            rows = db_manager.execute_query(q, (str(start_date), str(end_date), limit))
            tot_q = """
                SELECT SUM(total_seconds) FROM daily_usage
                WHERE date BETWEEN ? AND ? AND device_type = 'desktop'
            """
            total_time_rows = db_manager.execute_query(tot_q, (str(start_date), str(end_date)))
            total_time = total_time_rows[0][0] if total_time_rows and total_time_rows[0][0] else 0
            for app_name, category, seconds in rows:
                pct = (seconds / total_time * 100) if total_time else 0
                apps.append({
                    "app_name": app_name,
                    "category": category or 'Uncategorized',
                    "total_seconds": seconds,
                    "percentage": round(pct, 2),
                    "website_url": None
                })
        except HTTPError:
            use_fallback = True
    if use_fallback:
        fb_q = """
            SELECT app_name, SUM(duration_seconds) as total_seconds
            FROM events
            WHERE DATE(timestamp) BETWEEN ? AND ? AND device_type='desktop'
            GROUP BY app_name
            ORDER BY total_seconds DESC
            LIMIT ?
        """
        rows = db_manager.execute_query(fb_q, (str(start_date), str(end_date), limit))
        tot_q = """
            SELECT SUM(duration_seconds) FROM events
            WHERE DATE(timestamp) BETWEEN ? AND ? AND device_type='desktop'
        """
        total_time_rows = db_manager.execute_query(tot_q, (str(start_date), str(end_date)))
        total_time = total_time_rows[0][0] if total_time_rows and total_time_rows[0][0] else 0
        for app_name, seconds in rows:
            pct = (seconds / total_time * 100) if total_time else 0
            apps.append({
                "app_name": app_name,
                "category": 'Uncategorized',
                "total_seconds": seconds,
                "percentage": round(pct, 2),
                "website_url": None
            })
    return {"apps": apps, "total_apps": len(apps)}


@app.get("/usage/hourly")
def hourly_usage():
    date_param = request.args.get("date")
    if not date_param:
        raise HTTPError(400, "Missing required query param 'date'")
    target_date = _parse_date(date_param)
    q = """
        SELECT hour, app_name, category, total_seconds
        FROM hourly_usage
        WHERE date = ? AND device_type = 'desktop'
        ORDER BY hour, total_seconds DESC
    """
    rows = db_manager.execute_query(q, (str(target_date),))
    hourly: Dict[int, Dict[str, Any]] = {}
    for hour, app_name, category, seconds in rows:
        if hour not in hourly:
            hourly[hour] = {"total_seconds": 0, "apps": []}
        hourly[hour]["total_seconds"] += seconds
        hourly[hour]["apps"].append({
            "app_name": app_name,
            "category": category,
            "total_seconds": seconds,
            "percentage": 0,
            "website_url": None
        })
    formatted = []
    for h in range(24):
        if h in hourly:
            total = hourly[h]["total_seconds"]
            for app_dict in hourly[h]["apps"]:
                app_dict["percentage"] = round((app_dict["total_seconds"] / total * 100) if total else 0, 2)
            formatted.append({"hour": h, "total_seconds": total, "apps": hourly[h]["apps"]})
        else:
            formatted.append({"hour": h, "total_seconds": 0, "apps": []})
    return {"date": str(target_date), "hourly_data": formatted}


@app.get("/categories")
def categories():
    data = category_manager.load_categories()
    categories_dict = {}
    for name, info in data.get("categories", {}).items():
        categories_dict[name] = {
            "name": name,
            "apps": info.get("apps", []),
            "color": info.get("color", "#9CA3AF"),
            "description": info.get("description", "")
        }
    return {"categories": categories_dict}


@app.post("/categories/<category_name>/apps")
def add_app_to_category(category_name: str):
    body = request.get_json(force=True, silent=True) or {}
    app_name = body.get("app_name")
    if not app_name:
        raise HTTPError(400, "Missing app_name in body")
    data = category_manager.load_categories()
    if category_name not in data.get("categories", {}):
        raise HTTPError(404, "Category not found")
    app_lower = app_name.lower()
    for cat, info in data["categories"].items():
        if app_lower in info.get("apps", []):
            info["apps"].remove(app_lower)
    if app_lower not in data["categories"][category_name]["apps"]:
        data["categories"][category_name]["apps"].append(app_lower)
    category_manager.save_categories(data)
    return {"message": f"App '{app_name}' added to category '{category_name}'"}


@app.delete("/categories/<category_name>/apps/<app_name>")
def remove_app_from_category(category_name: str, app_name: str):
    data = category_manager.load_categories()
    if category_name not in data.get("categories", {}):
        raise HTTPError(404, "Category not found")
    app_lower = app_name.lower()
    if app_lower in data["categories"][category_name]["apps"]:
        data["categories"][category_name]["apps"].remove(app_lower)
        category_manager.save_categories(data)
        return {"message": f"App '{app_name}' removed from category '{category_name}'"}
    raise HTTPError(404, "App not found in category")


@app.get("/stats/summary")
def summary_stats():
    try:
        days = int(request.args.get("days", 30))
    except ValueError:
        raise HTTPError(400, "Invalid days parameter")
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)
    use_fallback = not db_manager.table_exists('daily_category_usage')
    total_time = 0
    if not use_fallback:
        try:
            q = """
                SELECT SUM(total_seconds) FROM daily_category_usage
                WHERE date BETWEEN ? AND ? AND device_type = 'desktop'
            """
            res = db_manager.execute_query(q, (str(start_date), str(end_date)))
            total_time = res[0][0] if res and res[0] and res[0][0] else 0
        except HTTPError:
            use_fallback = True
    if use_fallback:
        q = """
            SELECT SUM(duration_seconds) FROM events
            WHERE DATE(timestamp) BETWEEN ? AND ? AND device_type='desktop'
        """
        try:
            res = db_manager.execute_query(q, (str(start_date), str(end_date)))
            total_time = res[0][0] if res and res[0] and res[0][0] else 0
        except HTTPError:
            total_time = 0
    avg_daily = total_time / days if days else 0
    productive_row = None
    if not use_fallback:
        try:
            prod_q = """
                SELECT date, total_seconds FROM daily_category_usage
                WHERE date BETWEEN ? AND ? AND device_type = 'desktop' AND category = 'Work'
                ORDER BY total_seconds DESC LIMIT 1
            """
            pr = db_manager.execute_query(prod_q, (str(start_date), str(end_date)))
            productive_row = pr[0] if pr else None
        except HTTPError:
            productive_row = None
    # unique apps
    unique_apps = 0
    if not use_fallback and db_manager.table_exists('daily_usage'):
        try:
            uq_q = """
                SELECT COUNT(DISTINCT app_name) FROM daily_usage
                WHERE date BETWEEN ? AND ? AND device_type = 'desktop'
            """
            rq = db_manager.execute_query(uq_q, (str(start_date), str(end_date)))
            unique_apps = rq[0][0] if rq else 0
        except HTTPError:
            unique_apps = 0
    else:
        uq_q = """
            SELECT COUNT(DISTINCT app_name) FROM events
            WHERE DATE(timestamp) BETWEEN ? AND ? AND device_type='desktop'
        """
        try:
            rq = db_manager.execute_query(uq_q, (str(start_date), str(end_date)))
            unique_apps = rq[0][0] if rq else 0
        except HTTPError:
            unique_apps = 0
    return {
        "period": {"start_date": str(start_date), "end_date": str(end_date), "days": days},
        "totals": {
            "screen_time_seconds": total_time,
            "screen_time_hours": round(total_time / 3600, 2),
            "average_daily_seconds": round(avg_daily),
            "average_daily_hours": round(avg_daily / 3600, 2)
        },
        "insights": {
            "unique_apps_used": unique_apps,
            "most_productive_day": {
                "date": productive_row[0] if productive_row else None,
                "work_seconds": productive_row[1] if productive_row else 0
            }
        },
        "fallback": use_fallback
    }


@app.get("/debug/overview-check")
def debug_overview():
    date_param = request.args.get("date") or datetime.utcnow().strftime('%Y-%m-%d')
    issues: List[str] = []
    tables: Dict[str, bool] = {}
    for t in ["events", "hourly_usage", "daily_usage", "daily_category_usage"]:
        tables[t] = db_manager.table_exists(t)
        if not tables[t]:
            issues.append(f"Missing table: {t}")
    details: Dict[str, Any] = {}
    try:
        details['daily_category_usage'] = db_manager.execute_query("SELECT COUNT(*) FROM daily_category_usage WHERE date=?", (date_param,))[0][0] if tables['daily_category_usage'] else None
    except HTTPError as e:
        issues.append(f"daily_category_usage query error: {e.detail}")
    try:
        details['daily_usage_rows'] = db_manager.execute_query("SELECT COUNT(*) FROM daily_usage WHERE date=?", (date_param,))[0][0] if tables['daily_usage'] else None
    except HTTPError as e:
        issues.append(f"daily_usage query error: {e.detail}")
    try:
        details['events_today'] = db_manager.execute_query("SELECT COUNT(*) FROM events WHERE DATE(timestamp)=?", (date_param,))[0][0] if tables['events'] else None
    except HTTPError as e:
        issues.append(f"events query error: {e.detail}")
    return {
        "date": date_param,
        "tables": tables,
        "details": details,
        "issues": issues,
        "hint": "If aggregated tables are missing run processor. If events is 0 ensure collector running."}


@app.get("/diagnostics/status")
def diagnostics_status():
    warnings: List[str] = []

    def one(query: str, params: tuple = (), default=None):
        try:
            res = db_manager.execute_query(query, params)
            if res and res[0] and res[0][0] is not None:
                return res[0][0]
            return default
        except HTTPError:
            return default
        except Exception:
            return default

    last_event_ts = one("SELECT MAX(timestamp) FROM events WHERE device_type='desktop'")
    events_today = one("SELECT COUNT(*) FROM events WHERE DATE(timestamp)=DATE('now','localtime') AND device_type='desktop'", default=0)
    distinct_apps = one("SELECT COUNT(DISTINCT app_name) FROM events WHERE device_type='desktop'", default=0)
    last_hourly_created = one("SELECT MAX(created_at) FROM hourly_usage WHERE device_type='desktop'")
    last_daily_created = one("SELECT MAX(created_at) FROM daily_usage WHERE device_type='desktop'")

    db_path = Path(DB_PATH)
    db_exists = db_path.exists()
    db_size = db_path.stat().st_size if db_exists else 0
    uptime_seconds = (datetime.utcnow() - APP_START_TIME).total_seconds()

    collector_status = "unknown"
    last_event_age_seconds = None
    if last_event_ts:
        try:
            last_event_dt = datetime.fromisoformat(last_event_ts)
            last_event_age_seconds = (datetime.utcnow() - last_event_dt).total_seconds()
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

    processor_status = "unknown"
    last_hourly_age_seconds = None
    if last_hourly_created:
        try:
            last_hourly_dt = datetime.fromisoformat(last_hourly_created)
            last_hourly_age_seconds = (datetime.utcnow() - last_hourly_dt).total_seconds()
            if last_hourly_age_seconds < 600:
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

    daily_status = "unknown"
    if last_daily_created:
        try:
            last_daily_dt = datetime.fromisoformat(last_daily_created)
            if last_daily_dt.date() == datetime.utcnow().date():
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

    uncategorized: List[str] = []
    try:
        raw_uncat = db_manager.execute_query(
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

    categories_data = category_manager.load_categories()
    total_categories = len(categories_data.get("categories", {}))
    apps_with_category = one("SELECT COUNT(*) FROM app_categories", default=0)

    components: List[Dict[str, Any]] = []
    components.append({
        "name": "backend",
        "status": "ok",
        "details": {"uptime_seconds": round(uptime_seconds, 2), "version": app.config["API_VERSION"]},
        "warnings": []
    })
    components.append({
        "name": "database",
        "status": "ok" if db_exists else "missing",
        "details": {
            "path": str(db_path),
            "exists": db_exists,
            "size_bytes": db_size,
            "last_event_timestamp": last_event_ts,
            "events_today": events_today,
            "distinct_apps": distinct_apps
        },
        "warnings": []
    })
    components.append({
        "name": "collector",
        "status": collector_status,
        "details": {"last_event_age_seconds": last_event_age_seconds, "last_event_timestamp": last_event_ts},
        "warnings": []
    })
    components.append({
        "name": "processor_hourly",
        "status": processor_status,
        "details": {"last_hourly_created": last_hourly_created, "age_seconds": last_hourly_age_seconds},
        "warnings": []
    })
    components.append({
        "name": "processor_daily",
        "status": daily_status,
        "details": {"last_daily_created": last_daily_created},
        "warnings": []
    })
    components.append({
        "name": "categories",
        "status": "ok",
        "details": {
            "total_categories": total_categories,
            "mapped_apps": apps_with_category,
            "uncategorized_sample": uncategorized
        },
        "warnings": ["Uncategorized apps present"] if uncategorized else []
    })

    for comp in components:
        for w in comp.get("warnings", []):
            if w not in warnings:
                warnings.append(w)

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "components": components,
        "warnings": warnings
    }


if __name__ == "__main__":
    # Dev server (for local debugging). Production uses gunicorn via start script.
    app.run(host="0.0.0.0", port=8847, debug=True)
