"""
Main FastAPI application
"""

import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database.base import init_db
from app.telegram.listener import get_telegram_listener, MessageProcessor
from app.parsers.implementations import init_parsers

# Import API routes
from app.api.routes import signals, channels, message_types, telegram_auth, market

# Configure logging
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


# Initialize telegram listener at module level
telegram_listener = get_telegram_listener()


async def _connect_telegram_in_background() -> None:
    try:
        await asyncio.wait_for(
            telegram_listener.connect(),
            timeout=settings.telegram_connect_timeout_seconds,
        )
        logger.info("Connected to Telegram")
        await telegram_listener.ensure_listening()
        logger.info("Telegram listener started")
    except asyncio.CancelledError:
        raise
    except Exception as error:
        logger.error("Telegram startup connection failed; API remains available: %s", type(error).__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup
    logger.info("Starting Signal Analyzer application")
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # Initialize parsers
    init_parsers()
    logger.info("Signal parsers initialized")
    
    telegram_listener.register_handler(MessageProcessor.store_and_parse_message)
    MessageProcessor.listener = telegram_listener
    telegram_listener.refresh_channels()
    telegram_start_task = None
    if settings.enable_telegram_listener:
        telegram_start_task = asyncio.create_task(_connect_telegram_in_background())
    
    logger.info("Application startup complete")
    
    yield  # App runs here
    
    # Shutdown
    logger.info("Shutting down Signal Analyzer application")
    if telegram_start_task and not telegram_start_task.done():
        telegram_start_task.cancel()
        await asyncio.gather(telegram_start_task, return_exceptions=True)
    if telegram_listener.client:
        await telegram_listener.disconnect()
    await market.close_market_provider()
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Signal Analyzer API",
    description="Trading signal analysis platform",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(?:localhost|127\.0\.0\.1|\[::1\])(?::[0-9]+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(signals.router)
app.include_router(channels.router)
app.include_router(message_types.router)
app.include_router(telegram_auth.router)
app.include_router(market.router)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "version": "0.1.0",
        "telegram_enabled": settings.enable_telegram_listener
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Signal Analyzer API",
        "version": "0.1.0",
        "docs": "/docs",
        "features": {
            "telegram_listener": settings.enable_telegram_listener,
            "analysis_engine": settings.enable_analysis_engine,
            "trade_engine": settings.enable_trade_engine
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload
    )
