# NeonHub AI-Powered Growth Ecosystem

An autonomous marketing system for B2B and B2C outreach across email, social media, and digital sales channels.

## System Architecture

### Core Agents
- `email_outreach_agent`: AI-personalized B2B email sequences
- `social_sync_agent`: Social media management and trend monitoring
- `ads_optim_agent`: Paid performance optimization and A/B testing
- `lead_scrape_agent`: Distributor lead generation
- `language_localizer`: Content translation and localization
- `dashboard_connector`: Analytics and KPI visualization
- `ugc_influencer_agent`: Influencer detection and UGC campaigns

### Tech Stack
- Backend: Python 3.11+
- Database: PostgreSQL
- Deployment: Vercel (Frontend) + GCP (Backend)
- Task Scheduling: Celery + Redis
- Message Queue: RabbitMQ
- API Integration: REST + GraphQL

## Setup Instructions

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```
5. Initialize the database:
   ```bash
   python scripts/init_db.py
   ```
6. Start the development server:
   ```bash
   python main.py
   ```

## Project Structure

```
neonhub/
├── agents/                 # AI agent implementations
├── api/                    # REST/GraphQL API endpoints
├── core/                   # Core business logic
├── data/                   # Data models and schemas
├── services/              # External service integrations
├── utils/                 # Utility functions
├── tests/                 # Test suite
├── scripts/               # Management scripts
└── config/                # Configuration files
```

## Development Guidelines

1. Follow PEP 8 style guide
2. Write tests for all new features
3. Document all API endpoints
4. Use type hints
5. Implement proper error handling
6. Follow security best practices

## License

MIT License - See LICENSE file for details

## Phase 13: AI Optimization Layer
- Implements a strategy optimizer that analyzes tracked outcomes (UGC, outreach, engagement, conversions) and updates internal strategy parameters automatically.
- Continuously refines outreach content, channel priority, timing, and offer logic.
- Promotes successful templates, drops underperformers, and adapts influencer engagement criteria based on conversion results.
- Adds new Prometheus metrics for strategy updates and optimizer cycles.
- Ensure `prometheus_client` is installed (see requirements.txt) for metrics support. 