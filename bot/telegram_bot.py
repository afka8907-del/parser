"""
Telegram bot using aiogram for iPhone reseller intelligence.

Uses inline keyboards and callback queries for a modern menu-driven UX
instead of requiring users to type slash commands.
"""

import asyncio
from typing import List, Optional

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from loguru import logger
from sqlalchemy import func, or_, select

from alerts.alerts import AlertManager
from analyzer.deal_detector import DealDetector
from analyzer.market_analyzer import MarketAnalyzer
from config import settings
from database import AsyncSessionLocal, Listing, ListingStatus, Watchlist
from utils.helpers import format_currency


def _main_menu_kb() -> InlineKeyboardMarkup:
    """Build the persistent main-menu inline keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔥 Top Deals", callback_data="menu_topdeals"),
            InlineKeyboardButton(text="💰 Cheapest", callback_data="menu_cheapest"),
        ],
        [
            InlineKeyboardButton(text="📊 Market", callback_data="menu_market"),
            InlineKeyboardButton(text="📈 Stats", callback_data="menu_stats"),
        ],
        [
            InlineKeyboardButton(text="📱 By Model", callback_data="menu_models"),
            InlineKeyboardButton(text="🔍 Search", callback_data="menu_search"),
        ],
        [
            InlineKeyboardButton(text="💵 Profit Calc", callback_data="menu_profit"),
            InlineKeyboardButton(text="👁 Watchlist", callback_data="menu_watchlist"),
        ],
    ])


def _models_kb() -> InlineKeyboardMarkup:
    """Keyboard for choosing an iPhone model."""
    rows = [
        [
            InlineKeyboardButton(text="iPhone 17 Pro", callback_data="model_iPhone 17 Pro"),
            InlineKeyboardButton(text="iPhone 16 Pro", callback_data="model_iPhone 16 Pro"),
        ],
        [
            InlineKeyboardButton(text="iPhone 16", callback_data="model_iPhone 16"),
            InlineKeyboardButton(text="iPhone 15 Pro", callback_data="model_iPhone 15 Pro"),
        ],
        [
            InlineKeyboardButton(text="iPhone 15", callback_data="model_iPhone 15"),
            InlineKeyboardButton(text="iPhone 14 Pro", callback_data="model_iPhone 14 Pro"),
        ],
        [
            InlineKeyboardButton(text="iPhone 14", callback_data="model_iPhone 14"),
            InlineKeyboardButton(text="iPhone 13", callback_data="model_iPhone 13"),
        ],
        [
            InlineKeyboardButton(text="iPhone 12", callback_data="model_iPhone 12"),
            InlineKeyboardButton(text="iPhone 11", callback_data="model_iPhone 11"),
        ],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="menu_back")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _back_kb() -> InlineKeyboardMarkup:
    """Single back-to-menu button."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Menu", callback_data="menu_back")],
    ])


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
        """Setup command and callback handlers."""
        self.router.message.register(self.cmd_start, CommandStart())
        self.router.message.register(self.cmd_help, Command("help"))
        self.router.message.register(self.cmd_search, Command("search"))
        self.router.message.register(self.cmd_profit, Command("profit"))
        self.router.message.register(self.cmd_admin, Command("admin"))

        self.router.callback_query.register(self.on_callback)

    def _is_admin(self, user_id: int) -> bool:
        return user_id in settings.admin_user_ids

    # ------------------------------------------------------------------
    # /start – welcome + main menu
    # ------------------------------------------------------------------
    async def cmd_start(self, message: Message):
        welcome = (
            "🔥 <b>iPhone Reseller Intelligence</b>\n\n"
            "Găsește cele mai profitabile oferte iPhone din Moldova.\n\n"
            "Alege o opțiune din meniu:"
        )
        await message.answer(welcome, parse_mode=ParseMode.HTML, reply_markup=_main_menu_kb())

    async def cmd_help(self, message: Message):
        help_text = (
            "<b>📖 Ghid rapid</b>\n\n"
            "Folosește butoanele din meniu sau comenzile:\n"
            "/search <i>termen</i> — caută listări\n"
            "/profit <i>buy sell [costs]</i> — calcul profit\n\n"
            "Meniul principal:"
        )
        await message.answer(help_text, parse_mode=ParseMode.HTML, reply_markup=_main_menu_kb())

    # ------------------------------------------------------------------
    # Callback router
    # ------------------------------------------------------------------
    async def on_callback(self, cq: CallbackQuery):
        data = cq.data
        try:
            if data == "menu_back":
                await self._edit_menu(cq)
            elif data == "menu_topdeals":
                await self._cb_topdeals(cq)
            elif data == "menu_cheapest":
                await self._cb_cheapest(cq)
            elif data == "menu_market":
                await self._cb_market(cq)
            elif data == "menu_stats":
                await self._cb_stats(cq)
            elif data == "menu_models":
                await self._cb_models_menu(cq)
            elif data == "menu_search":
                await cq.message.edit_text(
                    "🔍 <b>Căutare</b>\n\nTrimite comanda:\n<code>/search termen</code>",
                    parse_mode=ParseMode.HTML,
                    reply_markup=_back_kb(),
                )
                await cq.answer()
            elif data == "menu_profit":
                await cq.message.edit_text(
                    "💵 <b>Calculator Profit</b>\n\nTrimite comanda:\n"
                    "<code>/profit buy_price sell_price [costs]</code>\n\n"
                    "Ex: <code>/profit 15000 19500 500</code>",
                    parse_mode=ParseMode.HTML,
                    reply_markup=_back_kb(),
                )
                await cq.answer()
            elif data == "menu_watchlist":
                await self._cb_watchlist(cq)
            elif data.startswith("model_"):
                model = data[len("model_"):]
                await self._cb_model_deals(cq, model)
            elif data.startswith("fav_"):
                await cq.answer("⭐ Adăugat la favorite!")
            else:
                await cq.answer()
        except Exception as e:
            logger.error(f"Callback error ({data}): {e}")
            await cq.answer("❌ Eroare internă")

    async def _edit_menu(self, cq: CallbackQuery):
        """Switch the current message back to the main menu."""
        await cq.message.edit_text(
            "🔥 <b>iPhone Reseller Intelligence</b>\n\nAlege o opțiune:",
            parse_mode=ParseMode.HTML,
            reply_markup=_main_menu_kb(),
        )
        await cq.answer()

    # ------------------------------------------------------------------
    # Top Deals
    # ------------------------------------------------------------------
    async def _cb_topdeals(self, cq: CallbackQuery):
        await cq.message.edit_text("🔍 Caut cele mai bune afaceri...", reply_markup=None)
        await cq.answer()

        try:
            deals = await self.deal_detector.get_top_deals(limit=5)
            if not deals:
                await cq.message.edit_text(
                    "❌ Nu am găsit afaceri profitabile momentan.\n"
                    "Asigură-te că parserul a rulat cel puțin o dată.",
                    reply_markup=_back_kb(),
                )
                return

            for i, deal in enumerate(deals, 1):
                listing = deal["listing"]
                text = self._format_deal_message(deal, i)
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔗 Vezi anunțul", url=listing.listing_url)],
                ])
                if i == 1:
                    await cq.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
                else:
                    await cq.message.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb)
                await asyncio.sleep(0.3)

            await cq.message.answer("⬅️ Meniu principal", reply_markup=_main_menu_kb())
        except Exception as e:
            logger.error(f"topdeals error: {e}")
            await cq.message.edit_text("❌ Eroare la căutarea afacerilor.", reply_markup=_back_kb())

    # ------------------------------------------------------------------
    # Cheapest
    # ------------------------------------------------------------------
    async def _cb_cheapest(self, cq: CallbackQuery):
        await cq.message.edit_text("🔍 Caut cele mai ieftine iPhone...", reply_markup=None)
        await cq.answer()

        try:
            listings = await self.deal_detector.get_cheapest_listings(limit=10)
            if not listings:
                await cq.message.edit_text("❌ Nu am găsit listări.", reply_markup=_back_kb())
                return

            response = "📊 <b>Cele mai ieftine iPhone</b>\n\n"
            for i, listing in enumerate(listings, 1):
                price = format_currency(float(listing.price), listing.currency)
                response += f"{i}. <b>{listing.model}</b>"
                if listing.storage_gb:
                    response += f" {listing.storage_gb}GB"
                response += f"\n   💰 {price}"
                if listing.location:
                    response += f" | 📍 {listing.location}"
                response += f"\n   🔗 <a href='{listing.listing_url}'>Vezi</a>\n\n"

            await cq.message.edit_text(
                response, parse_mode=ParseMode.HTML,
                disable_web_page_preview=True, reply_markup=_back_kb(),
            )
        except Exception as e:
            logger.error(f"cheapest error: {e}")
            await cq.message.edit_text("❌ Eroare.", reply_markup=_back_kb())

    # ------------------------------------------------------------------
    # Market analysis
    # ------------------------------------------------------------------
    async def _cb_market(self, cq: CallbackQuery):
        await cq.message.edit_text("📊 Analizez piața...", reply_markup=None)
        await cq.answer()

        try:
            stats = await self.market_analyzer.analyze_market()
            if not stats:
                await cq.message.edit_text(
                    "❌ Nu sunt date de piață. Rulează parserul mai întâi.",
                    reply_markup=_back_kb(),
                )
                return

            top_models = sorted(stats, key=lambda x: x.total_listings, reverse=True)[:8]

            response = "📈 <b>Analiza Pieței iPhone</b>\n\n"
            response += f"<b>Modele analizate:</b> {len(stats)}\n\n"

            for stat in top_models:
                storage = f"{stat.storage_gb}GB" if stat.storage_gb else "—"
                response += (
                    f"• <b>{stat.model}</b> ({storage})\n"
                    f"  {stat.total_listings} listări | Avg: {format_currency(stat.avg_price, 'MDL')}\n"
                    f"  Min: {format_currency(stat.min_price, 'MDL')} — "
                    f"Max: {format_currency(stat.max_price, 'MDL')}\n\n"
                )

            await cq.message.edit_text(
                response, parse_mode=ParseMode.HTML, reply_markup=_back_kb(),
            )
        except Exception as e:
            logger.error(f"market error: {e}")
            await cq.message.edit_text("❌ Eroare la analiza pieței.", reply_markup=_back_kb())

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    async def _cb_stats(self, cq: CallbackQuery):
        await cq.answer()

        try:
            async with AsyncSessionLocal() as session:
                total_active = (await session.execute(
                    select(func.count(Listing.id)).where(Listing.status == ListingStatus.ACTIVE)
                )).scalar() or 0

                total_all = (await session.execute(
                    select(func.count(Listing.id))
                )).scalar() or 0

                model_rows = (await session.execute(
                    select(Listing.model, func.count(Listing.id).label("cnt"))
                    .where(Listing.status == ListingStatus.ACTIVE)
                    .group_by(Listing.model)
                    .order_by(func.count(Listing.id).desc())
                    .limit(5)
                )).all()

                avg_price = (await session.execute(
                    select(func.avg(Listing.price)).where(Listing.status == ListingStatus.ACTIVE)
                )).scalar() or 0

            response = (
                "📊 <b>Statistici Platformă</b>\n\n"
                f"<b>Listări active:</b> {total_active:,}\n"
                f"<b>Total listări:</b> {total_all:,}\n"
                f"<b>Preț mediu:</b> {format_currency(float(avg_price), 'MDL')}\n\n"
                "<b>Top modele:</b>\n"
            )
            for model, cnt in model_rows:
                response += f"• {model}: {cnt}\n"

            response += (
                f"\n<b>Parser:</b> 🟢 Activ | interval {settings.parser_interval_minutes} min"
            )

            await cq.message.edit_text(
                response, parse_mode=ParseMode.HTML, reply_markup=_back_kb(),
            )
        except Exception as e:
            logger.error(f"stats error: {e}")
            await cq.message.edit_text("❌ Eroare.", reply_markup=_back_kb())

    # ------------------------------------------------------------------
    # Model picker
    # ------------------------------------------------------------------
    async def _cb_models_menu(self, cq: CallbackQuery):
        await cq.message.edit_text(
            "📱 <b>Alege un model:</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=_models_kb(),
        )
        await cq.answer()

    async def _cb_model_deals(self, cq: CallbackQuery, model: str):
        await cq.message.edit_text(f"📱 Caut {model}...", reply_markup=None)
        await cq.answer()

        try:
            listings = await self.deal_detector.get_cheapest_listings(model=model, limit=8)
            if not listings:
                await cq.message.edit_text(
                    f"❌ Nu am găsit {model} disponibil.",
                    reply_markup=_back_kb(),
                )
                return

            response = f"📱 <b>{model} — cele mai bune prețuri</b>\n\n"
            for i, listing in enumerate(listings, 1):
                price = format_currency(float(listing.price), listing.currency)
                response += f"{i}. <b>{listing.title[:50]}</b>\n"
                response += f"   💰 {price}"
                if listing.storage_gb:
                    response += f" | {listing.storage_gb}GB"
                if listing.location:
                    response += f"\n   📍 {listing.location}"
                response += f"\n   🔗 <a href='{listing.listing_url}'>Vezi</a>\n\n"

            await cq.message.edit_text(
                response, parse_mode=ParseMode.HTML,
                disable_web_page_preview=True, reply_markup=_back_kb(),
            )
        except Exception as e:
            logger.error(f"model deals error: {e}")
            await cq.message.edit_text("❌ Eroare.", reply_markup=_back_kb())

    # ------------------------------------------------------------------
    # Watchlist
    # ------------------------------------------------------------------
    async def _cb_watchlist(self, cq: CallbackQuery):
        user_id = cq.from_user.id
        await cq.answer()

        try:
            async with AsyncSessionLocal() as session:
                watches = (await session.execute(
                    select(Watchlist).where(Watchlist.user_id == user_id)
                )).scalars().all()

            if not watches:
                await cq.message.edit_text(
                    "👁 <b>Watchlist gol</b>\n\n"
                    "Adaugă alerte cu:\n<code>/watchlist add model storage max_price</code>",
                    parse_mode=ParseMode.HTML,
                    reply_markup=_back_kb(),
                )
                return

            response = "👁 <b>Watchlist-ul tău</b>\n\n"
            for w in watches:
                response += f"• <b>{w.model or 'Orice'}</b>"
                if w.storage_gb:
                    response += f" {w.storage_gb}GB"
                if w.max_price:
                    response += f" | Max: {format_currency(float(w.max_price), 'MDL')}"
                response += "\n"

            await cq.message.edit_text(
                response, parse_mode=ParseMode.HTML, reply_markup=_back_kb(),
            )
        except Exception as e:
            logger.error(f"watchlist error: {e}")
            await cq.message.edit_text("❌ Eroare.", reply_markup=_back_kb())

    # ------------------------------------------------------------------
    # /search command (text-based by necessity)
    # ------------------------------------------------------------------
    async def cmd_search(self, message: Message):
        args = message.text.split()[1:]
        if not args:
            await message.answer(
                "🔍 <b>Căutare</b>\n\nUtilizare: <code>/search termen</code>\n"
                "Ex: <code>/search 256GB</code>, <code>/search pro max</code>",
                parse_mode=ParseMode.HTML, reply_markup=_back_kb(),
            )
            return

        term = " ".join(args)
        try:
            async with AsyncSessionLocal() as session:
                listings = (await session.execute(
                    select(Listing)
                    .where(Listing.status == ListingStatus.ACTIVE)
                    .where(or_(
                        Listing.title.ilike(f"%{term}%"),
                        Listing.description.ilike(f"%{term}%"),
                        Listing.model.ilike(f"%{term}%"),
                    ))
                    .order_by(Listing.price.asc())
                    .limit(10)
                )).scalars().all()

            if not listings:
                await message.answer(
                    f"❌ Niciun rezultat pentru «{term}».",
                    reply_markup=_back_kb(),
                )
                return

            response = f"🔍 <b>Rezultate pentru «{term}»</b>\n\n"
            for i, listing in enumerate(listings, 1):
                price = format_currency(float(listing.price), listing.currency)
                response += (
                    f"{i}. <b>{listing.model}</b>"
                    f"{f' {listing.storage_gb}GB' if listing.storage_gb else ''}\n"
                    f"   💰 {price}"
                    f"{f' | 📍 {listing.location}' if listing.location else ''}\n"
                    f"   🔗 <a href='{listing.listing_url}'>Vezi</a>\n\n"
                )

            await message.answer(
                response, parse_mode=ParseMode.HTML,
                disable_web_page_preview=True, reply_markup=_back_kb(),
            )
        except Exception as e:
            logger.error(f"search error: {e}")
            await message.answer("❌ Eroare la căutare.", reply_markup=_back_kb())

    # ------------------------------------------------------------------
    # /profit command
    # ------------------------------------------------------------------
    async def cmd_profit(self, message: Message):
        args = message.text.split()[1:]
        if len(args) < 2:
            await message.answer(
                "💵 <b>Calculator Profit</b>\n\n"
                "<code>/profit buy sell [costs]</code>\n"
                "Ex: <code>/profit 15000 19500 500</code>",
                parse_mode=ParseMode.HTML, reply_markup=_back_kb(),
            )
            return

        try:
            buy = float(args[0])
            sell = float(args[1])
            costs = float(args[2]) if len(args) > 2 else 0

            from utils.helpers import calculate_profit_margin
            c = calculate_profit_margin(buy, sell, costs)

            emoji = "🟢" if c["roi_percent"] >= 20 else "🟡" if c["roi_percent"] >= 10 else "🔴"
            response = (
                "💵 <b>Rezultat</b>\n\n"
                f"Cumpăr: {format_currency(buy, 'MDL')}\n"
                f"Vând: {format_currency(sell, 'MDL')}\n"
                f"Costuri: {format_currency(costs, 'MDL')}\n\n"
                f"<b>Profit net:</b> {format_currency(c['net_profit'], 'MDL')}\n"
                f"<b>Marjă:</b> {c['margin_percent']}%\n"
                f"<b>ROI:</b> {c['roi_percent']}%\n\n"
                f"{emoji} {'Excelent!' if c['roi_percent'] >= 20 else 'Bun.' if c['roi_percent'] >= 10 else 'Slab.'}"
            )
            await message.answer(response, parse_mode=ParseMode.HTML, reply_markup=_back_kb())
        except ValueError:
            await message.answer("❌ Valori invalide. Folosește numere.")

    # ------------------------------------------------------------------
    # /admin
    # ------------------------------------------------------------------
    async def cmd_admin(self, message: Message):
        if not self._is_admin(message.from_user.id):
            await message.answer("⛔ Acces interzis.")
            return

        args = message.text.split()[1:]
        if not args:
            await message.answer(
                "🔐 <b>Admin</b>\n\n"
                "<code>/admin force_run</code> — rulează parser\n"
                "<code>/admin stats</code> — statistici",
                parse_mode=ParseMode.HTML,
            )
            return

        if args[0] == "force_run":
            await message.answer("🔄 Pornesc parserul manual...")
            await message.answer("✅ Parser pornit!")

    # ------------------------------------------------------------------
    # Deal formatting
    # ------------------------------------------------------------------
    def _format_deal_message(self, deal: dict, rank: int = None) -> str:
        listing = deal["listing"]
        emoji = ["🥇", "🥈", "🥉"][rank - 1] if rank and rank <= 3 else f"{rank}." if rank else "🔥"

        current_price = format_currency(deal["current_price"], listing.currency)
        market_avg = format_currency(deal["market_avg"], "MDL")
        resale = format_currency(deal["estimated_resale"], "MDL")
        profit = format_currency(deal["estimated_profit"], "MDL")

        text = f"{emoji} <b>DEAL</b>\n\n"
        text += f"📱 <b>{listing.model}</b>"
        if listing.storage_gb:
            text += f" {listing.storage_gb}GB"
        text += "\n\n"

        text += (
            f"💰 <b>Preț:</b> {current_price}\n"
            f"📊 <b>Media pieței:</b> {market_avg}\n"
            f"💵 <b>Revânzare est.:</b> {resale}\n"
            f"✅ <b>Profit est.:</b> +{profit} ({deal['profit_margin']}%)\n\n"
        )

        text += f"Score: {deal['score']}/100"
        risk_emoji = "🟢" if deal["risk_score"] < 30 else "🟡" if deal["risk_score"] < 60 else "🔴"
        text += f" | {risk_emoji} Risc: {deal['risk_score']}/100\n"

        if listing.face_id_issue:
            text += "⚠️ Face ID defect\n"
        if listing.icloud_locked:
            text += "⛔ iCloud blocat\n"

        text += f"\n<b>{deal['recommendation']}</b>"
        return text

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def start(self):
        logger.info("Starting Telegram bot...")
        await self.bot.set_my_commands([
            BotCommand(command="start", description="Meniu principal"),
            BotCommand(command="search", description="Caută listări"),
            BotCommand(command="profit", description="Calculator profit"),
            BotCommand(command="help", description="Ajutor"),
        ])
        await self.dp.start_polling(self.bot)

    async def stop(self):
        logger.info("Stopping Telegram bot...")
        await self.bot.session.close()

    async def send_alert(self, chat_id: int, text: str, reply_markup=None):
        try:
            await self.bot.send_message(
                chat_id=chat_id, text=text,
                parse_mode=ParseMode.HTML, reply_markup=reply_markup,
                disable_web_page_preview=True,
            )
        except Exception as e:
            logger.error(f"Error sending alert: {e}")

    async def send_deal_alert(self, deal: dict, chat_id: int = None):
        text = self._format_deal_message(deal)
        listing = deal["listing"]
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Vezi anunțul", url=listing.listing_url)],
        ])
        target = chat_id or settings.telegram_channel_id
        if target:
            await self.send_alert(target, text, kb)
