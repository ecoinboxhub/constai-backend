# FAQ: Construction AI Nigeria

## Technical Questions

### What's your tech stack?
**Backend**: FastAPI (Python), PostgreSQL, Redis, Celery, MLflow, DVC, Docker, SlowAPI (rate limiting), APScheduler (scheduled tasks)

**Frontend**: React 19, TypeScript, Vite, Tailwind CSS, Recharts, TanStack Query, Framer Motion, Lucide React

**Deployment**: Docker, Render (backend), Vercel (frontend), Supabase (production DB)

### How do you handle authentication?
JWT-based authentication with access and refresh tokens. RBAC with roles: admin, project_manager, analyst, safety, procurement, legal, engineer, user.

### What's your data pipeline?
DVC for data versioning, MLflow for experiment tracking, bootstrap data generation for MVP, real-time scraping from Jiji and dealers.

### How do you deploy your models?
Models are trained offline and deployed as REST endpoints. We use joblib for scikit-learn models. For production, we plan to use LiteLLM for LLM-based features.

### What's your API architecture?
Single FastAPI gateway on port 8000 with 10 modules separated by URL paths. All endpoints require JWT authentication except health check.

### How do you handle rate limiting?
SlowAPI with 100 requests per minute limit per IP. Configurable per endpoint.

### What's your database schema?
PostgreSQL with tables: projects, delay_predictions, users, cost_estimates, equipment, safety_findings, maintenance_predictions, purchase_orders, transactions, materials, price_points, supplier_quotes, weather_logs, audit_logs, companies, accounts, employees.

### How do you handle errors?
Global exception handler returns 500 with detailed error in debug mode. Validation errors return 422. Authentication errors return 401. Authorization errors return 403.

### What's your CI/CD pipeline?
GitHub Actions for CI. Tests run on push. Docker build and push to registry. Manual deployment to Render.

### How do you handle secrets?
.env file with gitignore. Environment variables for production. Plan to use Supabase secrets or AWS Secrets Manager.

## Product Questions

### What makes you different from Procore/Autodesk?
We're Nigeria-specific with models trained on local data, Naira pricing, and COREN compliance mapping. Existing tools are generic and don't address Nigeria-specific challenges.

### How is your pricing different?
We use Naira pricing with automatic adjustments for parallel market rates. Existing tools use USD pricing and don't account for local currency volatility.

### What's your target market?
Mid-sized construction firms (500+), engineering consultancies (200+), government infrastructure departments (50+ annually).

### How do you handle data privacy?
NDPR and GDPR compliant architecture. Encrypted data at rest and in transit. Least-privilege access. Audit logging. Data retention policies.

### What's your data sources?
Synthetic data for MVP, Jiji supplier scraping, OpenWeather API, manual data entry. Plan to integrate live supplier APIs and construction company data.

### How do you handle model updates?
DVC for data versioning, MLflow for experiment tracking, CI/CD for model deployment. Plan to implement A/B testing for model comparison.

### What's your uptime target?
99.9% for production. Current local deployment is 100% (no downtime).

### How do you handle scalability?
Modular architecture allows independent scaling. Cloud-native deployment with Docker. Plan to use Kubernetes for production.

## Business Questions

### What's your business model?
Tiered subscriptions: Basic ($99/mo), Pro ($299/mo), Enterprise (custom). Free tier for small firms with limited features.

### How much are you seeking to raise?
[Specify amount] for [specific use of funds].

### What's your pricing strategy?
Product-led growth with free tier, enterprise sales for large firms, and partnerships with construction associations.

### How are you acquiring customers?
Content marketing, LinkedIn outreach, industry events, partnerships with construction associations, free tier adoption.

### What's your go-to-market strategy?
1. Pilot (Months 1-3): 10 pilot customers (free tier)
2. Launch (Months 4-6): Open beta, pricing tiers
3. Scale (Months 7-12): Enterprise sales, mobile app

### What's your revenue projection?
Year 1: $120K ARR (100 customers)
Year 2: $600K ARR (500 customers)
Year 3: $2.4M ARR (1,500 customers)

### What's your customer acquisition cost?
Target: $500 per customer (free tier conversion, content marketing).

### What's your lifetime value?
Target: $3,000 per customer (25-month average retention).

### What's your churn rate target?
Target: <5% monthly churn (SaaS benchmark).

### What's your gross margin target?
Target: 85%+ (SaaS benchmark).

### What's your burn rate?
Current: $8K/month (development, infrastructure, marketing).
Projected: $10K/month post-funding.

