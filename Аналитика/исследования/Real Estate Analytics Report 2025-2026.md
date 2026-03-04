# Real Estate Analytics & Valuation Tools: Global Report (2025-2026)

*Research Date: March 2026*

---

## Table of Contents
1. [Top US Real Estate Analytics Platforms](#1-top-us-real-estate-analytics-platforms)
2. [Automated Valuation Models (AVM) -- Deep Dive](#2-automated-valuation-models-avm--deep-dive)
3. [Auction/Foreclosure Analytics](#3-auctionforeclosure-analytics)
4. [PropTech Trends 2025-2026](#4-proptech-trends-2025-2026)
5. [UK & European Platforms](#5-uk--european-platforms)
6. [Sources](#6-sources)

---

## 1. Top US Real Estate Analytics Platforms

### 1.1 Zillow Zestimate

**How It Works:**
Zillow's Zestimate uses a neural network-based model that processes data from county/tax assessor records and direct feeds from hundreds of MLS (Multiple Listing Services) and brokerages. The algorithm uses ensemble methods to weight factors differently depending on local market conditions.

**Data Sources:**
- County and tax assessor records (50+ years of history)
- MLS listings and brokerage feeds (hundreds of sources)
- Property characteristics: square footage, lot size, bedrooms, bathrooms
- On-market data: listing price, description, comparable homes, days on market
- Off-market data: tax assessments, prior sales, public records
- Property photos via computer vision/image recognition

**Accuracy Metrics (2025-2026):**
| Metric | On-Market | Off-Market |
|--------|-----------|------------|
| Median Error Rate | 1.83% | 7.01% |
| Within 5% of sale price | ~70% | N/A |
| Within 10% of sale price | ~90% | N/A |

For a $400,000 home, the ~2.4% error translates to approximately $9,600.

**Key Limitations:**
- Cannot assess property condition, recent renovations, or unique features
- Accuracy depends heavily on data availability in the area
- Rural and low-transaction areas have significantly higher error rates
- Does not account for curb appeal, interior design quality, or neighborhood nuances

**Pricing Model:** Free for consumers. Zillow monetizes through advertising (Premier Agent program) and ancillary services.

**Coverage:** 100M+ homes across the US.

---

### 1.2 Redfin Estimate

**Approach:**
Redfin's Estimate relies heavily on MLS data, which updates daily, giving it an edge in active markets where homes sell quickly. The model uses comparable sales analysis combined with machine learning.

**Accuracy Metrics (2025-2026):**
| Metric | On-Market | Off-Market |
|--------|-----------|------------|
| Median Error Rate | 1.98% | 7.72% |

**Key Difference from Zillow:**
- Redfin has direct MLS access (as a licensed brokerage), providing fresher listing data
- Zillow casts a wider net with more diverse data sources (tax records, user inputs, photos)
- In practice, accuracy is nearly identical nationally (~0.3% difference)
- Both vary significantly by location: Nevada ~4.5-4.8% error vs. Maine/Vermont ~12-13%

**Pricing Model:** Free for consumers. Redfin monetizes as a discount brokerage.

---

### 1.3 Realtor.com

**Approach:**
Realtor.com's My Home tool delivers **multiple valuations from professional data providers** rather than a single algorithmic estimate. It leverages direct access to MLS and recent sales data.

**Key Features:**
- Aggregates estimates from multiple AVM providers (including CoreLogic)
- Direct MLS data integration (official MLS portal partner)
- Provides a range of estimates rather than a single number
- Operated by Move, Inc. (subsidiary of News Corp)

**Pricing Model:** Free for consumers. Monetized via lead generation for agents.

---

### 1.4 Trulia

**Technology:**
Trulia (owned by Zillow Group since 2015) uses a proprietary algorithm that calculates estimates automatically and updates them daily. Since Zillow's acquisition, Trulia Estimates are now powered by the Zestimate engine.

**Data Sources:**
- Location, lot size, square footage
- Bedrooms, bathrooms count
- Property tax information and assessor records
- Nearby home sales trends

**Coverage:** 65M+ off-market single-family homes, condos, and townhomes.

**Accuracy:** Comparable to Zestimate (same underlying model). Trulia continuously monitors accuracy by comparing actual sales prices over rolling 3-month periods.

---

### 1.5 HouseCanary -- Professional AVM

**Technology:**
HouseCanary is an institutional-grade AVM platform that combines massive datasets with ML/AI algorithms and proprietary image recognition technology that identifies room types and assesses home condition from photos.

**Data Coverage:**
- 114M+ residential properties in the US
- Thousands of normalized data sources (public records, MLS, proprietary)
- AI-driven + manual quality control pipelines

**Accuracy Metrics:**
| Metric | Value |
|--------|-------|
| Pre-list Median Absolute Error | ~7.5% |
| Post-list Median Absolute Error | ~2.7% |
| Third-party verified | Yes (best pre-list AVM) |

**Key Features:**
- Image recognition for property condition assessment
- Monthly fairness assessments (bias reduction vs. traditional appraisals)
- API access for enterprise clients
- Comparable sales and rental analytics
- Market forecasting (3-year forward projections)

**Pricing Model:** Enterprise/B2B. Custom contracts for lenders, investors, and institutions. Not consumer-facing.

---

### 1.6 CoreLogic -- Total Home ValueX

**Technology:**
CoreLogic's Total Home ValueX is an enterprise AVM that leverages cloud computing and machine learning. It is designed as a single unified model that eliminates the need for multiple AVMs.

**Data Sources:**
- Property records capturing 99.9%+ of US properties
- 50+ years of historical transaction data
- MLS data feeds
- Non-traditional data sources (not typically used in AVMs)
- Daily data refresh cycle

**Key Features:**
- Single-model architecture (replaces need for cascading AVMs)
- Available on Databricks Marketplace
- Supports mortgage, insurance, PropTech, and government use cases
- Confidence scoring for each valuation

**Pricing Model:** Enterprise B2B licensing. Custom contracts. CoreLogic (now rebranded as Cotality) provides data to many consumer platforms.

**Coverage:** 99.9%+ of US residential properties.

---

### 1.7 ATTOM Data

**Platform Overview:**
ATTOM is a comprehensive property data provider (not a consumer-facing tool). It powers many downstream analytics platforms and investment tools.

**Data Scale:**
- 158M+ US residential and commercial properties (99% of population)
- 70 billion+ rows of transactional data
- 9,000+ discrete data attributes
- 30TB data warehouse

**Products:**
| Product | Description |
|---------|-------------|
| Property Data API | REST API (JSON/XML), real-time access |
| ATTOM Nexus | Interactive data exploration platform |
| Bulk Data | Full dataset delivery |
| Cloud Delivery | Cloud-based data access |
| Property Reports | Individual property reports |
| Market Reports | Area-level market analytics |

**Data Categories:**
Property tax, deed, mortgage, foreclosure, valuation, climate change risks, hazard, school district, boundaries, neighborhood demographics.

**Pricing:**
- API: Starting ~$95-500/month depending on scale
- Enterprise: Custom contracts, typically $500+/month
- Bulk data: Negotiated pricing

---

### 1.8 Reonomy -- Commercial RE Analytics

**Technology:**
Reonomy is an AI-powered commercial real estate (CRE) intelligence platform using proprietary algorithms and machine learning. It consolidates public and private data sources at the parcel level using unique property identification strings (the "Reonomy ID").

**Data Coverage:**
- 54M+ commercial parcels across all 50 US states
- 100+ data points per property
- Sales, debt, tax history, ownership details
- Tenant and occupancy data

**Key Features:**
- "Likelihood to Sell" predictive indicator
- Ownership chain mapping (including LLCs and entity structures)
- Opportunity zone status
- Renovation tracking
- Salesforce integration
- API access

**Pricing:**
- Individual: ~$49/month (basic)
- Professional: ~$299+/month (advanced filters, tenant data)
- Enterprise: Custom pricing (API access, team features)
- 7-day free trial available

---

## 2. Automated Valuation Models (AVM) -- Deep Dive

### 2.1 How Modern AVMs Work

Modern AVMs combine three foundational approaches, increasingly augmented by machine learning:

#### A. Comparable Sales Approach (Sales Comparison)
The AVM identifies recently sold properties similar to the subject property and adjusts for differences. This is the digital equivalent of a traditional CMA (Comparative Market Analysis).

**Process:**
1. Select comparable properties (geographic proximity, similar characteristics)
2. Adjust prices for differences (size, age, condition, features)
3. Weight comparables by similarity and recency
4. Derive estimated value

#### B. Hedonic Pricing Model
Decomposes property value into constituent characteristics via regression analysis. Each feature (square footage, bedrooms, pool, garage) gets an estimated "price contribution."

**Mathematical Foundation:**
```
Price = B0 + B1(sqft) + B2(bedrooms) + B3(lot_size) + B4(age) + B5(location_score) + ... + e
```

Modern implementations use non-linear variants (polynomial, spline) and spatial adjustments (Geographically Weighted Regression / GWR).

#### C. Machine Learning Ensemble Methods
State-of-the-art AVMs use gradient-boosted decision trees (GBDT) as their primary model:

**Dominant Algorithms:**
- **LightGBM** -- Microsoft's GBDT framework (used by Cook County, many production AVMs)
- **XGBoost** -- Often outperforms other methods in benchmarks
- **CatBoost** -- Strong on categorical features
- **Random Forest** -- Robust baseline
- **Neural Networks** -- Used by Zillow (deep learning variant)

**Why GBDTs Dominate:**
- Handle categorical features natively
- Capture non-linear relationships and feature interactions
- Robust to missing data
- Fast training and inference
- Interpretable via SHAP values

#### D. Emerging: Multi-Modal Fusion
Cutting-edge research (2025) integrates:
- **Computer vision** features from property photos (condition, style, quality)
- **NLP** features from listing descriptions
- **Geospatial** features (proximity to amenities, transit, schools)
- **Late fusion** approach: extract embeddings from each modality, then feed into tree-based models

Research shows that incorporating multi-source image features improves accuracy significantly, with half of the top 10 significant features being image-based in recent studies.

### 2.2 Data Inputs for Modern AVMs

| Category | Specific Data Points |
|----------|---------------------|
| **Property Physical** | Square footage, lot size, bedrooms, bathrooms, stories, garage, pool, year built |
| **Transaction History** | Prior sales prices and dates, listing history, days on market |
| **Tax & Assessment** | Assessed value, property tax amounts, assessment history |
| **Location** | Latitude/longitude, neighborhood, school district, zip code |
| **Spatial Features** | Distance to transit, parks, water, commercial areas, highways |
| **Market Trends** | Area price trends, inventory levels, absorption rates, seasonality |
| **Environmental** | Flood zone, wildfire risk, climate hazard scores |
| **Demographics** | Median income, population density, crime rates |
| **Visual (emerging)** | Property photos (condition, style, quality via CV), satellite/aerial imagery |
| **Text (emerging)** | Listing descriptions parsed via NLP |

### 2.3 Accuracy Benchmarks

| AVM Provider | On-Market Median Error | Off-Market Median Error |
|-------------|----------------------|------------------------|
| Zillow Zestimate | 1.83% | 7.01% |
| Redfin Estimate | 1.98% | 7.72% |
| HouseCanary | 2.7% (post-list) | 7.5% (pre-list) |
| CoreLogic Total Home ValueX | Not publicly disclosed | Not publicly disclosed |
| Traditional Appraisal | ~3-5% (benchmark) | ~3-5% (benchmark) |

**Key Insight:** On-market accuracy (~2%) is dramatically better than off-market (~7%) because listing price provides a strong signal. The real challenge -- and where most value lies -- is accurate pre-list/off-market valuation.

### 2.4 Limitations and Edge Cases

1. **Data Scarcity** -- Rural areas, unique properties, new construction with few comparables
2. **Property Condition** -- AVMs cannot see deferred maintenance, damage, or recent renovations (mitigated partially by computer vision)
3. **Rapid Market Shifts** -- Models trained on historical data lag behind sudden market changes
4. **Non-arm's-length Transactions** -- Family transfers, distressed sales, and foreclosures pollute training data
5. **Unique Properties** -- Architectural uniqueness, historical significance, waterfront premiums are hard to model
6. **Zoning/Entitlements** -- Development potential is not captured
7. **Bias** -- Historical appraisal biases can be encoded in training data (HouseCanary actively monitors for this)

### 2.5 Best Open-Source Implementations

#### A. Cook County Assessor's Office AVM (GitHub: ccao-data/model-res-avm)
- **Language:** R
- **Model:** LightGBM
- **Coverage:** All class 200 residential properties in Cook County, IL
- **Features:** SHAP explanations, fairness monitoring, full reproducibility
- **Data:** Public via Cook County Open Data Portal
- **URL:** https://github.com/ccao-data/model-res-avm

Also available: `model-condo-avm` for condominiums.

#### B. OpenAVMKit (GitHub: larsiusprime/openavmkit)
- **Language:** Python
- **Models:** MRA, GWR, LightGBM, XGBoost, CatBoost (unified interface)
- **Features:**
  - Data cleaning and enrichment pipelines
  - Geographic feature enrichment from OpenStreetMap
  - Building footprints from Overture Maps
  - US Census statistics integration
  - USGS topography data
  - IAAO-compatible ratio study reporting (PDF/HTML)
  - Ensemble multiple models
- **URL:** https://github.com/larsiusprime/openavmkit

#### C. Academic Implementations
- **jayshah5696/AutomaticValuationModel** -- Basic AVM using Python ML libraries
- **Linhkust/ML-based-AVM** -- Code for "Machine-learning-based Automated Residential Property Valuation" paper

#### D. Key Research Papers
- "Learning Real Estate Automated Valuation Models from Heterogeneous Data Sources" (2019) -- arXiv:1909.00704
- "Real estate valuation with multi-source image fusion and enhanced machine learning pipeline" (2025) -- PLOS ONE
- "Automated land valuation models: A comparative study of four ML and DL methods" (2024) -- ScienceDirect
- Brookings Institution: "Governing the Ascendancy of Automated Valuation Models" (2023)

---

## 3. Auction/Foreclosure Analytics

### 3.1 Major Platforms

#### Auction.com
**Position:** Largest US online foreclosure auction platform (~13,000+ properties at any time).

**Technology & Analytics:**
- **AuctionSync** -- Digitized foreclosure auction platform capturing real-time bidding data
- **Portfolio Interact** -- Business intelligence dashboard for institutional sellers with asset-level detail and smart analytics
- **Bid Interact** -- Real-time auction status updates for buyers
- **Remote Bid** -- Nationwide remote bidding capability
- **Auction Market Dispatch** -- Quarterly report based on proprietary inventory, bidding, pricing, and survey data

**Data Scale:** Analyzed 390,000+ distressed property dispositions (2018-2025).

**Key Finding (2025):** Distressed property auctions outperform traditional REO (Real Estate Owned) sales in terms of recovery rates for sellers.

#### Hubzu
**Position:** Major online auction platform for foreclosed and bank-owned properties.
- Online auction format with extended bidding
- Property detail pages with comparables
- Operated by Altisource Portfolio Solutions
- Targets both investors and owner-occupant buyers

#### RealtyTrac (by ATTOM)
**Position:** Comprehensive foreclosure listing and analytics database.
- Partners with 6 largest online auction companies (including Auction.com and Hubzu)
- Property-level data: bedrooms, bathrooms, sqft, lot size, year built, owner info, debt
- Advanced search tools with geographic filtering
- Profit potential estimation using ATTOM and Zillow valuations
- Sales/tax history, foreclosure status tracking

### 3.2 Price Discovery Mechanisms

**Auction Types:**
1. **Foreclosure Auction (Trustee Sale)** -- Held on courthouse steps or online. Minimum bid = outstanding mortgage balance. Cash only.
2. **REO Auction** -- Bank-owned properties listed on auction platforms. More buyer-friendly (financing possible).
3. **CWCOT (Claims Without Conveyance of Title)** -- HUD/FHA properties auctioned pre-REO.

**Pricing Analytics:**
- Automated comparable analysis (what similar non-distressed properties sell for)
- Historical bidding pattern analysis (Auction.com captures all bid data)
- Market discount modeling based on property condition, location, title issues
- Institutional sellers use Portfolio Interact dashboards to validate pricing

### 3.3 Discount to Market Value

| Property Category | Typical Discount |
|-------------------|------------------|
| All foreclosure auctions (average) | ~14% below market value |
| Abandoned properties (built 1950-1990, underwater mortgages) | ~28% below market |
| Occupied foreclosures (equity positive) | ~26% below market |
| Bank-owned (REO) properties | ~3% ABOVE market (premium) |
| Zillow's research (precise methodology) | ~7.7% median discount |
| Academic research (Massachusetts study) | ~27% below comparable |

**Key Trend (2025):** Foreclosure discounts are narrowing. Properties now sell at ~86% of market value, up from ~77% just 12 months prior. The market is becoming more efficient and competitive.

**Q1 2025 Volume:** Foreclosure auction volume hit a six-quarter high, increasing 4% annually, with approximately 19% increase to two-year highs in subsequent quarters.

---

## 4. PropTech Trends 2025-2026

### 4.1 Market Size & Investment

| Metric | Value |
|--------|-------|
| PropTech VC investment (2025) | $16.7B (+67.9% YoY) |
| PropTech VC (Jan 2026) | $1.7B (+176% vs Jan 2025) |
| AI-centered PropTech growth rate | 42% annualized (2025) |
| Non-AI PropTech growth rate | 24% annualized (2025) |
| Global AI in PropTech market (2023) | $20.5B |
| Projected (2033) | $159.9B (CAGR 22.8%) |
| RE firms planning AI investment increase by 2026 | 72%+ |

### 4.2 AI/ML in Real Estate Valuation

**Current State:**
- Neural networks power Zillow's Zestimate (primary model)
- Gradient-boosted trees (LightGBM/XGBoost) dominate institutional AVMs
- Multi-modal fusion (text + images + structured data) is the frontier
- Transfer learning from ImageNet/CLIP for property photo analysis

**Trends:**
1. **Foundation models for real estate** -- Large language models being fine-tuned on property descriptions, appraisal reports, and market narratives
2. **Spatial transformers** -- Attention-based models processing geographic contexts
3. **Explainable AI (XAI)** -- SHAP values becoming standard for regulatory compliance
4. **Fairness monitoring** -- Monthly bias audits (HouseCanary leads here)
5. **Real-time inference** -- Moving from batch valuation to streaming/on-demand

### 4.3 Computer Vision for Property Assessment

**Key Players:**
| Company | Focus | Funding |
|---------|-------|---------|
| **ZestyAI** | Property-level risk assessment using CV + aerial imagery | $33M Series B |
| **Restb.ai** | Visual property intelligence (room detection, condition) | Leading RE CV provider |
| **Cape Analytics** | Aerial imagery analysis for property attributes | Competitor to ZestyAI |
| **FurtherAI** | Insurance workflow automation with CV | $25M Series A |
| **HouseCanary** | Photo-based condition assessment integrated into AVM | N/A (built-in) |

**Applications:**
- **Property condition scoring** from listing photos (detecting wear, outdated features, renovations)
- **Aerial/satellite imagery** analysis for roof condition, lot features, structural changes
- **Floor plan digitization** and room classification
- **Construction progress monitoring** from drone/satellite feeds
- **Insurance underwriting** with property-level risk models

**Market:** Companies at the intersection of RE, construction, insurance, and financial operations raised ~$2.1B globally in 2025 (+38% YoY).

### 4.4 Market Prediction Models

**Approaches:**
1. **Time series forecasting** -- ARIMA, Prophet, LSTM for price trajectory prediction
2. **Market cycle detection** -- Clustering algorithms identifying boom/bust phases
3. **Supply-demand modeling** -- Combining construction permits, inventory, migration data
4. **Sentiment analysis** -- NLP on news, social media, Fed statements
5. **Agent-based models** -- Simulating buyer/seller behavior under different scenarios

**Notable Tool:** Cushman & Wakefield launched (Feb 2026) CRE's first model designed to quantify "AI momentum" across the built environment -- measuring how AI-driven demand (data centers, tech offices) affects commercial real estate values.

### 4.5 Notable Startups (2025-2026)

| Startup | Focus | Valuation/Funding | Key Innovation |
|---------|-------|-------------------|----------------|
| **EliseAI** | AI-powered property management | $2.2B (Series E, $250M) | Conversational AI for leasing and operations |
| **Keyway** | AI underwriting for CRE investors | Significant VC backing | Automated deal sourcing and analysis |
| **Entera** | AI-driven residential investment | Notable funding | Portfolio management for institutional buyers |
| **Ridley** | ML-automated home selling | Early stage | Bypass agent commissions, shorten TTM |
| **ZestyAI** | CV-based property risk assessment | $33M+ | High-res aerial imagery + climate risk |
| **Restb.ai** | Computer vision for RE | Established | Industry-standard photo analysis API |
| **HouseCanary** | Professional AVM + analytics | Major platform | Best-in-class pre-list valuation |

**New Proptech Unicorns (since mid-2025):** Three new unicorns minted, all offering AI solutions for RE automation.

---

## 5. UK & European Platforms

### 5.1 UK

**Major Platforms:**

| Platform | Type | Key Feature |
|----------|------|-------------|
| **Zoopla** | Listings + Valuations | Instant online home valuation tool; 30% YoY increase in valuation leads (Jan 2026) |
| **Rightmove** | Listings + Valuations | Online Agent Valuation product (launched late 2025); 50% increase in valuation leads (Jan 2026 vs Jan 2025) |
| **PropertyData.co.uk** | Analytics | Aggregates listings from Rightmove, Zoopla, OnTheMarket; near real-time updates; analytics on price trends, planning, growth, demographics |
| **HM Land Registry** | Official Records | Official transaction data, Price Paid Data (PPD) |

**UK PropTech Ecosystem:**
- 749 active PropTech companies in the UK
- $1.68B raised (2020-2024)
- Both Rightmove and Zoopla are expanding AI-powered valuation tools

**Data Sources (UK):**
- HM Land Registry (transaction data, title records)
- Ordnance Survey (geographic data)
- Energy Performance Certificates (EPC)
- Council Tax bands
- Planning permission records

### 5.2 Europe

| Platform | Country | Focus |
|----------|---------|-------|
| **SeLoger** | France | Leading property portal |
| **Hemnet** | Sweden | Dominant listings platform |
| **Casavo** | Italy/Spain | iBuyer + instant valuation |
| **ImmoScout24** | Germany | Largest German property portal with AVM |
| **Idealista** | Spain/Portugal/Italy | Leading Southern European portal |
| **PriceHubble** | Switzerland (pan-European) | AI-powered property valuation and market insights for 10+ countries |

---

## 6. Sources

- [Zillow Zestimate -- How It Works](https://www.zillow.com/z/zestimate/)
- [Zillow Estimates Accuracy in 2026](https://agentsgather.com/zillow-estimates-how-accurate-are-zestimates-in-2026/)
- [How Reliable is Zestimate in 2026 -- iBuyer](https://ibuyer.com/blog/how-reliable-is-the-zestimate/)
- [Redfin vs Zillow Estimate Comparison](https://www.realestatewitch.com/redfin-vs-zillow-estimators/)
- [Redfin vs Zillow 2026 -- RealEstateSkills](https://www.realestateskills.com/blog/redfin-vs-zillow)
- [How Accurate Is Redfin Estimate -- Clever](https://listwithclever.com/real-estate-blog/how-accurate-is-a-redfin-home-value-estimate/)
- [HouseCanary -- Our AVM](https://www.housecanary.com/resources/our-avm)
- [HouseCanary -- AVM Explained](https://www.housecanary.com/blog/automated-valuation-model)
- [HouseCanary -- AVM Accuracy Guide](https://www.housecanary.com/blog/real-estate-avm-accuracy)
- [CoreLogic Total Home ValueX](https://www.corelogic.com/mortgage/origination-solutions/total-home-value-x/)
- [CoreLogic New AVM Launch -- HousingWire](https://www.housingwire.com/articles/total-home-valuex-from-corelogic-leverages-machine-learning-to-simplify-and-standardize-valuation/)
- [ATTOM Data Platform](https://www.attomdata.com/)
- [ATTOM API Pricing 2025](https://www.oreateai.com/blog/navigating-attom-property-data-api-pricing-what-to-expect-in-2025/93f3bc3903fa16dfc88c8413cc63ce42)
- [Reonomy Platform](https://www.reonomy.com/)
- [Reonomy 2026 Review -- CRE Daily](https://www.credaily.com/reviews/reonomy-review/)
- [Reonomy -- AI CRE Tools](https://www.aicretools.com/reonomy)
- [Trulia Estimates](https://www.trulia.com/info/trulia-estimates/)
- [Realtor.com Home Value Estimators -- FastExpert](https://www.fastexpert.com/blog/best-accurate-home-value-estimators/)
- [Cook County AVM (GitHub)](https://github.com/ccao-data/model-res-avm)
- [OpenAVMKit](https://github.com/larsiusprime/openavmkit)
- [OpenAVMKit Announcement](https://progressandpoverty.substack.com/p/openavmkit-a-free-and-open-source)
- [AVM Heterogeneous Data -- arXiv](https://arxiv.org/pdf/1909.00704)
- [Multi-source Image Fusion AVM -- PLOS ONE](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0321951)
- [Hedonic Pricing Models -- Cornell](https://ecommons.cornell.edu/items/2139e30d-1a98-4fe4-80a3-e9b468c749be)
- [Brookings -- Governing AVMs](https://www.brookings.edu/wp-content/uploads/2023/10/BR-AVM_report_Finalx2.pdf)
- [Auction.com Platform](https://www.auction.com)
- [Auction.com Market Dispatch Q2 2025](https://www.auction.com/lp/auction-market-dispatch-2025-q2/)
- [Distressed Auctions Outperform -- HousingWire](https://www.housingwire.com/articles/distressed-auctions-outperform-2025/)
- [RealtyTrac](https://www.realtytrac.com/)
- [Hubzu](https://www.hubzu.com/)
- [Foreclosure Discount -- Zillow Research](https://www.zillow.com/research/whats-the-real-discount-on-a-foreclosure-3229/)
- [Foreclosure Auction Prices -- HomeLight](https://www.homelight.com/blog/buyer-how-much-do-foreclosed-homes-sell-for-at-auction/)
- [PropTech Trends 2025-2026](https://www.smartconnectionspr.com/news/current-future-proptech-trends-2025-2026/)
- [PropTech Investment Trends 2026](https://qubit.capital/blog/proptech-investment-landscape)
- [PropTech Unicorns -- Bisnow](https://www.bisnow.com/national/news/proptech/the-4-newest-proptech-unicorns-show-ais-increasing-role-in-real-estate-133304)
- [PropTech & AI -- PWC](https://www.pwc.com/us/en/industries/financial-services/asset-wealth-management/real-estate/emerging-trends-in-real-estate-pwc-uli/trends/proptech-impact.html)
- [RE Tech Funding Rebound -- Crunchbase](https://news.crunchbase.com/real-estate-property-tech/rebound-ai-fintech-data-eoy-2025/)
- [Visual AI in CRE -- Commercial Observer](https://commercialobserver.com/2025/12/visual-ai-value-risk-commercial-real-estate/)
- [Restb.ai](https://restb.ai/)
- [CV in Real Estate -- CRETI](https://creti.org/insights/computer-vision-the-quiet-infrastructure-shift-transforming-real-estate)
- [AI in Real Estate 2025 -- RTS Labs](https://rtslabs.com/ai-in-real-estate/)
- [Cushman AI Momentum Model](https://www.cushmanwakefield.com/en/united-states/news/2026/02/launches-cre-first-model-designed-to-quantify-ai-momentum-across-built-environment)
- [Zoopla](https://www.zoopla.co.uk/)
- [Rightmove Valuation Leads -- BeBeez](https://bebeez.eu/2026/02/20/rightmove-reports-surge-in-property-valuation-leads-to-agents/)
- [PropertyData UK](https://propertydata.co.uk/)
- [UK PropTech Overview](https://www.propertynotify.co.uk/news/featured/what-is-proptech-and-how-is-it-reshaping-property-investment/)

---

*Report compiled March 2026. Data and accuracy metrics are subject to change as platforms update their models.*
