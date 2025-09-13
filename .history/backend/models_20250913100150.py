"""SQLAlchemy ORM models mapping existing schema"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Date, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime,timezone
from .database import db

class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True, index=True)
    timestamp = db.Column(db.DateTime, nullable=False)
    device_type = db.Column(db.String, nullable=False, default='desktop')
    app_name = db.Column(db.String, nullable=False)
    window_title = db.Column(db.Text)
    website_url = db.Column(db.String)
    website_title = db.Column(db.String)
    process_name = db.Column(db.String)
    duration_seconds = db.Column(db.Integer, nullable=False, default=10)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

class HourlyUsage(db.Model):
    __tablename__ = 'hourly_usage'
    id = db.Column(db.Integer, primary_key=True, index=True)
    date = db.Column(db.Date, nullable=False)
    hour = db.Column(db.Integer, nullable=False)
    device_type = db.Column(db.String, nullable=False, default='desktop')
    app_name = db.Column(db.String, nullable=False)
    website_url = db.Column(db.String)
    category = db.Column(db.String)
    total_seconds = db.Column(db.Integer, nullable=False, default=0)
    event_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    __table_args__ = (db.UniqueConstraint('date','hour','device_type','app_name','website_url', name='uq_hourly'),)

class DailyUsage(db.Model):
    __tablename__ = 'daily_usage'
    id = db.Column(db.Integer, primary_key=True, index=True)
    date = db.Column(db.Date, nullable=False)
    device_type = db.Column(db.String, nullable=False, default='desktop')
    app_name = db.Column(db.String, nullable=False)
    website_url = db.Column(db.String)
    category = db.Column(db.String)
    total_seconds = db.Column(db.Integer, nullable=False, default=0)
    event_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    __table_args__ = (db.UniqueConstraint('date','device_type','app_name','website_url', name='uq_daily'),)

class DailyCategoryUsage(db.Model):
    __tablename__ = 'daily_category_usage'
    id = db.Column(db.Integer, primary_key=True, index=True)
    date = db.Column(db.Date, nullable=False)
    device_type = db.Column(db.String, nullable=False, default='desktop')
    category = db.Column(db.String, nullable=False)
    total_seconds = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    __table_args__ = (db.UniqueConstraint('date','device_type','category', name='uq_daily_cat'),)

class AppCategory(db.Model):
    __tablename__ = 'app_categories'
    id = db.Column(db.Integer, primary_key=True, index=True)
    app_name = db.Column(db.String, nullable=False, unique=True)
    category = db.Column(db.String, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
