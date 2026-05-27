"""
Market analysis engine for iPhone listings.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional

import numpy as np
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal, Listing, ListingStatus, MarketAnalysis
from utils.helpers import calculate_profit_margin


@dataclass
class ModelStats:
    """Statistics for a specific iPhone model."""
    model: str
    storage_gb: Optional[int]
    avg_price: float
    median_price: float
    min_price: float
    max_price: float
    std_deviation: float
    total_listings: int
    price_range_10_90: tuple  # 10th and 90th percentile


@dataclass
class DealScore:
    """Deal scoring result."""
    listing_id: int
    profit_score: int  # 0-100
    risk_score: int  # 0-100 (lower is better)
    resale_speed_score: int  # 0-100
    demand_score: int  # 0-100
    overall_score: int  # 0-100
    estimated_resale_price: float
    estimated_profit: float
    recommendation: str


class MarketAnalyzer:
    """Analyzer for iPhone market data."""
    
    # Resale value multipliers based on condition and market
    RESALE_MULTIPLIERS = {
        "new": 1.15,
        "like_new": 1.10,
        "excellent": 1.05,
        "good": 1.00,
        "fair": 0.85,
        "poor": 0.70,
        "broken": 0.40,
    }
    
    # Demand scores by model (higher = faster resale)
    DEMAND_SCORES = {
        "iPhone 15 Pro Max": 95,
        "iPhone 15 Pro": 90,
        "iPhone 15 Plus": 75,
        "iPhone 15": 80,
        "iPhone 14 Pro Max": 90,
        "iPhone 14 Pro": 85,
        "iPhone 14 Plus": 70,
        "iPhone 14": 75,
        "iPhone 13 Pro Max": 80,
        "iPhone 13 Pro": 75,
        "iPhone 13 mini": 50,
        "iPhone 13": 70,
        "iPhone 12 Pro Max": 70,
        "iPhone 12 Pro": 65,
        "iPhone 12 mini": 45,
        "iPhone 12": 60,
        "iPhone 11 Pro Max": 60,
        "iPhone 11 Pro": 55,
        "iPhone 11": 50,
        "iPhone SE": 40,
        "iPhone XR": 45,
        "iPhone XS Max": 40,
        "iPhone XS": 35,
        "iPhone X": 30,
    }
    
    # Repair cost estimates in MDL
    REPAIR_COSTS = {
        "screen_replacement": 2500,
        "battery_replacement": 800,
        "face_id_repair": 1500,
        "back_glass": 1200,
        "charging_port": 600,
        "camera_repair": 1000,
    }
    
    async def analyze_market(self) -> List[ModelStats]:
        """
        Analyze market and calculate statistics for all models.
        
        Returns:
            List of ModelStats for each model/storage combination
        """
        async with AsyncSessionLocal() as session:
            # Get all active listings grouped by model and storage
            result = await session.execute(
                select(
                    Listing.model,
                    Listing.storage_gb,
                    func.avg(Listing.price).label("avg_price"),
                    func.min(Listing.price).label("min_price"),
                    func.max(Listing.price).label("max_price"),
                    func.count(Listing.id).label("count"),
                )
                .where(Listing.status == ListingStatus.ACTIVE)
                .group_by(Listing.model, Listing.storage_gb)
                .order_by(Listing.model, Listing.storage_gb)
            )
            
            stats = []
            for row in result.all():
                model, storage, avg_price, min_price, max_price, count = row
                
                # Get all prices for this model to calculate median and std deviation
                prices_result = await session.execute(
                    select(Listing.price)
                    .where(Listing.model == model)
                    .where(Listing.storage_gb == storage)
                    .where(Listing.status == ListingStatus.ACTIVE)
                )
                prices = [float(p[0]) for p in prices_result.all()]
                
                if len(prices) > 0:
                    median_price = float(np.median(prices))
                    std_deviation = float(np.std(prices)) if len(prices) > 1 else 0
                    
                    # Calculate 10th and 90th percentiles
                    p10 = float(np.percentile(prices, 10))
                    p90 = float(np.percentile(prices, 90))
                else:
                    median_price = avg_price
                    std_deviation = 0
                    p10 = min_price
                    p90 = max_price
                
                stats.append(ModelStats(
                    model=model,
                    storage_gb=storage,
                    avg_price=float(avg_price) if avg_price else 0,
                    median_price=median_price,
                    min_price=float(min_price) if min_price else 0,
                    max_price=float(max_price) if max_price else 0,
                    std_deviation=std_deviation,
                    total_listings=count,
                    price_range_10_90=(p10, p90),
                ))
            
            # Save market analysis
            await self._save_market_analysis(session, stats)
            await session.commit()
            
            logger.info(f"Market analysis completed for {len(stats)} model variants")
            return stats
    
    async def _save_market_analysis(self, session: AsyncSession, stats: List[ModelStats]):
        """Save market analysis to database."""
        for stat in stats:
            # Check if analysis exists for this model
            existing = await session.execute(
                select(MarketAnalysis)
                .where(MarketAnalysis.model == stat.model)
                .where(MarketAnalysis.storage_gb == stat.storage_gb)
                .order_by(MarketAnalysis.analyzed_at.desc())
                .limit(1)
            )
            existing_analysis = existing.scalar_one_or_none()
            
            analysis = MarketAnalysis(
                model=stat.model,
                storage_gb=stat.storage_gb,
                avg_price=Decimal(str(stat.avg_price)),
                median_price=Decimal(str(stat.median_price)),
                min_price=Decimal(str(stat.min_price)),
                max_price=Decimal(str(stat.max_price)),
                std_deviation=Decimal(str(stat.std_deviation)),
                total_listings=stat.total_listings,
            )
            
            session.add(analysis)
    
    async def find_underpriced_listings(
        self, 
        profit_threshold: float = 1000,
        max_results: int = 50
    ) -> List[dict]:
        """
        Find underpriced listings with profit potential.
        
        Args:
            profit_threshold: Minimum profit required
            max_results: Maximum number of results
            
        Returns:
            List of underpriced listing dictionaries
        """
        async with AsyncSessionLocal() as session:
            # Get market stats
            market_stats = await self.analyze_market()
            stats_by_model = {
                (s.model, s.storage_gb): s for s in market_stats
            }
            
            # Get all active listings
            result = await session.execute(
                select(Listing).where(Listing.status == ListingStatus.ACTIVE)
            )
            listings = result.scalars().all()
            
            deals = []
            for listing in listings:
                key = (listing.model, listing.storage_gb)
                if key not in stats_by_model:
                    continue
                
                stats = stats_by_model[key]
                
                # Calculate estimated resale price
                estimated_resale = self._estimate_resale_price(listing, stats.median_price)
                
                # Calculate profit
                current_price = float(listing.price)
                repair_costs = self._estimate_repair_costs(listing)
                
                profit = estimated_resale - current_price - repair_costs
                profit_percent = (profit / current_price * 100) if current_price > 0 else 0
                
                if profit >= profit_threshold and profit_percent >= 10:
                    deals.append({
                        "listing": listing,
                        "market_median": stats.median_price,
                        "market_avg": stats.avg_price,
                        "estimated_resale": estimated_resale,
                        "current_price": current_price,
                        "repair_costs": repair_costs,
                        "profit": profit,
                        "profit_percent": round(profit_percent, 1),
                    })
            
            # Sort by profit
            deals.sort(key=lambda x: x["profit"], reverse=True)
            
            return deals[:max_results]
    
    def _estimate_resale_price(self, listing: Listing, market_median: float) -> float:
        """Estimate realistic resale price for a listing."""
        # Start with market median
        base_price = market_median
        
        # Adjust for condition
        condition_multiplier = self.RESALE_MULTIPLIERS.get(
            listing.condition or "good", 
            1.0
        )
        
        # Adjust for battery health
        battery_multiplier = 1.0
        if listing.battery_health:
            if listing.battery_health >= 95:
                battery_multiplier = 1.05
            elif listing.battery_health >= 85:
                battery_multiplier = 1.0
            elif listing.battery_health >= 75:
                battery_multiplier = 0.90
            else:
                battery_multiplier = 0.80
        
        # Adjust for defects
        defect_multiplier = 1.0
        defects = [
            listing.face_id_issue,
            listing.icloud_locked,
            listing.broken_display,
            listing.replaced_parts,
            listing.is_refurbished,
        ]
        defect_count = sum(defects)
        defect_multiplier -= defect_count * 0.10
        
        # Calculate final estimate
        estimated_price = base_price * condition_multiplier * battery_multiplier * max(0.5, defect_multiplier)
        
        return round(estimated_price, 0)
    
    def _estimate_repair_costs(self, listing: Listing) -> float:
        """Estimate repair costs based on detected issues."""
        costs = 0
        
        if listing.broken_display:
            costs += self.REPAIR_COSTS["screen_replacement"]
        
        if listing.battery_replaced or (listing.battery_health and listing.battery_health < 80):
            costs += self.REPAIR_COSTS["battery_replacement"]
        
        if listing.face_id_issue:
            costs += self.REPAIR_COSTS["face_id_repair"]
        
        return costs
    
    async def score_deal(self, listing: Listing, market_stats: ModelStats) -> DealScore:
        """
        Calculate comprehensive deal score.
        
        Returns:
            DealScore with all metrics
        """
        current_price = float(listing.price)
        
        # Calculate profit score (0-100)
        estimated_resale = self._estimate_resale_price(listing, market_stats.median_price)
        repair_costs = self._estimate_repair_costs(listing)
        estimated_profit = estimated_resale - current_price - repair_costs
        
        profit_margin = (estimated_profit / current_price * 100) if current_price > 0 else 0
        profit_score = min(100, max(0, int(profit_margin * 2)))  # Scale: 50% margin = 100 score
        
        # Calculate risk score (0-100, lower is better)
        from sqlalchemy import inspect as sa_inspect
        seller_loaded = "seller" in sa_inspect(listing).dict
        risk_factors = [
            listing.is_suspicious,
            listing.icloud_locked,
            listing.is_fake,
            listing.seller.is_blacklisted if seller_loaded and listing.seller else False,
        ]
        risk_score = sum([20 for f in risk_factors if f]) + (30 if listing.replaced_parts else 0)
        risk_score = min(100, risk_score)
        
        # Calculate resale speed score (0-100)
        demand = self.DEMAND_SCORES.get(listing.model, 50)
        condition_penalty = {
            "new": 0,
            "like_new": 0,
            "excellent": 5,
            "good": 10,
            "fair": 20,
            "poor": 30,
            "broken": 50,
        }.get(listing.condition or "good", 10)
        
        defect_penalty = sum([
            listing.face_id_issue,
            listing.broken_display,
            listing.replaced_parts,
        ]) * 10
        
        resale_speed_score = max(0, demand - condition_penalty - defect_penalty)
        
        # Demand score (from predefined scores)
        demand_score = self.DEMAND_SCORES.get(listing.model, 50)
        
        # Calculate overall score
        overall_score = int(
            profit_score * 0.40 +  # 40% weight on profit
            (100 - risk_score) * 0.25 +  # 25% weight on low risk
            resale_speed_score * 0.20 +  # 20% weight on resale speed
            demand_score * 0.15  # 15% weight on demand
        )
        
        # Generate recommendation
        if overall_score >= 80:
            recommendation = "🔥 EXCELLENT DEAL - Buy immediately!"
        elif overall_score >= 65:
            recommendation = "✅ GOOD DEAL - Worth considering"
        elif overall_score >= 50:
            recommendation = "⚠️ MODERATE - Verify before buying"
        else:
            recommendation = "❌ POOR DEAL - Skip this one"
        
        return DealScore(
            listing_id=listing.id,
            profit_score=profit_score,
            risk_score=risk_score,
            resale_speed_score=resale_speed_score,
            demand_score=demand_score,
            overall_score=overall_score,
            estimated_resale_price=estimated_resale,
            estimated_profit=estimated_profit,
            recommendation=recommendation,
        )
    
    async def get_market_trends(self, days: int = 7) -> Dict:
        """
        Get market trends over time.
        
        Returns:
            Dict with trend data
        """
        async with AsyncSessionLocal() as session:
            from datetime import datetime, timedelta
            
            since = datetime.utcnow() - timedelta(days=days)
            
            # Get new listings count
            new_result = await session.execute(
                select(func.count(Listing.id))
                .where(Listing.scraped_at >= since)
            )
            new_count = new_result.scalar()
            
            # Get sold/deleted count
            sold_result = await session.execute(
                select(func.count(Listing.id))
                .where(Listing.status == ListingStatus.SOLD)
                .where(Listing.last_checked >= since)
            )
            sold_count = sold_result.scalar()
            
            # Get average price change
            price_result = await session.execute(
                select(
                    Listing.model,
                    func.avg(Listing.price).label("avg_price")
                )
                .where(Listing.status == ListingStatus.ACTIVE)
                .group_by(Listing.model)
            )
            current_prices = {row[0]: float(row[1]) for row in price_result.all()}
            
            return {
                "period_days": days,
                "new_listings": new_count,
                "sold_listings": sold_count,
                "market_velocity": sold_count / days if days > 0 else 0,
                "current_avg_prices": current_prices,
                "analyzed_at": datetime.utcnow().isoformat(),
            }
