"""Digital Wellbeing Tracker - Flask Backend

"""
from __future__ import annotations

import json
from datetime import datetime, date, timedelta,timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
from sqlalchemy import func, inspect

from flask import Flask, jsonify, request, abort
from flask_cors import CORS

from .database import db, DATABASE_URL
from . import models as m


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data/wellbeing.db"
CATEGORIES_PATH = PROJECT_ROOT / "data/app_categories.json"
APP_START_TIME = datetime.now(timezone.utc)

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
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

CORS(app, origins=["http://localhost:3847", "http://127.0.0.1:3847"], supports_credentials=True)
app.config["API_VERSION"] = "1.0.0"


@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(500)
def handle_http_error(e):
    return jsonify(detail=str(e)), e.code

def table_exists(table_name: str) -> bool:
    with app.app_context():
        return inspect(db.engine).has_table(table_name)


def _parse_date(date_str: str, field: str = "date") -> date:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        abort(400, description=f"Invalid {field} format. Use YYYY-MM-DD")


@app.route("/")
def root():
    return {"message": "Digital Wellbeing Tracker API", "status": "healthy"}


@app.get("/usage/daily")
def daily_usage():
    date_param = request.args.get("date")
    if not date_param:
        abort(400, "Missing required query param 'date'")
    target_date = _parse_date(date_param)

    if not table_exists('daily_usage') or not table_exists('daily_category_usage'):
        abort(503, "Aggregated data not available. Please run the processor.")

    try:
        cat_rows = db.session.query(
            m.DailyCategoryUsage.category,
            func.sum(m.DailyCategoryUsage.total_seconds)
        ).filter(
            m.DailyCategoryUsage.date == target_date,
            m.DailyCategoryUsage.device_type == 'desktop'
        ).group_by(m.DailyCategoryUsage.category).order_by(
            func.sum(m.DailyCategoryUsage.total_seconds).desc()
        ).all()

        total_screen_time = sum(r[1] for r in cat_rows)
        categories = [
            {
                "app_name": "",
                "category": category or 'Uncategorized',
                "total_seconds": seconds,
                "percentage": round((seconds / total_screen_time * 100) if total_screen_time else 0, 2),
                "website_url": None
            } for category, seconds in cat_rows
        ]

        apps_rows = db.session.query(
            m.DailyUsage.app_name,
            m.DailyUsage.category,
            m.DailyUsage.website_url,
            m.DailyUsage.total_seconds
        ).filter(
            m.DailyUsage.date == target_date,
            m.DailyUsage.device_type == 'desktop'
        ).order_by(m.DailyUsage.total_seconds.desc()).limit(10).all()

        top_apps = [
            {
                "app_name": app_name,
                "category": category or 'Uncategorized',
                "total_seconds": seconds,
                "percentage": round((seconds / total_screen_time * 100) if total_screen_time else 0, 2),
                "website_url": website_url
            } for app_name, category, website_url, seconds in apps_rows
        ]

    except Exception as e:
        logger.exception("Daily usage query failed")
        abort(500, f"Database error: {e}")

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
        abort(400, "Missing required query param 'start'")
    start_date = _parse_date(start_param, 'start')
    end_date = start_date + timedelta(days=6)

    daily_breakdown: List[Dict[str, Any]] = []
    current = start_date
    while current <= end_date:
        try:
            with app.test_request_context(f"/usage/daily?date={current}"):
                response = daily_usage()
                daily_breakdown.append(response)
        except Exception:
             daily_breakdown.append({
                "date": str(current),
                "total_screen_time": 0,
                "categories": [],
                "top_apps": []
            })
        current += timedelta(days=1)

    rows = db.session.query(
        m.DailyCategoryUsage.category,
        func.sum(m.DailyCategoryUsage.total_seconds)
    ).filter(
        m.DailyCategoryUsage.date.between(start_date, end_date),
        m.DailyCategoryUsage.device_type == 'desktop'
    ).group_by(m.DailyCategoryUsage.category).order_by(
        func.sum(m.DailyCategoryUsage.total_seconds).desc()
    ).all()

    total_week = sum(r[1] for r in rows)
    weekly_totals = [
        {
            "app_name": "",
            "category": category,
            "total_seconds": seconds,
            "percentage": round((seconds / total_week * 100) if total_week else 0, 2),
            "website_url": None
        } for category, seconds in rows
    ]

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
    except (ValueError, TypeError):
        abort(400, "Numeric query params invalid")
    if not (1 <= limit <= 100):
        abort(400, "Limit must be between 1 and 100")
    if not (1 <= days <= 365):
        abort(400, "Days must be between 1 and 365")

    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)

    if not table_exists('daily_usage'):
        abort(503, "Aggregated data not available. Please run the processor.")

    try:
        rows = db.session.query(
            m.DailyUsage.app_name,
            m.DailyUsage.category,
            func.sum(m.DailyUsage.total_seconds)
        ).filter(
            m.DailyUsage.date.between(start_date, end_date),
            m.DailyUsage.device_type == 'desktop'
        ).group_by(m.DailyUsage.app_name, m.DailyUsage.category).order_by(
            func.sum(m.DailyUsage.total_seconds).desc()
        ).limit(limit).all()

        total_time_res = db.session.query(func.sum(m.DailyUsage.total_seconds)).filter(
            m.DailyUsage.date.between(start_date, end_date),
            m.DailyUsage.device_type == 'desktop'
        ).scalar()
        total_time = total_time_res or 0

        apps = [
            {
                "app_name": app_name,
                "category": category or 'Uncategorized',
                "total_seconds": seconds,
                "percentage": round((seconds / total_time * 100) if total_time else 0, 2),
                "website_url": None
            } for app_name, category, seconds in rows
        ]
    except Exception as e:
        logger.exception("Top apps query failed")
        abort(500, f"Database error: {e}")

    return {"apps": apps, "total_apps": len(apps)}


