"""
Alert management system for sending notifications.
"""

from datetime import datetime
from typing import List, Optional

from aiogram import Bot
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import Alert, AsyncSessionLocal, Listing


class AlertManager:
    """Manages alerts and notifications."""
    
    def __init__(self, bot: Optional[Bot] = None):
        self.bot = bot
    
    async def create_alert(
        self, 
        listing_id: int, 
        alert_type: str, 
        message: str,
        profit_estimate: float = None
    ) -> Alert:
        """Create a new alert in the database."""
        async with AsyncSessionLocal() as session:
            alert = Alert(
                listing_id=listing_id,
                alert_type=alert_type,
                message=message,
                profit_estimate=profit_estimate,
                created_at=datetime.utcnow(),
            )
            session.add(alert)
            await session.commit()
            
            logger.info(f"Created alert {alert.id} for listing {listing_id}")
            return alert
    
    async def send_telegram_alert(
        self, 
        alert: Alert, 
        chat_id: str = None,
        reply_markup = None
    ) -> bool:
        """Send alert via Telegram."""
        if not self.bot:
            logger.warning("Bot not configured, cannot send Telegram alert")
            return False
        
        target_chat = chat_id or settings.telegram_channel_id
        if not target_chat:
            logger.warning("No target chat configured for alerts")
            return False
        
        try:
            from aiogram.types import ParseMode
            
            message = await self.bot.send_message(
                chat_id=target_chat,
                text=alert.message,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                disable_web_page_preview=True,
            )
            
            # Update alert as sent
            async with AsyncSessionLocal() as session:
                alert.sent_to_telegram = True
                alert.telegram_message_id = str(message.message_id)
                await session.commit()
            
            logger.info(f"Sent alert {alert.id} to Telegram")
            return True
            
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")
            return False
    
    async def process_new_deals(self, deals: List[dict]):
        """Process and send alerts for new deals."""
        for deal in deals:
            try:
                listing = deal["listing"]
                
                # Check if alert already sent for this listing
                async with AsyncSessionLocal() as session:
                    from sqlalchemy import select
                    
                    result = await session.execute(
                        select(Alert).where(Alert.listing_id == listing.id)
                    )
                    existing = result.scalar_one_or_none()
                    
                    if existing and existing.sent_to_telegram:
                        continue
                
                # Format alert message
                from bot.telegram_bot import TelegramBot
                
                bot_instance = TelegramBot()
                text = bot_instance._format_deal_message(deal)
                
                # Create alert
                alert = await self.create_alert(
                    listing_id=listing.id,
                    alert_type=deal.get("alert_type", "new_deal"),
                    message=text,
                    profit_estimate=deal.get("estimated_profit"),
                )
                
                # Send to Telegram
                from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔗 Vezi anunțul", url=listing.listing_url)],
                ])
                
                await self.send_telegram_alert(alert, reply_markup=keyboard)
                
            except Exception as e:
                logger.error(f"Error processing deal alert: {e}")
    
    async def send_price_drop_alert(self, deal: dict):
        """Send price drop alert."""
        listing = deal["listing"]
        drop = deal.get("price_drop", {})
        
        text = f"""
📉 <b>REDUCERE DE PREȚ</b>

📱 <b>{listing.model}</b>
{f"{listing.storage_gb}GB " if listing.storage_gb else ""}

💰 <b>Preț vechi:</b> {drop.get('old_price', 'N/A')} MDL
💰 <b>Preț nou:</b> {drop.get('new_price', 'N/A')} MDL
📉 <b>Reducere:</b> {drop.get('drop_percent', 0)}%

🔗 <a href="{listing.listing_url}">Vezi anunțul</a>
        """
        
        alert = await self.create_alert(
            listing_id=listing.id,
            alert_type="price_drop",
            message=text,
        )
        
        await self.send_telegram_alert(alert)
    
    async def send_market_report(self, report_content: str):
        """Send market report to channel."""
        text = f"""
📊 <b>RAPORT SĂPTĂMÂNAL - PIAȚA iPHONE</b>

{report_content}

<i>Raport generat automat de iPhone Reseller Intelligence</i>
        """
        
        if self.bot and settings.telegram_channel_id:
            try:
                from aiogram.types import ParseMode
                
                await self.bot.send_message(
                    chat_id=settings.telegram_channel_id,
                    text=text,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                )
                
                logger.info("Sent market report to Telegram")
                
            except Exception as e:
                logger.error(f"Error sending market report: {e}")
    
    async def send_watchlist_alert(self, user_id: int, deals: List[dict]):
        """Send watchlist match alerts to specific user."""
        if not self.bot:
            return
        
        if not deals:
            return
        
        try:
            text = f"👁 <b>Alertă Watchlist!</b>\n\n"
            text += f"Am găsit {len(deals)} oferte care se potrivesc criteriilor tale:\n\n"
            
            for i, deal in enumerate(deals[:5], 1):
                listing = deal["listing"]
                text += f"{i}. <b>{listing.model}</b>\n"
                text += f"   💰 {deal['current_price']:.0f} MDL\n"
                text += f"   📍 {listing.location or 'N/A'}\n"
                text += f"   🔗 {listing.listing_url}\n\n"
            
            from aiogram.types import ParseMode
            
            await self.bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            
            logger.info(f"Sent watchlist alert to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error sending watchlist alert: {e}")