### What's your runway?
Current: 12 months with $100K runway.
Post-funding: 18 months with $200K runway.

## Competition Questions

### Who are your competitors?
- **Procore**: General construction software, not Nigeria-specific
- **Autodesk**: General construction software, not Nigeria-specific
- **Custom builds**: Expensive, no AI features
- **Spreadsheets**: Manual, error-prone

### What's your competitive advantage?
1. Nigeria-specific models trained on local data
2. Cross-functional platform covering planning, procurement, safety, legal, operations
3. MLOps-ready stack with DVC, MLflow, CI/CD
4. Modular design with 10 independent modules
5. Naira pricing with automatic adjustments

### How do you defend against incumbents?
1. Domain expertise: Nigeria-specific models
2. Speed: Faster deployment than custom builds
3. Cost: Lower than enterprise software
4. AI: Native AI features incumbents lack

### What's your defensibility?
1. Domain-specific AI models trained on Nigerian data
2. Cross-functional platform creating network effects
3. MLOps infrastructure for rapid iteration
4. Partnerships with construction associations

## Demo Questions

### How do you demo your product?
1. Login as project manager
2. View macro dashboard with live stats
3. Predict delay risk for a project
4. Generate cost estimate for new project
5. Analyze safety log for hazards
6. Check progress deviation
7. Download comprehensive report

### What's your demo flow?
1. Introduction (30s)
2. Problem statement (1m)
3. Solution overview (1m)
4. Live demos (6 min)
5. Closing (1m)

### How do you handle demo questions?
1. Listen carefully
2. Answer concisely
3. Demonstrate if possible
4. Follow up with details

### What's your demo script?
See `DEMO_SCRIPT.md` for detailed script.

## Technical Deep Dive Questions

### How do you handle the 72-byte bcrypt limit?
We use direct bcrypt library with manual truncation: `password.encode('utf-8')[:72].decode('utf-8', 'ignore')`

### How do you extract company_id from JWT?
We extract it from token claims: `payload.get("company_id", 1)` with default of 1 for MVP.

### How do you handle CORS?
CORS middleware with allowed origins: localhost:3000, localhost:5173, *.netlify.app.

### How do you handle rate limiting?
SlowAPI with 100 requests per minute per IP. Configurable per endpoint.

### How do you handle logging?
Structured logging with app.logger. Log levels: DEBUG, INFO, WARNING, ERROR.

### How do you handle metrics?
Prometheus metrics for request count and latency. Exposed at /metrics endpoint.

### How do you handle database migrations?
Alembic for migrations. Schema version tracked in alembic_version table.

### How do you handle background tasks?
Celery workers for async tasks. Redis as broker. APScheduler for scheduled tasks.

### How do you handle file uploads?
Currently not implemented. Plan to use Supabase Storage for images.

### How do you handle real-time updates?
Currently polling. Plan to implement WebSockets for real-time updates.

## Market Questions

### What's your TAM?
$15B+ Nigerian construction market.

### What's your SAM?
- Mid-sized construction firms: 500+
- Engineering consultancies: 200+
- Government projects: 50+ annually

### What's your SOM?
- Year 1: 100 customers
- Year 2: 500 customers
- Year 3: 1,500 customers

### What's your pricing?
- Basic: $99/mo (5 projects)
- Pro: $299/mo (20 projects)
- Enterprise: Custom (unlimited)

### What's your target customer?
Mid-sized construction firms with 10-50 employees, managing 5-20 projects.

### What's your sales cycle?
- Free tier: Self-serve, instant onboarding
- Enterprise: 2-4 weeks sales cycle

### What's your distribution strategy?
- Product-led growth (free tier)
- Enterprise sales (large firms)
- Partnerships (construction associations)

## Team Questions

### Who's on your team?
[Your Name] - Founder, AI/ML, Backend, Frontend

### What's your team's expertise?
- AI/ML: Construction domain expertise, NLP, computer vision
- Backend: FastAPI, PostgreSQL, Docker, CI/CD
- Frontend: React, TypeScript, Tailwind, Recharts
- DevOps: Render, Vercel, Supabase

### What's your team's track record?
[Add if applicable - previous startups, projects, achievements]

### What's your co-founder situation?
Solo founder. Open to co-founder with [specific skill].

### What's your advisory board?
[Add if applicable - advisors with industry expertise]

## Financial Questions

### What's your burn rate?
Current: $8K/month (development, infrastructure, marketing).

