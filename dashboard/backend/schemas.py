"""
Pydantic schemas for API responses.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class ListingResponse(BaseModel):
    """Listing response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    external_id: str
    title: str
    model: str
    storage_gb: Optional[int]
    color: Optional[str]
    battery_health: Optional[int]
    condition: Optional[str]
    price: float
    currency: str
    status: str
    listing_url: str
    images: List[str]
    location: Optional[str]
    posted_at: Optional[datetime]
    scraped_at: datetime
    is_underpriced: bool
    estimated_resale_price: Optional[float]
    estimated_profit: Optional[float]
    profit_score: int
    risk_score: int
    face_id_issue: bool
    icloud_locked: bool
    broken_display: bool
    replaced_parts: bool
    is_suspicious: bool
    
    @classmethod
    def from_orm(cls, obj):
        """Create from ORM object."""
        data = {
            "id": obj.id,
            "external_id": obj.external_id,
            "title": obj.title,
            "model": obj.model,
            "storage_gb": obj.storage_gb,
            "color": obj.color,
            "battery_health": obj.battery_health,
            "condition": obj.condition.value if obj.condition else None,
            "price": float(obj.price),
            "currency": obj.currency,
            "status": obj.status.value,
            "listing_url": obj.listing_url,
            "images": obj.images or [],
            "location": obj.location,
            "posted_at": obj.posted_at,
            "scraped_at": obj.scraped_at,
            "is_underpriced": obj.is_underpriced,
            "estimated_resale_price": float(obj.estimated_resale_price) if obj.estimated_resale_price else None,
            "estimated_profit": float(obj.estimated_profit) if obj.estimated_profit else None,
            "profit_score": obj.profit_score,
            "risk_score": obj.risk_score,
            "face_id_issue": obj.face_id_issue,
            "icloud_locked": obj.icloud_locked,
            "broken_display": obj.broken_display,
            "replaced_parts": obj.replaced_parts,
            "is_suspicious": obj.is_suspicious,
        }
        return cls(**data)


class StatsResponse(BaseModel):
    """Statistics response schema."""
    total_active_listings: int
    total_all_time_listings: int
    new_listings_today: int
    total_profitable_deals: int
    average_price: float
    active_sellers: int


class MarketStatsResponse(BaseModel):
    """Market statistics response schema."""
    model: str
    storage_gb: Optional[int]
    avg_price: float
    median_price: float
    min_price: float
    max_price: float
    total_listings: int


class SellerResponse(BaseModel):
    """Seller response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    location: Optional[str]
    total_listings: int
    active_listings: int
    sold_listings: int
    reputation_score: float
    is_trusted: bool
    is_blacklisted: bool
    is_reseller: bool
    first_seen: datetime
    last_seen: Optional[datetime]
    
    @classmethod
    def from_orm(cls, obj):
        """Create from ORM object."""
        data = {
            "id": obj.id,
            "name": obj.name,
            "location": obj.location,
            "total_listings": obj.total_listings,
            "active_listings": obj.active_listings,
            "sold_listings": obj.sold_listings,
            "reputation_score": float(obj.reputation_score),
            "is_trusted": obj.is_trusted,
            "is_blacklisted": obj.is_blacklisted,
            "is_reseller": obj.is_reseller,
            "first_seen": obj.first_seen,
            "last_seen": obj.last_seen,
        }
        return cls(**data)


class AlertResponse(BaseModel):
    """Alert response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    listing_id: int
    alert_type: str
    message: str
    profit_estimate: Optional[float]
    sent_to_telegram: bool
    created_at: datetime
    
    @classmethod
    def from_orm(cls, obj):
        """Create from ORM object."""
        data = {
            "id": obj.id,
            "listing_id": obj.listing_id,
            "alert_type": obj.alert_type,
            "message": obj.message,
            "profit_estimate": float(obj.profit_estimate) if obj.profit_estimate else None,
            "sent_to_telegram": obj.sent_to_telegram,
            "created_at": obj.created_at,
        }
        return cls(**data)


class DealResponse(BaseModel):
    """Deal response schema."""
    listing: ListingResponse
    score: int
    profit_score: int
    risk_score: int
    resale_speed_score: int
    demand_score: int
    current_price: float
    market_median: float
    market_avg: float
    estimated_resale: float
    estimated_profit: float
    profit_margin: float
    is_profitable: bool
    recommendation: str
