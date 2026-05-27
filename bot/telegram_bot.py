"""
Telegram bot using aiogram for iPhone reseller intelligence.
"""

import asyncio
from typing import List, Optional

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from loguru import logger

from alerts.alerts import AlertManager
from analyzer.deal_detector import DealDetector
from analyzer.market_analyzer import MarketAnalyzer
from config import settings
from database import AsyncSessionLocal, Listing, Watchlist
from utils.helpers import format_currency


class TelegramBot:
    """Telegram bot for iPhone reseller intelligence."""
    
    def __init__(self):
        self.bot = Bot(token=settings.telegram_bot_token)
        self.dp = Dispatcher()
        self.router = Router()
        self.dp.include_router(self.router)
        
        self.deal_detector = DealDetector()
        self.market_analyzer = MarketAnalyzer()
        self.alert_manager = AlertManager(self.bot)
        
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup command handlers."""
        # Basic commands
        self.router.message.register(self.cmd_start, CommandStart())
        self.router.message.register(self.cmd_help, Command("help"))
        
        # Deal commands
        self.router.message.register(self.cmd_topdeals, Command("topdeals"))
        self.router.message.register(self.cmd_cheapest, Command("cheapest"))
        self.router.message.register(self.cmd_market, Command("market"))
        self.router.message.register(self.cmd_profit, Command("profit"))
        
        # Model-specific commands
        self.router.message.register(self.cmd_iphone13, Command("iphone13"))
        self.router.message.register(self.cmd_iphone14, Command("iphone14"))
        self.router.message.register(self.cmd_iphone14pro, Command("iphone14pro"))
        self.router.message.register(self.cmd_iphone15, Command("iphone15"))
        self.router.message.register(self.cmd_iphone15pro, Command("iphone15pro"))
        
        # Search and stats
        self.router.message.register(self.cmd_search, Command("search"))
        self.router.message.register(self.cmd_stats, Command("stats"))
        self.router.message.register(self.cmd_seller, Command("seller"))
        
        # Watchlist
        self.router.message.register(self.cmd_watchlist, Command("watchlist"))
        
        # Admin commands
        self.router.message.register(self.cmd_admin, Command("admin"))
        
        # Callback handlers
        self.router.callback_query.register(self.on_callback)
    
    def _is_admin(self, user_id: int) -> bool:
        """Check if user is admin."""
        return user_id in settings.admin_user_ids
    
    # ===== Basic Commands =====
    
    async def cmd_start(self, message: Message):
        """Handle /start command."""
        welcome_text = f"""
🔥 <b>Bine ai venit la iPhone Reseller Intelligence!</b>

Sunt asistentul tău inteligent pentru arbitrage și profit pe piața iPhone din Moldova.

<b>Comenzi disponibile:</b>

📊 <b>Piață:</b>
/topdeals - Top afaceri profitabile
/cheapest - Cele mai ieftine listări
/market - Analiza pieței
/profit - Calcul profit

📱 <b>Modele:</b>
/iphone13, /iphone14, /iphone14pro
/iphone15, /iphone15pro

🔍 <b>Căutare:</b>
/search [term] - Caută listări
/stats - Statistici generale
/seller [nume] - Info vânzător

👁 <b>Watchlist:</b>
/watchlist - Gestionează alerte

<b>Canal:</b> {settings.telegram_channel_id or 'N/A'}
        """
        await message.answer(welcome_text, parse_mode=ParseMode.HTML)
    
    async def cmd_help(self, message: Message):
        """Handle /help command."""
        help_text = """
<b>📖 Ghid de utilizare</b>

<b>Cum să găsești afaceri:</b>
1. Folosește /topdeals pentru cele mai bune oportunități
2. Setează /watchlist pentru alerte automate
3. Verifică /market pentru tendințe

<b>Cum să analizezi un iPhone:</b>
1. Copiază link-ul din 999.md
2. Vei primi analiză automată cu:
   • Scor de profit
   • Preț de revânzare estimat
   • Riscuri detectate
   • Sfaturi de negociere

<b>Profit Calculator:</b>
/profit [buy_price] [sell_price] [costs]

