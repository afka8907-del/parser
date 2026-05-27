"""
Listing processor - saves scraped data to database.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Tuple

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import Listing, ListingStatus, PriceHistory, Seller
from database import AsyncSessionLocal
from parser.scraper import ScrapedListing
from utils.defect_detector import DefectDetector


class ListingProcessor:
    """Process and save scraped listings to database."""
    
    def __init__(self):
        self.defect_detector = DefectDetector()

    async def has_listings(self) -> bool:
        """Return True if the listings table already has data."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(func.count(Listing.id)))
            total = result.scalar_one() or 0
            return total > 0
    
    async def process_listings(self, listings: List[ScrapedListing]) -> Tuple[int, int, int]:
        """
        Process scraped listings and save to database.
        
        Returns:
            Tuple of (new_count, updated_count, error_count)
        """
        new_count = 0
        updated_count = 0
        error_count = 0
        
        async with AsyncSessionLocal() as session:
            for scraped in listings:
                try:
                    result = await self._process_single_listing(session, scraped)
                    if result == "new":
                        new_count += 1
                    elif result == "updated":
                        updated_count += 1
                except Exception as e:
                    logger.error(f"Error processing listing {scraped.external_id}: {e}")
                    error_count += 1
                    continue
            
            await session.commit()
        
        logger.info(
            f"Processed {len(listings)} listings: {new_count} new, "
            f"{updated_count} updated, {error_count} errors"
        )
        return new_count, updated_count, error_count
    
    async def _process_single_listing(
        self, session: AsyncSession, scraped: ScrapedListing
    ) -> str:
        """
        Process a single listing.
        
        Returns:
            "new", "updated", or "skipped"
        """
        # Check if listing already exists
        existing = await session.execute(
            select(Listing).where(Listing.external_id == scraped.external_id)
        )
        listing = existing.scalar_one_or_none()
        
        if listing:
            # Check for price change
            old_price = listing.price
            new_price = Decimal(str(scraped.price))
            
            if old_price != new_price:
                # Record price history
                price_history = PriceHistory(
                    listing_id=listing.id,
                    old_price=old_price,
                    new_price=new_price,
                )
                session.add(price_history)
                
                listing.price = new_price
                listing.original_price = old_price if not listing.original_price else listing.original_price
                logger.info(f"Price change for {scraped.external_id}: {old_price} -> {new_price}")
            
            # Update status and last checked
            listing.status = ListingStatus.ACTIVE
            listing.last_checked = datetime.utcnow()
            
            return "updated"
        
        # Get or create seller
        seller = None
        if scraped.seller_external_id:
            seller_result = await session.execute(
                select(Seller).where(Seller.external_id == scraped.seller_external_id)
            )
            seller = seller_result.scalar_one_or_none()
            
            if not seller:
                seller = Seller(
                    external_id=scraped.seller_external_id,
                    name=scraped.seller_name or "Unknown",
                    location=scraped.location,
                )
                session.add(seller)
                await session.flush()
            
            seller.last_seen = datetime.utcnow()
            seller.total_listings += 1
            seller.active_listings += 1
        
        # Detect defects from title and description
        defect_analysis = self.defect_detector.analyze(
            title=scraped.title,
            description=scraped.description,
        )
        
        # Create new listing
        listing = Listing(
            external_id=scraped.external_id,
            title=scraped.title,
            description=scraped.description,
            model=scraped.model,
            storage_gb=scraped.storage_gb,
            color=scraped.color,
            battery_health=scraped.battery_health,
            condition=scraped.condition,
            price=Decimal(str(scraped.price)),
            currency=scraped.currency,
            listing_url=scraped.listing_url,
            images=scraped.images,
            location=scraped.location,
            posted_at=scraped.posted_at,
            seller_id=seller.id if seller else None,
            status=ListingStatus.ACTIVE,
            scraped_at=datetime.utcnow(),
            last_checked=datetime.utcnow(),
            # Defect detection
            face_id_issue=defect_analysis.get("face_id_issue", False),
            icloud_locked=defect_analysis.get("icloud_locked", False),
            broken_display=defect_analysis.get("broken_display", False),
            replaced_parts=defect_analysis.get("replaced_parts", False),
            battery_replaced=defect_analysis.get("battery_replaced", False),
            is_refurbished=defect_analysis.get("is_refurbished", False),
            is_fake=defect_analysis.get("is_fake", False),
            is_suspicious=defect_analysis.get("is_suspicious", False),
        )
        
        session.add(listing)
        await session.flush()
        
        logger.debug(f"Created new listing: {scraped.external_id} - {scraped.title}")
        
        return "new"
    
    async def mark_inactive_listings(self, active_external_ids: List[str]) -> int:
        """
        Mark listings as deleted if not found in current scrape.
        
        Returns:
            Number of listings marked as deleted
        """
        async with AsyncSessionLocal() as session:
            # Get all currently active listings
            result = await session.execute(
                select(Listing).where(Listing.status == ListingStatus.ACTIVE)
            )
            active_listings = result.scalars().all()
            
            marked_count = 0
            active_set = set(active_external_ids)
            
            for listing in active_listings:
                if listing.external_id not in active_set:
                    listing.status = ListingStatus.DELETED
                    listing.last_checked = datetime.utcnow()
                    
                    # Update seller counts
                    if listing.seller_id:
                        seller_result = await session.execute(
                            select(Seller).where(Seller.id == listing.seller_id)
                        )
                        seller = seller_result.scalar_one_or_none()
                        if seller:
                            seller.active_listings = max(0, seller.active_listings - 1)
                            seller.sold_listings += 1
                    
                    marked_count += 1
            
            await session.commit()
            
            if marked_count > 0:
                logger.info(f"Marked {marked_count} listings as deleted")
            
            return marked_count
