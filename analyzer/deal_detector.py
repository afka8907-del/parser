"""
Deal detection system for finding profitable opportunities.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from analyzer.market_analyzer import MarketAnalyzer
from database import Alert, AsyncSessionLocal, Listing, ListingStatus, Watchlist
from config import settings


class DealDetector:
    """Detect and alert on profitable deals."""
    
    def __init__(self):
        self.market_analyzer = MarketAnalyzer()
    
    async def detect_new_deals(self) -> List[Dict]:
        """
        Detect new profitable deals since last run.
        
        Returns:
            List of new deals
        """
        async with AsyncSessionLocal() as session:
            # Get recently added listings (last 30 minutes)
            recent_time = datetime.utcnow() - timedelta(minutes=30)
            
            result = await session.execute(
                select(Listing)
                .where(Listing.scraped_at >= recent_time)
                .where(Listing.status == ListingStatus.ACTIVE)
                .where(Listing.is_underpriced == False)
            )
            new_listings = result.scalars().all()
            
            deals = []
            for listing in new_listings:
                deal = await self._analyze_deal(session, listing)
                if deal and deal.get("is_profitable"):
                    deals.append(deal)
                    
                    # Mark as underpriced
                    listing.is_underpriced = True
                    listing.estimated_resale_price = deal["estimated_resale"]
                    listing.estimated_profit = deal["profit"]
                    listing.profit_score = deal["score"]
            
            await session.commit()
            
            return deals
    
    async def detect_price_drops(self) -> List[Dict]:
        """
        Detect significant price drops.
        
        Returns:
            List of listings with price drops
        """
        async with AsyncSessionLocal() as session:
            # Get listings with price history in last 24 hours
            yesterday = datetime.utcnow() - timedelta(hours=24)
            
            from database import PriceHistory
            
            result = await session.execute(
                select(PriceHistory)
                .where(PriceHistory.changed_at >= yesterday)
                .order_by(PriceHistory.changed_at.desc())
            )
            price_changes = result.scalars().all()
            
            deals = []
            seen_listings = set()
            
            for change in price_changes:
                if change.listing_id in seen_listings:
                    continue
                seen_listings.add(change.listing_id)
                
                # Get listing
                listing_result = await session.execute(
                    select(Listing).where(Listing.id == change.listing_id)
                )
                listing = listing_result.scalar_one_or_none()
                
                if not listing or listing.status != ListingStatus.ACTIVE:
                    continue
                
                # Calculate drop percentage
                old_price = float(change.old_price)
                new_price = float(change.new_price)
                
                if old_price <= 0:
                    continue
                
                drop_percent = ((old_price - new_price) / old_price) * 100
                
                # Only alert on significant drops (>10%)
                if drop_percent >= 10:
                    deal = await self._analyze_deal(session, listing)
                    if deal:
                        deal["price_drop"] = {
                            "old_price": old_price,
                            "new_price": new_price,
                            "drop_percent": round(drop_percent, 1),
                        }
                        deal["alert_type"] = "price_drop"
                        deals.append(deal)
            
            return deals
    
    async def detect_urgent_sales(self) -> List[Dict]:
        """
        Detect urgent sales and motivated sellers.
        
        Returns:
            List of urgent sale opportunities
        """
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Listing)
                .where(Listing.status == ListingStatus.ACTIVE)
                .where(Listing.is_urgent == True)
                .where(Listing.scraped_at >= datetime.utcnow() - timedelta(hours=24))
            )
            urgent_listings = result.scalars().all()
            
            deals = []
            for listing in urgent_listings:
                deal = await self._analyze_deal(session, listing)
                if deal:
                    deal["alert_type"] = "urgent_sale"
                    deal["urgency_indicators"] = listing.ai_analysis.get("urgency_reasons", [])
                    deals.append(deal)
            
            return deals
    
    async def check_watchlist_matches(self, user_id: int) -> List[Dict]:
        """
        Check for watchlist matches.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            List of matching deals
        """
        async with AsyncSessionLocal() as session:
            # Get user watchlist
            result = await session.execute(
                select(Watchlist).where(Watchlist.user_id == user_id)
            )
            watches = result.scalars().all()
            
            if not watches:
                return []
            
            matches = []
            
            for watch in watches:
                # Build query
                query = select(Listing).where(Listing.status == ListingStatus.ACTIVE)
                
                if watch.model:
                    query = query.where(Listing.model.ilike(f"%{watch.model}%"))
                
                if watch.storage_gb:
                    query = query.where(Listing.storage_gb == watch.storage_gb)
                
                if watch.min_price:
                    query = query.where(Listing.price >= watch.min_price)
                
                if watch.max_price:
                    query = query.where(Listing.price <= watch.max_price)
                
                if watch.condition:
                    query = query.where(Listing.condition == watch.condition)
                
                if watch.battery_min:
                    query = query.where(Listing.battery_health >= watch.battery_min)
                
                # Only recent listings
                recent = datetime.utcnow() - timedelta(hours=24)
                query = query.where(Listing.scraped_at >= recent)
                
                result = await session.execute(query)
                listings = result.scalars().all()
                
                for listing in listings:
                    deal = await self._analyze_deal(session, listing)
                    if deal and deal.get("is_profitable"):
                        deal["watch_id"] = watch.id
                        deal["watch_criteria"] = {
                            "model": watch.model,
                            "max_price": watch.max_price,
                        }
                        matches.append(deal)
            
            return matches
    
    async def _analyze_deal(self, session: AsyncSession, listing: Listing) -> Optional[Dict]:
        """Analyze a single listing for deal potential."""
        try:
            # Get market stats for this model
            from database import MarketAnalysis
            
            result = await session.execute(
                select(MarketAnalysis)
                .where(MarketAnalysis.model == listing.model)
                .where(MarketAnalysis.storage_gb == listing.storage_gb)
                .order_by(MarketAnalysis.analyzed_at.desc())
                .limit(1)
            )
            market_stat = result.scalar_one_or_none()
            
            if not market_stat:
                return None
            
            from analyzer.market_analyzer import ModelStats
            
            stats = ModelStats(
                model=market_stat.model,
                storage_gb=market_stat.storage_gb,
                avg_price=float(market_stat.avg_price),
                median_price=float(market_stat.median_price),
                min_price=float(market_stat.min_price),
                max_price=float(market_stat.max_price),
                std_deviation=float(market_stat.std_deviation or 0),
                total_listings=market_stat.total_listings,
                price_range_10_90=(0, 0),  # Not needed for deal detection
            )
            
            # Calculate deal score
            score_result = await self.market_analyzer.score_deal(listing, stats)
            
            current_price = float(listing.price)
            
            # Determine if profitable
            min_profit = settings.min_profit_threshold
            is_profitable = (
                score_result.estimated_profit >= min_profit and
                score_result.overall_score >= 50 and
                score_result.risk_score <= settings.risk_score_threshold
            )
            
            return {
                "listing": listing,
                "score": score_result.overall_score,
                "profit_score": score_result.profit_score,
                "risk_score": score_result.risk_score,
                "resale_speed_score": score_result.resale_speed_score,
                "demand_score": score_result.demand_score,
                "current_price": current_price,
                "market_median": stats.median_price,
                "market_avg": stats.avg_price,
                "estimated_resale": score_result.estimated_resale_price,
                "estimated_profit": score_result.estimated_profit,
                "profit_margin": round(
                    (score_result.estimated_profit / current_price * 100), 1
                ) if current_price > 0 else 0,
                "is_profitable": is_profitable,
                "recommendation": score_result.recommendation,
                "alert_type": "new_deal",
            }
            
        except Exception as e:
            logger.error(f"Error analyzing deal for listing {listing.id}: {e}")
            return None
    
    async def get_top_deals(self, limit: int = 10) -> List[Dict]:
        """Get top deals overall."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Listing)
                .where(Listing.status == ListingStatus.ACTIVE)
                .limit(200)
            )
            listings = result.scalars().all()

            deals = []
            for listing in listings:
                deal = await self._analyze_deal(session, listing)
                if deal and deal.get("is_profitable"):
                    deals.append(deal)

            deals.sort(key=lambda d: d["estimated_profit"], reverse=True)
            return deals[:limit]
    
    async def get_cheapest_listings(self, model: str = None, limit: int = 10) -> List[Listing]:
        """Get cheapest listings, optionally filtered by model."""
        async with AsyncSessionLocal() as session:
            query = select(Listing).where(Listing.status == ListingStatus.ACTIVE)
            
            if model:
                query = query.where(Listing.model == model)
            
            query = query.order_by(Listing.price.asc()).limit(limit)
            
            result = await session.execute(query)
            return result.scalars().all()
