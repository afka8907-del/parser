"""
Main entry point for the iPhone Reseller Intelligence Platform.
"""

import asyncio
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from loguru import logger

from config import settings
from dashboard.backend.main import app as api_app
from scheduler import ParserScheduler


# Configure logging
logger.remove()
logger.add(
    settings.log_file,
    rotation=settings.log_rotation,
    level=settings.log_level,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
)
logger.add(
    sys.stdout,
    level=settings.log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
)


class Application:
    """Main application controller."""
    
    def __init__(self):
        self.scheduler = None
        self.mode = None
    
    async def run_scheduler(self):
        """Run only the scheduler (parser + bot)."""
        self.scheduler = ParserScheduler()
        await self.scheduler.start()
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(60)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Shutting down scheduler...")
            self.scheduler.stop()
    
    def run_api(self):
        """Run only the API server."""
        uvicorn.run(
            "dashboard.backend.main:app",
            host=settings.api_host,
            port=settings.api_port,
            reload=settings.api_debug,
            log_level="info",
        )
    
    async def run_all(self):
        """Run both scheduler and API."""
        # Start scheduler in background
        self.scheduler = ParserScheduler()
        await self.scheduler.init()
        self.scheduler.setup_jobs()
        self.scheduler.scheduler.start()
        
        # Run initial jobs
        await self.scheduler.run_parser()
        await self.scheduler.run_market_analysis()
        
        logger.info("Scheduler started, launching API server...")
        
        # Start API server
        config = uvicorn.Config(
            "dashboard.backend.main:app",
            host=settings.api_host,
            port=settings.api_port,
            reload=settings.api_debug,
            log_level="info",
        )
        server = uvicorn.Server(config)
        await server.serve()


def print_usage():
    """Print usage information."""
    print("""
iPhone Reseller Intelligence Platform

Usage:
  python main.py [mode]

Modes:
  scheduler    - Run only the parser scheduler and Telegram bot
  api          - Run only the FastAPI server
  all          - Run both scheduler and API (default)
  bot          - Run only the Telegram bot

Examples:
  python main.py scheduler
  python main.py api
  python main.py all
    """)


async def main():
    """Main entry point."""
    # Get mode from command line
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    if mode in ("-h", "--help", "help"):
        print_usage()
        return
    
    app = Application()
    app.mode = mode
    
    logger.info(f"Starting iPhone Reseller Intelligence Platform in '{mode}' mode")
    
    try:
        if mode == "scheduler":
            await app.run_scheduler()
        elif mode == "api":
            app.run_api()
        elif mode == "all":
            await app.run_all()
        elif mode == "bot":
            # Run only bot
            from bot.telegram_bot import TelegramBot
            bot = TelegramBot()
            await bot.start()
        else:
            print(f"Unknown mode: {mode}")
            print_usage()
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
