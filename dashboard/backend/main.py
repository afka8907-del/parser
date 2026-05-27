"""
FastAPI backend for iPhone Reseller Intelligence dashboard.
"""

from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import (
    Alert,
    AsyncSessionLocal,
    Listing,
    ListingStatus,
    MarketAnalysis,
    Seller,
    get_db,
    init_db,
)
from dashboard.backend.schemas import (
    AlertResponse,
    DealResponse,
    ListingResponse,
    MarketStatsResponse,
    SellerResponse,
    StatsResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    # Startup
    await init_db()
    yield
    # Shutdown
    pass


app = FastAPI(
    title="iPhone Reseller Intelligence API",
    description="API for iPhone market analysis and deal detection",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "iPhone Reseller Intelligence API",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Get overall statistics."""
    # Total active listings
    active_result = await db.execute(
        select(func.count(Listing.id)).where(Listing.status == ListingStatus.ACTIVE)
    )
    total_active = active_result.scalar()
    
    # Total all time
    all_result = await db.execute(select(func.count(Listing.id)))
    total_all = all_result.scalar()
    
    # Today's new listings
    from datetime import datetime, timedelta
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    
    today_result = await db.execute(
        select(func.count(Listing.id)).where(Listing.scraped_at >= today_start)
    )
    today_count = today_result.scalar()
    
    # Total deals (underpriced)
    deals_result = await db.execute(
        select(func.count(Listing.id)).where(Listing.is_underpriced == True)
    )
    total_deals = deals_result.scalar()
    
    # Average price
    avg_result = await db.execute(
        select(func.avg(Listing.price)).where(Listing.status == ListingStatus.ACTIVE)
    )
    avg_price = avg_result.scalar() or 0
    
    # Active sellers
    sellers_result = await db.execute(
        select(func.count(Seller.id)).where(Seller.active_listings > 0)
    )
    active_sellers = sellers_result.scalar()
    
    return StatsResponse(
        total_active_listings=total_active,
        total_all_time_listings=total_all,
        new_listings_today=today_count,
        total_profitable_deals=total_deals,
        average_price=round(float(avg_price), 2),
        active_sellers=active_sellers,
    )


@app.get("/api/listings", response_model=List[ListingResponse])
async def get_listings(
    status: Optional[str] = Query(None, description="Filter by status"),
    model: Optional[str] = Query(None, description="Filter by model"),
    min_price: Optional[float] = Query(None, description="Minimum price"),
    max_price: Optional[float] = Query(None, description="Maximum price"),
    is_underpriced: Optional[bool] = Query(None, description="Only underpriced"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get listings with filters."""
    query = select(Listing)
    
    if status:
        query = query.where(Listing.status == status)
    if model:
        query = query.where(Listing.model.ilike(f"%{model}%"))
    if min_price:
        query = query.where(Listing.price >= min_price)
    if max_price:
        query = query.where(Listing.price <= max_price)
    if is_underpriced is not None:
        query = query.where(Listing.is_underpriced == is_underpriced)
    
    query = query.order_by(Listing.scraped_at.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    listings = result.scalars().all()
    
    return [ListingResponse.from_orm(l) for l in listings]


@app.get("/api/listings/{listing_id}", response_model=ListingResponse)
async def get_listing(listing_id: int, db: AsyncSession = Depends(get_db)):
    """Get specific listing."""
    result = await db.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalar_one_or_none()
    
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    return ListingResponse.from_orm(listing)


@app.get("/api/deals", response_model=List[DealResponse])
async def get_deals(
    min_profit: Optional[float] = Query(1000, description="Minimum profit"),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get top deals."""
    from analyzer.deal_detector import DealDetector
    
    detector = DealDetector()
    deals = await detector.get_top_deals(limit=limit)
    
    return [DealResponse(**deal) for deal in deals]


@app.get("/api/market-stats", response_model=List[MarketStatsResponse])
async def get_market_stats(db: AsyncSession = Depends(get_db)):
    """Get market analysis statistics."""
    from analyzer.market_analyzer import MarketAnalyzer
    
    analyzer = MarketAnalyzer()
    stats = await analyzer.analyze_market()
    
    return [
        MarketStatsResponse(
            model=s.model,
            storage_gb=s.storage_gb,
            avg_price=s.avg_price,
            median_price=s.median_price,
            min_price=s.min_price,
            max_price=s.max_price,
            total_listings=s.total_listings,
        )
        for s in stats
    ]


@app.get("/api/sellers", response_model=List[SellerResponse])
async def get_sellers(
    is_trusted: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get sellers."""
    query = select(Seller)
    
    if is_trusted is not None:
        query = query.where(Seller.is_trusted == is_trusted)
    
    query = query.order_by(Seller.total_listings.desc()).limit(limit)
    
    result = await db.execute(query)
    sellers = result.scalars().all()
    
    return [SellerResponse.from_orm(s) for s in sellers]


@app.get("/api/sellers/{seller_id}", response_model=SellerResponse)
async def get_seller(seller_id: int, db: AsyncSession = Depends(get_db)):
    """Get specific seller."""
    result = await db.execute(select(Seller).where(Seller.id == seller_id))
    seller = result.scalar_one_or_none()
    
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    
    return SellerResponse.from_orm(seller)


@app.get("/api/alerts", response_model=List[AlertResponse])
async def get_alerts(
    alert_type: Optional[str] = Query(None),
    sent_only: Optional[bool] = Query(False),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get alerts."""
    query = select(Alert)
    
    if alert_type:
        query = query.where(Alert.alert_type == alert_type)
    if sent_only:
        query = query.where(Alert.sent_to_telegram == True)
    
    query = query.order_by(Alert.created_at.desc()).limit(limit)
    
    result = await db.execute(query)
    alerts = result.scalars().all()
    
    return [AlertResponse.from_orm(a) for a in alerts]


@app.get("/api/models")
async def get_models(db: AsyncSession = Depends(get_db)):
    """Get all unique iPhone models."""
    result = await db.execute(
        select(Listing.model, func.count(Listing.id).label("count"))
        .where(Listing.status == ListingStatus.ACTIVE)
        .group_by(Listing.model)
        .order_by(func.count(Listing.id).desc())
    )
    models = result.all()
    
    return [{"model": m[0], "count": m[1]} for m in models]


@app.get("/api/trends")
async def get_trends(days: int = Query(7, ge=1, le=30), db: AsyncSession = Depends(get_db)):
    """Get market trends."""
    from analyzer.market_analyzer import MarketAnalyzer
    
    analyzer = MarketAnalyzer()
    trends = await analyzer.get_market_trends(days=days)
    
    return trends


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "dashboard.backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug,
    )