@app.get("/usage/hourly")
def hourly_usage():
    date_param = request.args.get("date")
    if not date_param:
        abort(400, "Missing required query param 'date'")
    target_date = _parse_date(date_param)

    if not table_exists('hourly_usage'):
        abort(503, "Hourly data not available. Please run the processor.")

    rows = db.session.query(
        m.HourlyUsage.hour,
        m.HourlyUsage.app_name,
        m.HourlyUsage.category,
        m.HourlyUsage.total_seconds
    ).filter(
        m.HourlyUsage.date == target_date,
        m.HourlyUsage.device_type == 'desktop'
    ).order_by(m.HourlyUsage.hour, m.HourlyUsage.total_seconds.desc()).all()

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
def get_categories():
    """Returns a list of all categories and their associated apps."""
    if not table_exists('categories'):
        return {"categories": {}}
    
    categories = m.Category.query.all()
    categories_dict = {
        cat.name: {
            "name": cat.name,
            "apps": [app.app_name for app in cat.apps],
            "color": cat.color,
            "description": cat.description
        } for cat in categories
    }
    return {"categories": categories_dict}


@app.post("/categories")
def create_category():
    """Creates a new category."""
    body = request.get_json(force=True, silent=True) or {}
    name = body.get("name")
    if not name:
        abort(400, "Missing 'name' in body")

    if m.Category.query.get(name):
        abort(409, f"Category '{name}' already exists")

    new_category = m.Category(
        name=name,
        color=body.get("color", "#9CA3AF"),
        description=body.get("description", "")
    )
    db.session.add(new_category)
    db.session.commit()
    
    return {
        "message": f"Category '{name}' created successfully",
        "category": {
            "name": new_category.name,
            "color": new_category.color,
            "description": new_category.description,
            "apps": []
        }
    }, 201


@app.put("/categories/<category_name>")
def update_category(category_name: str):
    """Updates a category's color or description."""
    category = m.Category.query.get(category_name)
    if not category:
        abort(404, "Category not found")

    body = request.get_json(force=True, silent=True) or {}
    if "color" in body:
        category.color = body["color"]
    if "description" in body:
        category.description = body["description"]
    
    db.session.commit()
    return {"message": f"Category '{category_name}' updated"}


@app.delete("/categories/<category_name>")
def delete_category(category_name: str):
    """Deletes a category and re-assigns its apps to 'Other'."""
    category = m.Category.query.get(category_name)
    if not category:
        abort(404, "Category not found")
    if category.name == "Other":
        abort(400, "Cannot delete the default 'Other' category")

    other_category = m.Category.query.get("Other")
    if not other_category:
        # Create 'Other' if it doesn't exist
        other_category = m.Category(name="Other", description="Uncategorized applications")
        db.session.add(other_category)

    # Re-assign apps to 'Other'
    for app in category.apps:
        app.category_name = "Other"

    db.session.delete(category)
    db.session.commit()
    return {"message": f"Category '{category_name}' deleted and its apps moved to 'Other'"}