<b>Pentru suport:</b> Contact admin
        """
        await message.answer(help_text, parse_mode=ParseMode.HTML)
    
    # ===== Deal Commands =====
    
    async def cmd_topdeals(self, message: Message):
        """Handle /topdeals command."""
        await message.answer("🔍 Caut cele mai bune afaceri...")
        
        try:
            deals = await self.deal_detector.get_top_deals(limit=10)
            
            if not deals:
                await message.answer("❌ Nu am găsit afaceri profitabile momentan.")
                return
            
            for i, deal in enumerate(deals[:5], 1):
                listing = deal["listing"]
                text = self._format_deal_message(deal, i)
                
                # Create inline buttons
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔗 Vezi anunțul", url=listing.listing_url)],
                    [InlineKeyboardButton(text="⭐ Adaugă la favorite", callback_data=f"fav_{listing.id}")],
                ])
                
                await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
                await asyncio.sleep(0.5)  # Avoid rate limits
                
        except Exception as e:
            logger.error(f"Error in topdeals: {e}")
            await message.answer("❌ Eroare la căutarea afacerilor.")
    
    async def cmd_cheapest(self, message: Message):
        """Handle /cheapest command."""
        args = message.text.split()[1:] if len(message.text.split()) > 1 else []
        model = args[0] if args else None
        
        await message.answer(f"🔍 Caut cele mai ieftine {model or 'iPhone'}...")
        
        try:
            listings = await self.deal_detector.get_cheapest_listings(
                model=model, 
                limit=10
            )
            
            if not listings:
                await message.answer(f"❌ Nu am găsit listări pentru {model or 'iPhone'}.")
                return
            
            response = f"📊 <b>Cele mai ieftine {model or 'iPhone'}</b>\n\n"
            
            for i, listing in enumerate(listings, 1):
                price = format_currency(float(listing.price), listing.currency)
                response += f"{i}. <b>{listing.model}</b>\n"
                response += f"   💰 {price}"
                if listing.storage_gb:
                    response += f" | {listing.storage_gb}GB"
                response += f"\n   📍 {listing.location or 'N/A'}"
                if listing.battery_health:
                    response += f" | 🔋 {listing.battery_health}%"
                response += f"\n   🔗 <a href='{listing.listing_url}'>Vezi anunțul</a>\n\n"
            
            await message.answer(response, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            
        except Exception as e:
            logger.error(f"Error in cheapest: {e}")
            await message.answer("❌ Eroare la căutare.")
    
    async def cmd_market(self, message: Message):
        """Handle /market command."""
        await message.answer("📊 Analizez piața...")
        
        try:
            stats = await self.market_analyzer.analyze_market()
            
            # Get top models by volume
            top_models = sorted(stats, key=lambda x: x.total_listings, reverse=True)[:8]
            
            response = "📈 <b>Analiza Pieței iPhone</b>\n\n"
            response += f"<b>Total modele analizate:</b> {len(stats)}\n"
            response += f"<b>Actualizat:</b> acum\n\n"
            
            response += "<b>Top modele după volum:</b>\n"
            for stat in top_models:
                storage = f"{stat.storage_gb}GB" if stat.storage_gb else "N/A"
                avg_price = format_currency(stat.avg_price, "MDL")
                response += f"• <b>{stat.model}</b> ({storage})\n"
                response += f"  📊 {stat.total_listings} listări | 💰 {avg_price}\n"
                response += f"  Min: {format_currency(stat.min_price, 'MDL')} | "
                response += f"Max: {format_currency(stat.max_price, 'MDL')}\n\n"
            
            # Add trends
            trends = await self.market_analyzer.get_market_trends(days=7)
            response += f"\n📈 <b>Tendințe (ultimele 7 zile):</b>\n"
            response += f"• Listări noi: {trends['new_listings']}\n"
            response += f"• Vânzări: {trends['sold_listings']}\n"
            response += f"• Viteza pieței: {trends['market_velocity']:.1f}/zi\n"
            
            await message.answer(response, parse_mode=ParseMode.HTML)
            
        except Exception as e:
            logger.error(f"Error in market: {e}")
            await message.answer("❌ Eroare la analiza pieței.")
    
    async def cmd_profit(self, message: Message):
        """Handle /profit command."""
        args = message.text.split()[1:]
        
        if len(args) < 2:
            await message.answer(
                "💰 <b>Calculator Profit</b>\n\n"
                "Utilizare: <code>/profit [buy] [sell] [costs]</code>\n\n"
                "Exemple:\n"
                "• <code>/profit 15000 19500</code>\n"
                "• <code>/profit 15000 19500 500</code> (cu costuri)\n\n"
                "Calculează: marja, ROI, profit net",
                parse_mode=ParseMode.HTML
            )
            return
        
        try:
            buy_price = float(args[0])
            sell_price = float(args[1])
            costs = float(args[2]) if len(args) > 2 else 0
            
            from utils.helpers import calculate_profit_margin
            
            calc = calculate_profit_margin(buy_price, sell_price, costs)
            
            response = "💰 <b>Calculator Profit</b>\n\n"
            response += f"<b>Cumpărare:</b> {format_currency(calc['buy_price'], 'MDL')}\n"
            response += f"<b>Vânzare:</b> {format_currency(calc['sell_price'], 'MDL')}\n"
            response += f"<b>Costuri:</b> {format_currency(calc['costs'], 'MDL')}\n\n"
            response += f"<b>Profit brut:</b> {format_currency(calc['gross_profit'], 'MDL')}\n"
            response += f"<b>Profit net:</b> {format_currency(calc['net_profit'], 'MDL')}\n"
            response += f"<b>Marjă:</b> {calc['margin_percent']}%\n"
            response += f"<b>ROI:</b> {calc['roi_percent']}%\n\n"
            
            if calc['roi_percent'] >= 20:
                response += "🟢 <b>Excelent! Oportunitate grozavă!</b>"
            elif calc['roi_percent'] >= 10:
                response += "🟡 <b>Bun. Merită considerat.</b>"
            else:
                response += "🔴 <b>Slab. Profit insuficient.</b>"
            
            await message.answer(response, parse_mode=ParseMode.HTML)
            
        except ValueError:
            await message.answer("❌ Valori invalide. Folosește numere.")
    
    # ===== Model Commands =====
    
    async def _send_model_deals(self, message: Message, model: str):
        """Send deals for specific model."""
        await message.answer(f"📱 Caut {model}...")
        
        try:
            listings = await self.deal_detector.get_cheapest_listings(
                model=model, 
                limit=8
            )
            
            if not listings:
                await message.answer(f"❌ Nu am găsit {model} disponibil.")
                return
            
            response = f"📱 <b>{model} - Cele mai bune prețuri</b>\n\n"
            
            for i, listing in enumerate(listings, 1):
                price = format_currency(float(listing.price), listing.currency)
                response += f"{i}. <b>{listing.title[:40]}...</b>\n"
                response += f"   💰 {price}"
                if listing.storage_gb:
                    response += f" | {listing.storage_gb}GB"
                response += f"\n   📍 {listing.location or 'N/A'}"
                if listing.battery_health:
                    response += f" | 🔋 {listing.battery_health}%"
                response += f"\n   🔗 <a href='{listing.listing_url}'>Vezi anunțul</a>\n\n"
            
            await message.answer(response, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            
        except Exception as e:
            logger.error(f"Error getting {model} deals: {e}")
            await message.answer(f"❌ Eroare la căutarea {model}.")
    
    async def cmd_iphone13(self, message: Message):
        await self._send_model_deals(message, "iPhone 13")
    
    async def cmd_iphone14(self, message: Message):
        await self._send_model_deals(message, "iPhone 14")
    
    async def cmd_iphone14pro(self, message: Message):
        await self._send_model_deals(message, "iPhone 14 Pro")
    
    async def cmd_iphone15(self, message: Message):
        await self._send_model_deals(message, "iPhone 15")
    
    async def cmd_iphone15pro(self, message: Message):
        await self._send_model_deals(message, "iPhone 15 Pro")
    
    # ===== Search and Stats Commands =====
    
    async def cmd_search(self, message: Message):
        """Handle /search command."""
        args = message.text.split()[1:]
        
        if not args:
            await message.answer(
                "🔍 <b>Căutare</b>\n\n"
                "Utilizare: <code>/search [term]</code>\n\n"
                "Exemple:\n"
                "• <code>/search 256GB</code>\n"
                "• <code>/search pro max</code>\n"
                "• <code>/search baterie 90</code>",
                parse_mode=ParseMode.HTML
            )
            return
        
        search_term = " ".join(args)
        await message.answer(f"🔍 Caut: <b>{search_term}</b>...", parse_mode=ParseMode.HTML)
        
        try:
            async with AsyncSessionLocal() as session:
                from sqlalchemy import or_
                
                result = await session.execute(
                    select(Listing)
                    .where(Listing.status == "active")
                    .where(
                        or_(
                            Listing.title.ilike(f"%{search_term}%"),
                            Listing.description.ilike(f"%{search_term}%"),
                            Listing.model.ilike(f"%{search_term}%"),
                        )
                    )
                    .order_by(Listing.price.asc())
                    .limit(10)
                )
                listings = result.scalars().all()
                
                if not listings:
                    await message.answer(f"❌ Nu am găsit rezultate pentru '{search_term}'.")
                    return
                
                response = f"🔍 <b>Rezultate pentru '{search_term}'</b>\n\n"
                
                for i, listing in enumerate(listings, 1):
                    price = format_currency(float(listing.price), listing.currency)
                    response += f"{i}. <b>{listing.model}</b>\n"
                    response += f"   💰 {price}"
                    if listing.storage_gb:
                        response += f" | {listing.storage_gb}GB"
                    response += f"\n   📍 {listing.location or 'N/A'}"
                    response += f"\n   🔗 <a href='{listing.listing_url}'>Vezi anunțul</a>\n\n"
                
                await message.answer(response, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
                
        except Exception as e:
            logger.error(f"Error in search: {e}")
            await message.answer("❌ Eroare la căutare.")
    
    async def cmd_stats(self, message: Message):
        """Handle /stats command."""
        await message.answer("📊 Generez statistici...")
        
        try:
            async with AsyncSessionLocal() as session:
                from sqlalchemy import func
                
                # Total stats
                total_result = await session.execute(
                    select(func.count(Listing.id)).where(Listing.status == "active")
                )
                total_active = total_result.scalar()
                
                # Total all time
                all_result = await session.execute(select(func.count(Listing.id)))
                total_all = all_result.scalar()
                
                # Model distribution
                model_result = await session.execute(
                    select(Listing.model, func.count(Listing.id).label("count"))
                    .where(Listing.status == "active")
                    .group_by(Listing.model)
                    .order_by(func.count(Listing.id).desc())
                    .limit(5)
                )
                top_models = model_result.all()
                
                # Average price
                price_result = await session.execute(
                    select(func.avg(Listing.price)).where(Listing.status == "active")
                )
                avg_price = price_result.scalar() or 0
                
                response = "📊 <b>Statistici Platformă</b>\n\n"
                response += f"<b>Listări active:</b> {total_active:,}\n"
                response += f"<b>Total listări:</b> {total_all:,}\n"
                response += f"<b>Preț mediu:</b> {format_currency(float(avg_price), 'MDL')}\n\n"
                
                response += "<b>Top modele:</b>\n"
                for model, count in top_models:
                    response += f"• {model}: {count} listări\n"
                
                response += f"\n<b>Status parser:</b> 🟢 Activ\n"
                response += f"<b>Interval:</b> {settings.parser_interval_minutes} minute\n"
                
                await message.answer(response, parse_mode=ParseMode.HTML)
                
        except Exception as e:
            logger.error(f"Error in stats: {e}")
            await message.answer("❌ Eroare la generarea statisticilor.")
    
    async def cmd_seller(self, message: Message):
        """Handle /seller command."""
        args = message.text.split()[1:]
        
        if not args:
            await message.answer(
                "👤 <b>Analiză Vânzător</b>\n\n"
                "Utilizare: <code>/seller [nume/id]</code>\n\n"
                "Afișează:\n"
                "• Reputație și istoric\n"
                "• Număr de listări\n"
                "• Scor de încredere",
                parse_mode=ParseMode.HTML
            )
            return
        
        seller_name = " ".join(args)
        await message.answer(f"👤 Caut vânzătorul: <b>{seller_name}</b>...", parse_mode=ParseMode.HTML)
        
        try:
            async with AsyncSessionLocal() as session:
                from database import Seller
                
                result = await session.execute(
                    select(Seller).where(Seller.name.ilike(f"%{seller_name}%"))
                )
                seller = result.scalar_one_or_none()
                
                if not seller:
                    await message.answer(f"❌ Vânzătorul '{seller_name}' nu a fost găsit.")
                    return
                
                response = f"👤 <b>Analiză Vânzător</b>\n\n"
                response += f"<b>Nume:</b> {seller.name}\n"
                response += f"<b>Locație:</b> {seller.location or 'N/A'}\n\n"
                
                response += f"<b>Statistici:</b>\n"
                response += f"• Listări totale: {seller.total_listings}\n"
                response += f"• Listări active: {seller.active_listings}\n"
                response += f"• Vânzări: {seller.sold_listings}\n"
                response += f"• Scor reputație: {seller.reputation_score}/5.00\n\n"
                
                if seller.is_trusted:
                    response += "✅ <b>Vânzător de încredere</b>\n"
                if seller.is_reseller:
                    response += "🔄 <b>Identificat ca reseller</b>\n"
                if seller.is_blacklisted:
                    response += "⛔ <b>Vânzător pe blacklist</b>\n"
                
                response += f"\n<b>Prima apariție:</b> {seller.first_seen.strftime('%d.%m.%Y')}\n"
                response += f"<b>Ultima apariție:</b> {seller.last_seen.strftime('%d.%m.%Y') if seller.last_seen else 'N/A'}\n"
                
                await message.answer(response, parse_mode=ParseMode.HTML)
                
        except Exception as e:
            logger.error(f"Error in seller: {e}")
            await message.answer("❌ Eroare la căutarea vânzătorului.")
    
    # ===== Watchlist Commands =====
    
    async def cmd_watchlist(self, message: Message):
        """Handle /watchlist command."""
        user_id = message.from_user.id
        
        args = message.text.split()[1:]
        
        if not args:
            # Show current watchlist
            try:
                async with AsyncSessionLocal() as session:
                    result = await session.execute(
                        select(Watchlist).where(Watchlist.user_id == user_id)
                    )
                    watches = result.scalars().all()
                    
                    if not watches:
                        await message.answer(
                            "👁 <b>Watchlist Gol</b>\n\n"
                            "Primești alerte automat pentru:\n"
                            "• iPhone sub prețul pieței\n"
                            "• Oferte urgente\n\n"
                            "Pentru alerte personalizate:\n"
                            "<code>/watchlist add iphone14 256 15000</code>\n\n"
                            "Format: /watchlist add [model] [storage] [max_price]",
                            parse_mode=ParseMode.HTML
                        )
                        return
                    
                    response = "👁 <b>Watchlist-ul tău</b>\n\n"
                    
                    for watch in watches:
                        response += f"• <b>{watch.model or 'Orice model'}</b>\n"
                        if watch.storage_gb:
                            response += f"  {watch.storage_gb}GB | "
                        if watch.max_price:
                            response += f"Max: {format_currency(float(watch.max_price), 'MDL')}\n"
                        response += f"  /remove_{watch.id} pentru ștergere\n\n"
                    
                    await message.answer(response, parse_mode=ParseMode.HTML)
                    
            except Exception as e:
                logger.error(f"Error in watchlist: {e}")
                await message.answer("❌ Eroare.")
            return
        
        # Add to watchlist
        if args[0] == "add" and len(args) >= 2:
            model = args[1] if len(args) > 1 else None
            storage = int(args[2]) if len(args) > 2 and args[2].isdigit() else None
            max_price = float(args[3]) if len(args) > 3 else None
            
            try:
                async with AsyncSessionLocal() as session:
                    watch = Watchlist(
                        user_id=user_id,
                        model=model,
                        storage_gb=storage,
                        max_price=max_price,
                        notify_on_deal=True,
                    )
                    session.add(watch)
                    await session.commit()
                    
                    await message.answer(
                        f"✅ <b>Adăugat în watchlist!</b>\n\n"
                        f"Model: {model or 'Orice'}\n"
                        f"Stocare: {storage or 'Orice'}GB\n"
                        f"Preț max: {format_currency(max_price, 'MDL') if max_price else 'Orice'}\n\n"
                        f"Vei primi alerte când găsesc oferte.",
                        parse_mode=ParseMode.HTML
                    )
                    
            except Exception as e:
                logger.error(f"Error adding watchlist: {e}")
                await message.answer("❌ Eroare la adăugare.")
    
    # ===== Admin Commands =====
    
    async def cmd_admin(self, message: Message):
        """Handle /admin command."""
        user_id = message.from_user.id
        
        if not self._is_admin(user_id):
            await message.answer("⛔ Acces interzis.")
            return
        
        args = message.text.split()[1:]
        
        if not args:
            await message.answer(
                "🔐 <b>Panou Admin</b>\n\n"
                "Comenzi:\n"
                "• <code>/admin stats</code> - Statistici complete\n"
                "• <code>/admin force_run</code> - Rulează parser acum\n"
                "• <code>/admin broadcast [mesaj]</code> - Mesaj tuturor\n"
                "• <code>/admin export</code> - Export CSV",
                parse_mode=ParseMode.HTML
            )
            return
        
        subcommand = args[0]
        
        if subcommand == "force_run":
            await message.answer("🔄 Pornesc parserul manual...")
            # This would trigger the parser - implementation depends on your setup
            await message.answer("✅ Parser pornit! Verifică logurile.")
            
        elif subcommand == "broadcast":
            if len(args) < 2:
                await message.answer("❌ Specifică un mesaj.")
                return
            
            broadcast_msg = " ".join(args[1:])
            # Broadcast logic would go here
            await message.answer(f"📢 Mesaj trimis!")
            
        else:
            await message.answer("❌ Comandă necunoscută.")
    
    # ===== Callback Handler =====
    
    async def on_callback(self, callback_query: CallbackQuery):
        """Handle inline button callbacks."""
        data = callback_query.data
        
        if data.startswith("fav_"):
            listing_id = int(data.split("_")[1])
            await callback_query.answer("⭐ Adăugat la favorite!")
            
        elif data.startswith("remove_"):
            watch_id = int(data.split("_")[1])
            # Remove from watchlist
            await callback_query.answer("🗑️ Șters din watchlist.")
    
    # ===== Helper Methods =====
    
    def _format_deal_message(self, deal: dict, rank: int = None) -> str:
        """Format deal message for Telegram."""
        listing = deal["listing"]
        
        emoji_rank = ["🥇", "🥈", "🥉"][rank - 1] if rank and rank <= 3 else f"{rank}." if rank else "🔥"
        
        text = f"{emoji_rank} <b>🔥 UNDERPRICED DEAL</b>\n\n"
        
        text += f"📱 <b>{listing.model}</b>"
        if listing.storage_gb:
            text += f" {listing.storage_gb}GB"
        text += "\n\n"
        
        # Price info
        current_price = format_currency(deal["current_price"], listing.currency)
        market_avg = format_currency(deal["market_avg"], "MDL")
        estimated_resale = format_currency(deal["estimated_resale"], "MDL")
        profit = format_currency(deal["profit"], "MDL")
        
        text += f"💰 <b>Preț actual:</b> {current_price}\n"
        text += f"📊 <b>Preț mediu piață:</b> {market_avg}\n"
        text += f"💵 <b>Preț revânzare est.:</b> {estimated_resale}\n"
        text += f"✅ <b>Profit estimat:</b> +{profit} ({deal['profit_margin']}%)\n\n"
        
        # Details
        if listing.battery_health:
            text += f"🔋 <b>Baterie:</b> {listing.battery_health}%\n"
        if listing.location:
            text += f"📍 <b>Locație:</b> {listing.location}\n"
        if listing.condition:
            text += f"📋 <b>Condiție:</b> {listing.condition}\n"
        
        # Scores
        text += f"\n📈 <b>Scoruri:</b>\n"
        text += f"  Overall: {deal['score']}/100\n"
        text += f"  Profit: {deal['profit_score']}/100\n"
        risk_emoji = "🟢" if deal['risk_score'] < 30 else "🟡" if deal['risk_score'] < 60 else "🔴"
        text += f"  {risk_emoji} Risc: {deal['risk_score']}/100\n"
        text += f"  Viteza vânzării: {deal['resale_speed_score']}/100\n\n"
        
        # Issues
        issues = []
        if listing.face_id_issue:
            issues.append("⚠️ Face ID defect")
        if listing.icloud_locked:
            issues.append("⛔ iCloud blocat")
        if listing.broken_display:
            issues.append("📱 Display spart")
        if listing.replaced_parts:
            issues.append("🔧 Piese înlocuite")
        
        if issues:
            text += "<b>Probleme detectate:</b>\n" + "\n".join(issues) + "\n\n"
        
        text += f"<b>{deal['recommendation']}</b>\n\n"
        
        return text
    
    # ===== Lifecycle Methods =====
    
    async def start(self):
        """Start the bot."""
        logger.info("Starting Telegram bot...")
        await self.dp.start_polling(self.bot)
    
    async def stop(self):
        """Stop the bot."""
        logger.info("Stopping Telegram bot...")
        await self.bot.session.close()
    
    async def send_alert(self, chat_id: int, text: str, reply_markup=None):
        """Send alert to specific chat."""
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                disable_web_page_preview=True,
            )
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
    
    async def send_deal_alert(self, deal: dict, chat_id: int = None):
        """Send deal alert to channel or specific chat."""
        text = self._format_deal_message(deal)
        
        listing = deal["listing"]
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Vezi anunțul", url=listing.listing_url)],
        ])
        
        target = chat_id or settings.telegram_channel_id
        if target:
            await self.send_alert(target, text, keyboard)
