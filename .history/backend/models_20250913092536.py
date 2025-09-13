"""SQLAlchemy ORM models mapping existing schema"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Date, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Event(Base):
    __tablename__ = 'events'
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False)
    device_type = Column(String, nullable=False, default='desktop')
    app_name = Column(String, nullable=False)
    window_title = Column(Text)
    website_url = Column(String)
    website_title = Column(String)
    process_name = Column(String)
    duration_seconds = Column(Integer, nullable=False, default=10)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

class HourlyUsage(Base):
    __tablename__ = 'hourly_usage'
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    hour = Column(Integer, nullable=False)
    device_type = Column(String, nullable=False, default='desktop')
    app_name = Column(String, nullable=False)
    website_url = Column(String)
    category = Column(String)
    total_seconds = Column(Integer, nullable=False, default=0)
    event_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    __table_args__ = (UniqueConstraint('date','hour','device_type','app_name','website_url', name='uq_hourly'),)

class DailyUsage(Base):
    __tablename__ = 'daily_usage'
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    device_type = Column(String, nullable=False, default='desktop')
    app_name = Column(String, nullable=False)
    website_url = Column(String)
    category = Column(String)
    total_seconds = Column(Integer, nullable=False, default=0)
    event_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.now(timezone.utc)
    __table_args__ = (UniqueConstraint('date','device_type','app_name','website_url', name='uq_daily'),)

class DailyCategoryUsage(Base):
    __tablename__ = 'daily_category_usage'
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    device_type = Column(String, nullable=False, default='desktop')
    category = Column(String, nullable=False)
    total_seconds = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    __table_args__ = (UniqueConstraint('date','device_type','category', name='uq_daily_cat'),)

class AppCategory(Base):
    __tablename__ = 'app_categories'
    id = Column(Integer, primary_key=True, index=True)
    app_name = Column(String, nullable=False, unique=True)
    category = Column(String, nullable=False)
    updated_at = Column(DateTime, default=datetime.now(timezone.utc))