@app.post("/categories/<category_name>/apps")
def add_app_to_category(category_name: str):
    body = request.get_json(force=True, silent=True) or {}
    app_name = body.get("app_name")
    if not app_name:
        abort(400, "Missing app_name in body")

    if not m.Category.query.get(category_name):
        abort(404, "Category not found")

    # Remove from old category if it exists
    m.AppCategory.query.filter_by(app_name=app_name).delete()

    # Add to new category
    new_mapping = m.AppCategory(app_name=app_name, category_name=category_name)
    db.session.add(new_mapping)
    db.session.commit()
    
    return {"message": f"App '{app_name}' assigned to category '{category_name}'"}


@app.delete("/categories/<category_name>/apps/<app_name>")
def remove_app_from_category(category_name: str, app_name: str):
    mapping = m.AppCategory.query.filter_by(app_name=app_name, category_name=category_name).first()
    if not mapping:
        abort(404, "App not found in specified category")
    
    db.session.delete(mapping)
    db.session.commit()
    
    return {"message": f"App '{app_name}' removed from category '{category_name}'"}


@app.get("/stats/summary")
def summary_stats():
    try:
        days = int(request.args.get("days", 30))
    except (ValueError, TypeError):
        abort(400, "Invalid days parameter")
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)

    if not table_exists('daily_category_usage'):
        abort(503, "Aggregated data not available. Please run the processor.")

    try:
        total_time_res = db.session.query(func.sum(m.DailyCategoryUsage.total_seconds)).filter(
            m.DailyCategoryUsage.date.between(start_date, end_date),
            m.DailyCategoryUsage.device_type == 'desktop'
        ).scalar()
        total_time = total_time_res or 0

        avg_daily = total_time / days if days else 0

        productive_row = db.session.query(
            m.DailyCategoryUsage.date,
            m.DailyCategoryUsage.total_seconds
        ).filter(
            m.DailyCategoryUsage.date.between(start_date, end_date),
            m.DailyCategoryUsage.device_type == 'desktop',
            m.DailyCategoryUsage.category == 'Work'
        ).order_by(m.DailyCategoryUsage.total_seconds.desc()).first()

        unique_apps_res = db.session.query(func.count(func.distinct(m.DailyUsage.app_name))).filter(
            m.DailyUsage.date.between(start_date, end_date),
            m.DailyUsage.device_type == 'desktop'
        ).scalar()
        unique_apps = unique_apps_res or 0

    except Exception as e:
        logger.exception("Summary stats query failed")
        abort(500, f"Database error: {e}")

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
        "fallback": False
    }


@app.get("/debug/overview-check")
def debug_overview():
    date_param = request.args.get("date") or datetime.utcnow().strftime('%Y-%m-%d')
    issues: List[str] = []
    tables: Dict[str, bool] = {}
    for t in ["events", "hourly_usage", "daily_usage", "daily_category_usage"]:
        tables[t] = table_exists(t)
        if not tables[t]:
            issues.append(f"Missing table: {t}")
    details: Dict[str, Any] = {}
    try:
        details['daily_category_usage'] = db.session.query(func.count(m.DailyCategoryUsage.id)).filter(m.DailyCategoryUsage.date == date_param).scalar() if tables['daily_category_usage'] else None
    except Exception as e:
        issues.append(f"daily_category_usage query error: {e}")
    try:
        details['daily_usage_rows'] = db.session.query(func.count(m.DailyUsage.id)).filter(m.DailyUsage.date == date_param).scalar() if tables['daily_usage'] else None
    except Exception as e:
        issues.append(f"daily_usage query error: {e}")
    try:
        details['events_today'] = db.session.query(func.count(m.Event.id)).filter(func.date(m.Event.timestamp) == date_param).scalar() if tables['events'] else None
    except Exception as e:
        issues.append(f"events query error: {e}")
    return {
        "date": date_param,
        "tables": tables,
        "details": details,
        "issues": issues,
        "hint": "If aggregated tables are missing run processor. If events is 0 ensure collector running."}


