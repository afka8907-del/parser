"""
SQLAlchemy database models for the iPhone market data.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class ListingStatus(str, PyEnum):
    """Listing status enumeration."""
    ACTIVE = "active"
    SOLD = "sold"
    EXPIRED = "expired"
    DELETED = "deleted"
    RESERVED = "reserved"


class Condition(str, PyEnum):
    """Phone condition enumeration."""
    NEW = "new"
    LIKE_NEW = "like_new"
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    BROKEN = "broken"


class Seller(Base):
    """Seller information model."""
    
    __tablename__ = "sellers"
    
    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(100), unique=True, index=True)
    name = Column(String(200), nullable=False)
    phone = Column(String(50), nullable=True)
    email = Column(String(200), nullable=True)
    location = Column(String(200), nullable=True)
    
    # Reputation metrics
    total_listings = Column(Integer, default=0)
    active_listings = Column(Integer, default=0)
    sold_listings = Column(Integer, default=0)
    reputation_score = Column(Numeric(3, 2), default=5.00)
    is_trusted = Column(Boolean, default=False)
    is_blacklisted = Column(Boolean, default=False)
    is_reseller = Column(Boolean, default=False)
    
    # Metadata
    first_seen = Column(DateTime(timezone=True), default=datetime.utcnow)
    last_seen = Column(DateTime(timezone=True))
    
    # Relationships
    listings = relationship("Listing", back_populates="seller")


class Listing(Base):
    """iPhone listing model."""
    
    __tablename__ = "listings"
    
    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(100), unique=True, index=True, nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    
    # iPhone details
    model = Column(String(100), nullable=False, index=True)
    storage_gb = Column(Integer, nullable=True, index=True)
    color = Column(String(50), nullable=True)
    battery_health = Column(Integer, nullable=True)  # Percentage
    condition = Column(Enum(Condition), nullable=True)
    
    # Price information
    price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), default="MDL")
    original_price = Column(Numeric(10, 2), nullable=True)
    
    # Status
    status = Column(Enum(ListingStatus), default=ListingStatus.ACTIVE, index=True)
    
    # URLs
    listing_url = Column(String(500), nullable=False)
    images = Column(JSON, default=list)
    
    # Location & Time
    location = Column(String(200), nullable=True)
    posted_at = Column(DateTime(timezone=True), nullable=True)
    scraped_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    last_checked = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Seller relationship
    seller_id = Column(Integer, ForeignKey("sellers.id"), nullable=True)
    seller = relationship("Seller", back_populates="listings")
    
    # Analysis results
    is_underpriced = Column(Boolean, default=False)
    is_urgent = Column(Boolean, default=False)
    is_repost = Column(Boolean, default=False)
    is_suspicious = Column(Boolean, default=False)
    
    # Risk and opportunity scoring
    profit_score = Column(Integer, default=0)  # 0-100
    risk_score = Column(Integer, default=50)  # 0-100 (lower is better)
    resale_speed_score = Column(Integer, default=50)  # 0-100
    demand_score = Column(Integer, default=50)  # 0-100
    overall_score = Column(Integer, default=0)  # Combined score
    
    # Issue detection
    face_id_issue = Column(Boolean, default=False)
    icloud_locked = Column(Boolean, default=False)
    broken_display = Column(Boolean, default=False)
    replaced_parts = Column(Boolean, default=False)
    battery_replaced = Column(Boolean, default=False)
    is_refurbished = Column(Boolean, default=False)
    is_fake = Column(Boolean, default=False)
    
    # AI Analysis
    ai_analysis = Column(JSON, default=dict)
    estimated_resale_price = Column(Numeric(10, 2), nullable=True)
    estimated_profit = Column(Numeric(10, 2), nullable=True)
    estimated_repair_cost = Column(Numeric(10, 2), default=0)
    negotiation_probability = Column(Numeric(3, 2), nullable=True)
    
    # Relationships
    price_history = relationship("PriceHistory", back_populates="listing", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="listing")
    
    __table_args__ = (
        UniqueConstraint("external_id", name="uq_listing_external_id"),
    )


class PriceHistory(Base):
    """Price history tracking model."""
    
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=False)
    old_price = Column(Numeric(10, 2), nullable=False)
    new_price = Column(Numeric(10, 2), nullable=False)
    changed_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    listing = relationship("Listing", back_populates="price_history")


class MarketAnalysis(Base):
    """Market analysis snapshot model."""
    
    __tablename__ = "market_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    model = Column(String(100), nullable=False, index=True)
    storage_gb = Column(Integer, nullable=True, index=True)
    
    # Price statistics
    avg_price = Column(Numeric(10, 2), nullable=False)
    median_price = Column(Numeric(10, 2), nullable=False)
    min_price = Column(Numeric(10, 2), nullable=False)
    max_price = Column(Numeric(10, 2), nullable=False)
    std_deviation = Column(Numeric(10, 2), nullable=True)
    
    # Market metrics
    total_listings = Column(Integer, default=0)
    new_listings_24h = Column(Integer, default=0)
    sold_listings_24h = Column(Integer, default=0)
    avg_days_on_market = Column(Numeric(4, 1), default=0)
    
    # Analysis timestamp
    analyzed_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class Alert(Base):
    """Alert/notification model."""
    
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=False)
    alert_type = Column(String(50), nullable=False)  # "underpriced", "urgent", "price_drop", etc.
    message = Column(Text, nullable=True)
    profit_estimate = Column(Numeric(10, 2), nullable=True)
    sent_to_telegram = Column(Boolean, default=False)
    telegram_message_id = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    listing = relationship("Listing", back_populates="alerts")


class Watchlist(Base):
    """User watchlist model."""
    
    __tablename__ = "watchlists"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    model = Column(String(100), nullable=True)
    storage_gb = Column(Integer, nullable=True)
    min_price = Column(Numeric(10, 2), nullable=True)
    max_price = Column(Numeric(10, 2), nullable=True)
    condition = Column(Enum(Condition), nullable=True)
    battery_min = Column(Integer, nullable=True)
    
    # Alert preferences
    notify_on_deal = Column(Boolean, default=True)
    notify_on_price_drop = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class Blacklist(Base):
    """Blacklist for sellers or listings."""
    
    __tablename__ = "blacklist"
    
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(20), nullable=False)  # "seller", "listing", "phone"
    value = Column(String(200), nullable=False)  # seller_id, listing_id, or phone number
    reason = Column(Text, nullable=True)
    added_by = Column(Integer, nullable=True)  # user_id
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("type", "value", name="uq_blacklist_type_value"),
    )


class Inventory(Base):
    """Reseller inventory tracking."""
    
    __tablename__ = "inventory"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    
    # Item details
    model = Column(String(100), nullable=False)
    storage_gb = Column(Integer, nullable=True)
    color = Column(String(50), nullable=True)
    battery_health = Column(Integer, nullable=True)
    condition = Column(Enum(Condition), nullable=True)
    
    # Purchase details
    purchase_price = Column(Numeric(10, 2), nullable=False)
    purchase_date = Column(DateTime(timezone=True), default=datetime.utcnow)
    repair_cost = Column(Numeric(10, 2), default=0)
    other_costs = Column(Numeric(10, 2), default=0)
    total_investment = Column(Numeric(10, 2), nullable=True)
    
    # Sale details
    listed_price = Column(Numeric(10, 2), nullable=True)
    sold_price = Column(Numeric(10, 2), nullable=True)
    sold_date = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    status = Column(String(20), default="in_stock")  # in_stock, listed, sold
    profit = Column(Numeric(10, 2), nullable=True)
    roi_percent = Column(Numeric(5, 2), nullable=True)
    
    # Source
    source_listing_id = Column(Integer, ForeignKey("listings.id"), nullable=True)
    notes = Column(Text, nullable=True)


class MarketReport(Base):
    """Automated market reports."""
    
    __tablename__ = "market_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    report_type = Column(String(50), nullable=False)  # daily, weekly, monthly
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    
    # Summary statistics
    total_listings = Column(Integer, default=0)
    new_listings = Column(Integer, default=0)
    sold_listings = Column(Integer, default=0)
    avg_price_change = Column(Numeric(5, 2), default=0)
    top_models = Column(JSON, default=list)
    hottest_deals = Column(JSON, default=list)
    
    # Generated content
    report_content = Column(Text, nullable=True)
    sent_to_telegram = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
