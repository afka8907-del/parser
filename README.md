# iPhone Reseller Intelligence Platform

An advanced Telegram-based reseller assistant that continuously monitors iPhone listings from 999.md (Moldova's largest classifieds site), analyzes the entire market, detects underpriced deals, calculates potential resale profit, and sends instant Telegram alerts.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)
![React](https://img.shields.io/badge/React-18+-61DAFB.svg)

## Features

### Market Parser
- Parse all iPhone listings from 999.md using Playwright
- Extract: title, model, storage, battery health, condition, price, currency, seller, location, posting time, listing URL, images, description
- Auto-detect: Face ID issues, locked/iCloud phones, broken display, replaced parts, battery replacement, fake/refurbished mentions

### Database System
- SQLite/PostgreSQL storage with SQLAlchemy
- Duplicate prevention
- Historical price tracking
- Seller history tracking
- Deleted listings archive
- Price change tracking over time

### Market Analyzer
- Analyze iPhone models separately (11/12/13/14/15 series, Pro/Pro Max variants)
- Calculate: average price, median price, cheapest listing, overpriced/underpriced detection
- Estimate reseller value and profit potential
- Market trend tracking

### Deal Detection System
- Underpriced phone detection
- Urgent sales identification
- Newly posted deals monitoring
- Reposted listings detection
- Suspicious/scam listing detection
- Comprehensive deal scoring: profitability, risk, resale speed, demand

### Telegram Bot
- Commands: /topdeals, /cheapest, /market, /iphone13, /iphone14pro, /profit, /search, /stats, /seller, /watchlist
- Instant notifications for hot deals
- Inline buttons for quick actions
- Image previews
- Pagination and search filters
- Admin panel and CSV/Excel export

### Advanced Features
- Market intelligence (best-selling models, price drop detection)
- Seller analysis (reputation scoring, flipper/reseller detection)
- AI/NLP analysis for hidden defects detection
- Price prediction engine
- Watchlist system with custom alerts
- Image analysis (optional)
- Weekly market reports

### Admin Dashboard
- Live listings view with filters
- Interactive price charts (Chart.js/Recharts)
- Hottest deals overview
- Seller rankings
- Market analytics
- Profit statistics
- React + TailwindCSS frontend

## Project Structure

```
project/
├── bot/                    # Telegram bot (aiogram)
│   ├── telegram_bot.py
│   └── __init__.py
├── parser/                 # Web scraper (Playwright)
│   ├── scraper.py
│   ├── processor.py
│   └── __init__.py
├── analyzer/               # Market analysis & deal detection
│   ├── market_analyzer.py
│   ├── deal_detector.py
│   └── __init__.py
├── dashboard/              # Web dashboard
│   ├── backend/            # FastAPI
│   │   ├── main.py
│   │   └── schemas.py
│   └── frontend/           # React
│       ├── src/
│       └── public/
├── database/               # Database models & session
│   ├── models.py
│   ├── session.py
│   └── __init__.py
├── alerts/                 # Alert management
│   ├── alerts.py
│   └── __init__.py
├── utils/                  # Helper functions
│   ├── defect_detector.py
│   └── helpers.py
├── config/                 # Configuration
│   └── settings.py
├── docker/                 # Docker setup
│   ├── Dockerfile
│   └── docker-compose.yml
├── logs/                   # Log files
├── data/                   # SQLite database (if used)
├── main.py                 # Main entry point
├── scheduler.py            # Background scheduler
├── requirements.txt
├── .env.example
└── README.md
```

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+ (for frontend)
- PostgreSQL (optional, SQLite works too)
- Redis (optional, for caching)
- Telegram Bot Token (from @BotFather)

### Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd iphone-reseller-intel
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
playwright install chromium
```

4. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your settings
```

5. **Run the application:**

Run everything (scheduler + API):
```bash
python main.py all
```

Or run components separately:
```bash
# Scheduler only (parser + bot)
python main.py scheduler

# API only
python main.py api

# Bot only
python main.py bot
```

### Frontend Setup

```bash
cd dashboard/frontend
npm install
npm start
```

The dashboard will be available at `http://localhost:3000`

## Docker Deployment

### Quick Start with Docker Compose

```bash
# Build and start all services
docker-compose up -d

# Or use the provided docker compose file
cd docker
docker-compose up -d
```

### Services
- **app**: Main application (scheduler + API)
- **db**: PostgreSQL database
- **redis**: Redis cache
- **scheduler** (optional): Separate scheduler service

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```env
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Database (choose one)
DATABASE_URL=sqlite+aiosqlite:///./data/iphone_market.db
# DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/iphone_market

# 999.md scraping
TARGET_URL=https://999.md/ro/list/phone-and-communication/mobile-phones?o_16_1=776&o_1078_589=6309&o_1084_593=6371,6370&o_2200_795=18895
PARSER_INTERVAL_MINUTES=5

# Telegram
TELEGRAM_ADMIN_USER_IDS=123456789,987654321
TELEGRAM_CHANNEL_ID=@your_channel_name

# OpenAI (optional, for AI analysis)
OPENAI_API_KEY=your_openai_key_here
ENABLE_AI_ANALYSIS=true

# API
API_HOST=0.0.0.0
API_PORT=8000
```

### Target URL

The default target URL filters for:
- iPhone brand (Apple)
- Mobile phones category
- Sorted by newest first

You can customize this URL in `.env` to target different regions or categories.

## Usage

### Telegram Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and help |
| `/help` | Detailed usage guide |
| `/topdeals` | Top 10 profitable deals |
| `/cheapest [model]` | Cheapest listings |
| `/market` | Market analysis |
| `/profit [buy] [sell] [costs]` | Profit calculator |
| `/iphone13` | iPhone 13 deals |
| `/iphone14pro` | iPhone 14 Pro deals |
| `/search [term]` | Search listings |
| `/stats` | Platform statistics |
| `/seller [name]` | Seller analysis |
| `/watchlist` | Manage watchlist |
| `/admin` | Admin panel |

### Dashboard

Access the web dashboard at `http://localhost:8000` (API) or `http://localhost:3000` (React dev server).

Features:
- Real-time listings with filters
- Deal rankings
- Price charts
- Seller analytics
- Alert history

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/stats` | Overall statistics |
| `GET /api/listings` | List all listings |
| `GET /api/deals` | Get top deals |
| `GET /api/market-stats` | Market analysis |
| `GET /api/sellers` | Seller list |
| `GET /api/alerts` | Alert history |
| `GET /api/models` | Available models |
| `GET /api/trends` | Market trends |

## Profit Calculation

The platform calculates profit using:

```
profit = estimated_resale_price - listing_price - estimated_repair_cost
```

Alerts are sent only if:
- Profit > configurable threshold (default: 1000 MDL)
- Risk score is acceptable
- Not a duplicate
- Seller is not blacklisted

## Anti-Bot Protection

The scraper includes:
- Rotating user agents
- Proxy support (configurable)
- Browser fingerprint randomization
- Request delays (2-5 seconds random)
- Stealth Playwright mode

## Development

### Running Tests

```bash
pytest
```

### Code Style

```bash
black .
isort .
flake8
```

### Database Migrations

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## Architecture

### Data Flow

1. **Parser** runs every 5 minutes (configurable)
2. New listings are saved to database
3. **Analyzer** calculates market stats
4. **Deal Detector** identifies profitable opportunities
5. **Alert Manager** sends Telegram notifications
6. **Dashboard** displays real-time data

### Async Architecture

- All I/O operations are async (asyncio)
- Database uses SQLAlchemy async session
- Telegram bot uses aiogram (async)
- Web scraper uses Playwright (async)

## Troubleshooting

### Playwright Issues

If Chromium fails to launch:
```bash
playwright install-deps chromium
```

### Database Connection

For PostgreSQL connection issues:
```bash
# Check if PostgreSQL is running
sudo service postgresql status

# Create database
sudo -u postgres psql -c "CREATE DATABASE iphone_market;"
```

### Telegram Bot Not Responding

1. Check bot token is correct
2. Ensure bot is started with `/start`
3. Check logs: `tail -f logs/app.log`

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## Support

For support, questions, or feature requests:
- Open an issue on GitHub
- Contact via Telegram: @your_support_bot

## Roadmap

- [ ] Image analysis with AI (detect cracked screens)
- [ ] Multi-market support (OLX, Facebook Marketplace)
- [ ] Mobile app (React Native)
- [ ] Advanced ML price prediction
- [ ] Inventory management system
- [ ] Automated buying bot (with safeguards)

---

**Disclaimer**: This tool is for educational and research purposes. Respect website Terms of Service and use responsibly.