@app.get("/diagnostics/status")
def diagnostics_status():
    warnings: List[str] = []

    def one(query):
        try:
            return query.scalar()
        except Exception:
            return None

    last_event_ts = one(db.session.query(func.max(m.Event.timestamp)).filter(m.Event.device_type == 'desktop'))
    events_today = one(db.session.query(func.count(m.Event.id)).filter(func.date(m.Event.timestamp) == date.today(), m.Event.device_type == 'desktop')) or 0
    distinct_apps = one(db.session.query(func.count(func.distinct(m.Event.app_name))).filter(m.Event.device_type == 'desktop')) or 0
    last_hourly_created = one(db.session.query(func.max(m.HourlyUsage.created_at)).filter(m.HourlyUsage.device_type == 'desktop'))
    last_daily_created = one(db.session.query(func.max(m.DailyUsage.created_at)).filter(m.DailyUsage.device_type == 'desktop'))

    db_path = Path(DB_PATH)
    db_exists = db_path.exists()
    db_size = db_path.stat().st_size if db_exists else 0
    uptime_seconds = (datetime.now(timezone.utc) - APP_START_TIME).total_seconds()

    collector_status, last_event_age_seconds = check_service_status(last_event_ts, 60, 300, "Collector")
    processor_status, last_hourly_age_seconds = check_service_status(last_hourly_created, 600, 1800, "Processor (hourly)")
    daily_status, _ = check_service_status(last_daily_created, 86400, 86400 * 2, "Processor (daily)", is_daily=True)

    uncategorized_apps = db.session.query(m.DailyUsage.app_name).filter(
        (m.DailyUsage.category == None) | (m.DailyUsage.category == ''),
        m.DailyUsage.device_type == 'desktop'
    ).distinct().limit(30).all()
    uncategorized = [r[0] for r in uncategorized_apps]

    total_categories = one(db.session.query(func.count(func.distinct(m.AppCategory.category)))) or 0
    apps_with_category = one(db.session.query(func.count(m.AppCategory.id))) or 0

    components = [
        {"name": "backend", "status": "ok", "details": {"uptime_seconds": round(uptime_seconds, 2), "version": app.config["API_VERSION"]}},
        {"name": "database", "status": "ok" if db_exists else "missing", "details": {
            "path": str(db_path), "exists": db_exists, "size_bytes": db_size,
            "last_event_timestamp": last_event_ts.isoformat() if last_event_ts else None,
            "events_today": events_today, "distinct_apps": distinct_apps
        }},
        {"name": "collector", "status": collector_status, "details": {"last_event_age_seconds": last_event_age_seconds, "last_event_timestamp": last_event_ts.isoformat() if last_event_ts else None}},
        {"name": "processor_hourly", "status": processor_status, "details": {"last_hourly_created": last_hourly_created.isoformat() if last_hourly_created else None, "age_seconds": last_hourly_age_seconds}},
        {"name": "processor_daily", "status": daily_status, "details": {"last_daily_created": last_daily_created.isoformat() if last_daily_created else None}},
        {"name": "categories", "status": "ok", "details": {
            "total_categories": total_categories, "mapped_apps": apps_with_category,
            "uncategorized_sample": uncategorized
        }}
    ]

    for comp in components:
        if comp['status'] != 'ok':
            warnings.append(f"Component '{comp['name']}' has status: {comp['status']}")
    if uncategorized:
        warnings.append("Uncategorized apps present")

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": components,
        "warnings": warnings
    }


def check_service_status(last_timestamp, ok_threshold, stale_threshold, service_name, is_daily=False):
    if not last_timestamp:
        return "no-data", None

    try:
        age_seconds = (datetime.now(timezone.utc) - last_timestamp).total_seconds()
        if is_daily:
            if last_timestamp.date() == datetime.now(timezone.utc).date():
                return "ok", age_seconds
            return "stale", age_seconds

        if age_seconds < ok_threshold:
            return "ok", age_seconds
        elif age_seconds < stale_threshold:
            return "stale", age_seconds
        return "offline", age_seconds
    except (ValueError, TypeError):
        return "error", None


if __name__ == "__main__":
    # Dev server (for local debugging). Production uses gunicorn via start script.
    app.run(host="0.0.0.0", port=8847, debug=True)