### What's your runway?
Current: 12 months with $100K runway.

### What's your revenue projection?
Year 1: $120K ARR (100 customers)
Year 2: $600K ARR (500 customers)
Year 3: $2.4M ARR (1,500 customers)

### What's your gross margin target?
85%+ (SaaS benchmark).

### What's your CAC target?
$500 per customer.

### What's your LTV target?
$3,000 per customer.

### What's your churn rate target?
<5% monthly churn.

### What's your pricing strategy?
Product-led growth with free tier, enterprise sales for large firms.

## Legal Questions

### What's your entity structure?
[Specify - LLC, C-Corp, etc.]

### What's your IP situation?
All IP owned by company. No third-party IP.

### What's your data privacy compliance?
NDPR and GDPR compliant architecture.

### What's your terms of service?
Standard SaaS terms with Nigeria-specific clauses.

### What's your privacy policy?
Standard privacy policy with NDPR/GDPR compliance.

### What's your security posture?
Encrypted data at rest and in transit. Least-privilege access. Audit logging.

## Investor-Specific Questions

### Why are you building this?
[Personal story - passion for construction, AI, Nigeria]

### What's your vision?
To become the operating system for Nigerian construction.

### What's your 12-month roadmap?
MVP production, 10 pilots, real-time data, mobile MVP, 500 customers.

### What's your 3-year roadmap?
1,000 customers, African expansion, enterprise features, mobile app.

### What's your exit strategy?
Acquisition by construction software company (Procore, Autodesk) or SaaS platform.

### What's your competitive moat?
Domain-specific AI models, cross-functional platform, MLOps infrastructure.

### What's your biggest risk?
Data acquisition. Mitigation: Building data pipeline partnerships.

### What's your traction?
MVP production-ready, all metrics exceeding targets, 11/11 endpoints passing.

### What's your ask?
[Specify amount and use of funds]

### What's your timeline to profitability?
Month 18 with 1,000 customers.

### What's your cap table?
[Specify ownership structure]

### What's your dilution target?
[Specify target dilution]

## Demo Day Questions

### What's your product?
AI-powered construction project management for Nigeria.

### What's the problem?
40-60% delays, 15-20% safety violations, 20-30% cost overruns.

### What's your solution?
10-module AI platform with Nigeria-specific models.

### What's your traction?
MVP production-ready, all metrics exceeding targets.

### What's your market?
$15B+ Nigerian construction market.

### What's your team?
[Your Name] - AI/ML, Backend, Frontend

### What's your ask?
[Specify amount and use of funds]

### What's your vision?
To become the operating system for African construction.

### What's your competitive advantage?
Nigeria-specific models, cross-functional platform, MLOps-ready.

### What's your business model?
Tiered subscriptions: Basic ($99/mo), Pro ($299/mo), Enterprise.

### What's your timeline?
MVP production, 10 pilots, 500 customers in 12 months.

## Post-Meeting Questions

### What are your next steps?
1. Deploy to production
2. Onboard pilot customers
3. Build enterprise features

### When can I expect to hear back?
[Specify timeline - 1 week, 2 weeks, etc.]

### What feedback do you have?
[Listen carefully, take notes]

### Can I follow up?
[Specify preferred contact method]

### Who else are you talking to?
[Specify if applicable]

### What's your decision timeline?
[Specify if applicable]

## Rejection Handling

### What if they say no?
- Ask for feedback
- Thank them for their time
- Ask if you can follow up in 6 months
- Stay positive and professional

### What if they're not interested?
- Ask for referrals
- Ask if they know anyone who might be interested
- Stay in touch for future opportunities

### What if they want more information?
- Send follow-up email with details
- Schedule a follow-up call
- Provide additional documentation

## Success Handling

### What if they want to invest?
- Ask about next steps
- Ask about timeline
- Ask about due diligence process

### What if they want to partner?
- Ask about partnership terms
- Ask about integration requirements
- Ask about co-marketing opportunities

### What if they want to buy?
- Ask about valuation
- Ask about terms
- Ask about timeline

## General Tips

### What should I wear?
Business casual or startup casual.

### What should I bring?
Laptop, notes, business cards, demo access.

### What should I avoid?
- Badmouthing competitors
- Overpromising
- Dismissing concerns
- Being defensive

### What questions should I ask?
- What are your biggest concerns?
- What would make you invest?
- What's your timeline?
- What are your next steps?

### What should I do after?
- Send thank-you email
- Follow up in 1 week
- Provide requested information
- Stay in touch
