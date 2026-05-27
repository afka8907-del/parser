"""
Scheduler for running the parser at regular intervals.
"""

import asyncio
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from alerts.alerts import AlertManager
from analyzer.deal_detector import DealDetector
from analyzer.market_analyzer import MarketAnalyzer
from bot.telegram_bot import TelegramBot
from config import settings
from database import init_db
from parser.processor import ListingProcessor
from parser.scraper import NinesScraper


class ParserScheduler:
    """Manages scheduled parsing and analysis tasks."""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.scraper = None
        self.processor = ListingProcessor()
        self.deal_detector = DealDetector()
        self.market_analyzer = MarketAnalyzer()
        self.alert_manager = None
        self.telegram_bot = None
    
    async def init(self):
        """Initialize the scheduler and dependencies."""
        logger.info("Initializing scheduler...")
        
        # Initialize database
        await init_db()
        logger.info("Database initialized")
        
        # Initialize bot if token is set
        if settings.telegram_bot_token:
            self.telegram_bot = TelegramBot()
            self.alert_manager = AlertManager(self.telegram_bot.bot)
            self.deal_detector.alert_manager = self.alert_manager
            logger.info("Telegram bot initialized")
        
        logger.info("Scheduler initialized successfully")
    
    async def run_parser(self):
        """Run the parser job."""
        logger.info("Starting parser job...")
        
        try:
            has_existing_data = await self.processor.has_listings()
            pages_to_scrape = (
                settings.incremental_pages_per_run
                if has_existing_data
                else settings.max_pages_per_run
            )

            if has_existing_data:
                logger.info(
                    f"Incremental mode: scraping first {pages_to_scrape} pages "
                    f"(sorted by newest)"
                )
            else:
                logger.info(
                    f"Bootstrap mode: scraping up to {pages_to_scrape} pages "
                    "for initial market snapshot"
                )

            async with NinesScraper() as scraper:
                # Scrape listings
                listings = await scraper.scrape_listings(
                    max_pages=pages_to_scrape
                )
                
                if not listings:
                    logger.warning("No listings found")
                    return
                
                # Scrape details in parallel for faster cycles.
                detail_candidates = listings[:20]  # Keep bounded
                semaphore = asyncio.Semaphore(5)

                async def enrich_listing(listing):
                    async with semaphore:
                        try:
                            details = await scraper.scrape_listing_details(listing.listing_url)
                            listing.description = details.get("description", "")
                            listing.battery_health = details.get("battery_health") or listing.battery_health
                            listing.condition = details.get("condition") or listing.condition
                            listing.seller_name = details.get("seller_name") or listing.seller_name
                            if details.get("all_images"):
                                listing.images = details.get("all_images")
                        except Exception as e:
                            logger.warning(f"Error scraping details for {listing.external_id}: {e}")

                await asyncio.gather(*(enrich_listing(listing) for listing in detail_candidates))
                
                # Process and save listings
                external_ids = [l.external_id for l in listings]
                new_count, updated_count, error_count = await self.processor.process_listings(listings)
                
                # Only mark missing listings as deleted during full crawl.
                # In incremental mode, we scan only first pages and should not
                # infer deletion for older listings not present in the sample.
                if has_existing_data:
                    deleted_count = 0
                else:
                    deleted_count = await self.processor.mark_inactive_listings(external_ids)
                
                logger.info(
                    f"Parser completed: {new_count} new, {updated_count} updated, "
                    f"{deleted_count} marked deleted, {error_count} errors"
                )
                
        except Exception as e:
            logger.error(f"Error in parser job: {e}")
    
    async def run_market_analysis(self):
        """Run market analysis job."""
        logger.info("Starting market analysis job...")
        
        try:
            stats = await self.market_analyzer.analyze_market()
            logger.info(f"Market analysis completed for {len(stats)} models")
        except Exception as e:
            logger.error(f"Error in market analysis: {e}")
    
    async def run_deal_detection(self):
        """Run deal detection and alerting job."""
        logger.info("Starting deal detection job...")
        
        try:
            # Detect new deals
            new_deals = await self.deal_detector.detect_new_deals()
            if new_deals:
                logger.info(f"Detected {len(new_deals)} new profitable deals")
                
                # Send alerts
                if self.alert_manager:
                    await self.alert_manager.process_new_deals(new_deals)
                    
                    # Send to Telegram channel
                    for deal in new_deals[:5]:  # Limit to top 5
                        await self.telegram_bot.send_deal_alert(deal)
            
            # Detect price drops
            price_drops = await self.deal_detector.detect_price_drops()
            if price_drops:
                logger.info(f"Detected {len(price_drops)} price drops")
                
                if self.alert_manager:
                    for deal in price_drops:
                        await self.alert_manager.send_price_drop_alert(deal)
            
            # Check watchlists
            # This would need to be implemented with user tracking
            
        except Exception as e:
            logger.error(f"Error in deal detection: {e}")
    
    def setup_jobs(self):
        """Setup scheduled jobs."""
        # Parser job - runs every X minutes
        self.scheduler.add_job(
            self.run_parser,
            IntervalTrigger(minutes=settings.parser_interval_minutes),
            id="parser",
            name="999.md Parser",
            replace_existing=True,
        )
        
        # Market analysis - runs every hour
        self.scheduler.add_job(
            self.run_market_analysis,
            IntervalTrigger(hours=1),
            id="market_analysis",
            name="Market Analysis",
            replace_existing=True,
        )
        
        # Deal detection - runs every 10 minutes
        self.scheduler.add_job(
            self.run_deal_detection,
            IntervalTrigger(minutes=10),
            id="deal_detection",
            name="Deal Detection",
            replace_existing=True,
        )
        
        logger.info("Scheduled jobs configured")
    
    async def start(self):
        """Start the scheduler."""
        await self.init()
        self.setup_jobs()
        self.scheduler.start()
        logger.info("Scheduler started")
        
        # Run initial parser
        logger.info("Running initial parser...")
        await self.run_parser()
        await self.run_market_analysis()
        await self.run_deal_detection()
    
    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")


async def main():
    """Main entry point."""
    scheduler = ParserScheduler()
    
    try:
        await scheduler.start()
        
        # Keep running
        while True:
            await asyncio.sleep(60)
            
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down...")
        scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())
