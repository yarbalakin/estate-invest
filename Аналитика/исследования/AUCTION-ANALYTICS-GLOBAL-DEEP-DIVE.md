# Global Auction & Distressed Property Analytics: Deep Dive Report

**Date:** 2026-03-01
**Purpose:** Technical research for building a Russian distressed property analytics product
**Scope:** US, UK, Germany, Australia + scoring models, real-time intelligence, UX patterns

---

## Table of Contents

1. [US Foreclosure Analytics](#1-us-foreclosure-analytics)
2. [UK Auction Market](#2-uk-auction-market)
3. [Germany Zwangsversteigerung](#3-germany-zwangsversteigerung)
4. [Australia — Auction Capital of the World](#4-australia--auction-capital-of-the-world)
5. [Distressed Property Scoring Models](#5-distressed-property-scoring-models)
6. [Real-Time Auction Intelligence](#6-real-time-auction-intelligence)
7. [Best UX Patterns for Auction Analytics](#7-best-ux-patterns-for-auction-analytics)
8. [Key Takeaways for a Russian Product](#8-key-takeaways-for-a-russian-product)

---

## 1. US Foreclosure Analytics

The US has the most mature and technologically advanced ecosystem for distressed property analytics, driven by the massive 2008-2012 foreclosure wave that created billion-dollar data companies.

### 1.1 Auction.com — The Platform Leader

**URL:** https://www.auction.com
**Scale:** 115,000+ homes sold since 2015, $33M+ in single demo events
**Market share:** Runs >50% of all CWCOT (Claims Without Conveyance of Title) auctions for FHA

#### AuctionSync Technology

AuctionSync is Auction.com's proprietary system that **digitizes live foreclosure auction events** by capturing bidding data electronically. Before AuctionSync, foreclosure auctions were offline events with zero data capture.

**What AuctionSync captures:**
- Electronic bidding data from live events (previously impossible to track)
- Bidding behavior patterns per property and per bidder
- Bid increment tracking (how much buyers jump between bids)
- Registration data linked to bidder profiles
- Venue-level activity and property tracking

**How they predict auction outcomes:**
- Regression-based forecasting model
- Primary inputs: home price appreciation (HPA) + unemployment rates
- Unemployment is imputed from seriously delinquent mortgage rates (a leading indicator)
- Model produces baseline, upside, and downside scenarios
- Q3 2025 result: completed foreclosure auctions increased 31% to a 10-quarter high

#### Portfolio Interact — BI Dashboard for Sellers

Portfolio Interact is a **real-time business intelligence dashboard** for institutional sellers (banks, servicers, GSEs):

**Core features:**
- **Asset-level detail**: Individual property performance metrics
- **Portfolio reporting**: Aggregated views across entire distressed portfolios
- **Smart analytics**: Trend identification and opportunity discovery
- **Multiple data filters**: Narrow datasets to identify patterns
- **Pricing Optimization**: Review priority assets, validate pricing with market intelligence
- **Reserve vs. Market Value comparison**: Quickly find assets with reserves exceeding market value
- **"Bids within range" alerts**: Identify assets close to selling

#### Bid Interact — Real-Time Auction Control

Bid Interact sits within Portfolio Interact and enables:
- **Real-time monitoring** of REO auctions as they happen
- **Instant reserve changes** during live auctions with one click
- **Live bid acceptance** — sellers can accept a bid in real-time
- **Bidding history + value data** displayed in one interface
- **796% increase in client usage** from Nov 2018 to Oct 2019
- **5,500+ pricing actions** taken since inception

#### Foreclosure Interact — Mobile App for Buyers

- Real-time auction status updates
- Property tracking by venue
- Notification of cleared/canceled properties
- Mobile-first bidder experience

#### CWCOT Program Data

Between 2021-2024:
- 67% of CWCOT properties sold on Auction.com were foreclosure auction sales (~20,000 properties)
- Average time from foreclosure to resale: **319 days** (CWCOT) vs. **785 days** (traditional REO)
- Saved FHA's MMI Fund an estimated **$10 billion** vs. traditional REO conveyance

**Key insight for Russian product:** Auction.com proves that digitizing offline auction events creates a massive data moat. The combination of AuctionSync (data capture) + Portfolio Interact (BI) + Bid Interact (real-time control) is the gold standard.

---

### 1.2 ATTOM Data (formerly RealtyTrac) — The Data Infrastructure

**URL:** https://www.attomdata.com
**API docs:** https://api.developer.attomdata.com/docs
**Scale:** 158+ million US properties, 99% population coverage, 20+ years of data

#### Foreclosure Pipeline Tracking

ATTOM tracks the **complete foreclosure lifecycle** through document-level data:

```
PRE-FORECLOSURE          AUCTION                    POST-AUCTION
├─ NOD (Notice of        ├─ NTS (Notice of          ├─ REO (Bank-owned)
│  Default)              │  Trustee's Sale)         ├─ Resale data
├─ LIS (Lis Pendens)     ├─ NFS (Notice of          └─ Deed transfer
│                        │  Foreclosure Sale)
└─ Default amounts       └─ Opening bids
```

#### Data Fields per Foreclosure Record

**Document-level data:**
- Notice type (NOD, LIS, NTS, NFS, REO)
- Recording date and published date
- Default amount
- Foreclosing lender and servicer details

**Auction-level data:**
- Auction dates
- Opening bids
- Sale amounts
- Trustee information
- Case numbers

**Property-level data (enriched):**
- Property features and addresses
- Ownership details
- Property taxes
- Sales/transfer/mortgage history
- Property valuations (AVM)
- Neighborhood data (schools, crime, etc.)

#### API Architecture

- REST API supporting JSON and XML
- Persistent **ATTOM ID** for each property (cross-dataset linking)
- Enterprise Data Management Program (EDMP): multi-step validation, standardization, enrichment
- Key endpoints: `/property`, `/sale`, `/saleshistory`, `/assessment`, `/attomavm`, `/salestrend`
- Foreclosure-specific endpoints available through the full API suite

#### ATTOM's Foreclosure Activity Report

Published monthly, tracks:
- Default notices filed (pre-foreclosure starts)
- Scheduled auctions
- Completed foreclosures (REO)
- Year-over-year trends by state, metro, county
- Foreclosure rate per housing unit

**Key insight for Russian product:** ATTOM's persistent property ID and document-level pipeline tracking is the foundation everything else is built on. For Russia, this means tracking FSSP (bailiff service) records, court decisions, and Rosreestr data with a unified property ID.

---

### 1.3 PropertyRadar — The Filter/Signal Leader

**URL:** https://www.propertyradar.com
**Scale:** 160M+ properties nationwide, originally California-only
**Criteria glossary:** https://help.propertyradar.com/en/articles/2507682-criteria-glossary-2007-2025

#### The 285+ Search Criteria (Complete Taxonomy)

PropertyRadar's power is in its **filter depth**. Here is the complete category structure:

**1. Location (15+ filters)**
- State, County, City, ZIP, Address, APN
- Advanced: FIPS Code, Census Tract, Congressional District, Carrier Route, Tax Rate Area
- Map tools: Polygon, Rectangle, Radius, Entire Map

**2. Property (30+ filters)**
- Type, Owner Occupied, Beds, Baths, Year Built, Age, SqFt, Lot Size
- Pool, Units, Vacant Site
- Structure: Rooms, Stories, Fireplace, AC, Heating, Garage, Basement, Construction Type, Roof, Exterior Wall
- Flood Zone Code, Flood Risk
- Zoning, View Type

**3. Owner (35+ filters)**
- Name, Properties Owned Count, Deceased
- Contact: Phone, Mobile, Email, DNC status
- Demographics: Age, Gender, Marital Status, Children, Birth Month, Ethnicity, Language, Education Level
- Financial: Household Income, Net Worth, Occupation, Business Owner
- Legal: Bankruptcy (status, date, chapter, district), Divorce (recording date, decree date)
- Interests, Charitable Giving

**4. Value & Equity (10+ filters)**
- Estimated Value, Est. Value/SqFt
- Estimated Equity $ and %
- Combined Loan to Value (CLTV)
- Open Loans Balance
- HUD Fair Market Rent
- Estimated Cap Rate, Cash Return

**5. Property Tax (8+ filters)**
- Assessed Value, Assessed/Estimated ratio
- Land vs. Improvements split
- Annual Taxes, Estimated Tax Rate
- Homeowner Exemption
- **Tax Delinquent status, Years Delinquent, Delinquent Amount**

**6. Loans & Liens (50+ filters per loan position)**
- Estimated Open Loans count
- First/Second/Other Loan: Purpose, Type, Date, Amount, LTV, Term, Lender
- ARM details: Index, Margin, Adjustment Frequency, Reset dates, Prepay Rider, Interest Only, Negative Amortization
- Liens: Recording Date, Type, Position, Status, Amount, Rate

**7. Foreclosure (25+ filters)**
- In Foreclosure (yes/no), Foreclosure Stage
- Notice: Document Type, Recording Date, Published Date
- Sale Tracking: Sale Date, Prior Sale Date, Postponed count, Opening Bid $, Opening Bid/Est Value, Winning Bid
- Notice of Sale: Original Sale Date, Time, Place, Published Bid, Published Bid/Est Value
- Notice of Default: Default Amount, Default Date
- Foreclosing Loan: Position, Amount, Date, Lender Name
- Trustee/Attorney: Name, Phone, TS Number, Case Number

**8. Transfer (20+ filters)**
- Purchase Date, Type, Document Type, Amount, Seller, Percent Down
- Purchase Amount Change $ and %
- Months Since Prior Sale
- Transfer details: Cash Transfer, Was Listed, Multiple Parcels, Buyer/Seller Names, Title Company

**9. Listing (10+ filters)**
- Listed for Sale, Status (Active, Contingent, Pending, Sold, Withdrawn, Expired, Canceled)
- **Listing Type**: Market, REO, Shortsale, QuickSale, Distressed, Non-Market, **Auction**, Unknown
- List Price, Price Reduced, **Discount to Estimated Value**
- Days on Market, Listing Date

**10. My Data (custom)**
- Status tags, Interest Level, Notes, Photos, Documents
- List membership (In Any List, In All Lists, Exclude)

#### Heatmaps

Color-coded map overlays visualizing:
- Property value distribution
- Length of ownership patterns
- Owner age demographics
- Real estate turnover rates
- Distress concentration areas

#### Signal Engine (Event-Driven Alerts)

PropertyRadar's "Signals" feature watches for property-level events in real-time:
- New foreclosure filings
- Listing status changes
- Mortgage activity changes
- Ownership transfers
- Tax delinquency triggers

**Automation:** When a signal fires, it can automatically trigger:
- Direct mail postcards
- Email campaigns
- SMS messages
- Phone call lists
- Online ad audience updates

#### How They Went from 1 State to Nationwide

PropertyRadar started as a **California-only** tool with deep county recorder data. Their expansion strategy:
1. **County-level data acquisition**: Each state's data is shown by county with earliest available dates
2. **Data sources vary by coverage**: Assessor records, recorded documents, foreclosure data, trustee sale tracking, for-sale listings, parcel boundaries
3. **Not all data available everywhere**: Some counties have data back to 1990s, others only recent years
4. **Continuous backfill**: Data is "acquired daily, backfilled, backtested, cleaned, and enhanced"

**Key insight for Russian product:** PropertyRadar's 285+ filters demonstrate that depth wins. For Russia, equivalent filters would be: FSSP proceedings, tax debts (FNS), utility debts, ownership duration, multiple property ownership, cadastral value vs. listing price, etc.

---

### 1.4 Sundae — Marketplace Model

**URL:** https://sundae.com
**Funding:** $36M+ raised (TechCrunch, 2020)

#### How Their Pricing Works

Sundae is NOT a direct buyer. It's a **marketplace** connecting distressed sellers with investors:

1. **Market Expert visit**: Local professional inspects property in person
2. **Offer range estimate**: Based on neighborhood comps, property condition, market research
3. **Marketplace listing**: Property goes to investor pool
4. **Multiple bids**: Average 9 investor offers, up to 22+
5. **No guarantee**: Initial estimates are not binding; final price depends on marketplace bids

**Fee structure:**
- $1,000 admin fee deducted from sale
- 5-7% buyer premium (paid by investor, not seller)
- Zero seller commission

**Key insight for Russian product:** The marketplace model (connecting distressed sellers with multiple investors) creates price discovery and transparency. This could work for bankrupt property in Russia where current processes are opaque.

---

### 1.5 Xome — Servicer-Owned Platform

**URL:** https://www.xome.com
**Owner:** Mr. Cooper Group (formerly Nationstar)
**Scale:** 115,000+ homes sold since 2015, inventory peaked at ~30,000

#### Key Features

- **DIY sales platform**: Launched 2024, lets investors sell homes without an agent
- **Integrated with Mr. Cooper servicing**: Direct pipeline from mortgage default to auction
- **Virtual Auction Game**: Gamification of the auction experience (launched 2023)
- **Mixed inventory**: Foreclosures, bank-owned, and traditional MLS listings
- **Revenue**: $60M in first 9 months of 2024

**Key insight for Russian product:** Xome shows that a mortgage servicer can build its own auction platform. In Russia, banks like Sberbank and VTB have similar distressed portfolios but no dedicated marketplace technology.

---

## 2. UK Auction Market

The UK auction market is smaller but highly structured, with ~40,000+ lots per year and strong data tracking traditions.

### 2.1 Essential Information Group (EIG) — The Authority

**URL:** https://www.eigpropertyauctions.co.uk
**Scale:** 600,000+ historical lots sold, 38,000+ lots added annually (worth GBP 4.7B+)

#### What EIG Tracks

EIG is the **only UK platform** providing information on every property coming to auction:
- Every lot offered (current and historical)
- Used by 120+ auctioneers
- Covers 70%+ of all lots offered in the UK

#### Technology Services

**SaleVision**: Display system for auction rooms showing:
- Lot details in real-time
- Current bid levels
- Internet broadcasting and live video streaming

**Auction Management System (AMS):**
- Data entry control panel for auctioneers
- Catalogue preview and PDF proof generation
- Client distribution system

**Online Auction Platform:**
- 66,000+ lots sold online
- 1,315,000+ bids placed
- 2,000,000+ legal documents downloaded annually

**Auction Passport**: Single sign-on system allowing buyers to bid across multiple auction houses with unified credentials.

**Bidder Registration**: Online identity verification for buyer authorization.

#### Data Fields per Lot

Based on EIG's tracking system:
- **Guide Price**: Auctioneer's estimate to attract interest
- **Reserve Price**: Minimum acceptable price (within +/- 10% of guide per ASA rules)
- **Sold Price**: Final hammer price
- **Premium/Discount**: Sold price vs. guide price ratio
- **Lot Status**: Sold, Withdrawn, Unsold
- **Auction House**: Which firm sold it
- **Property Type**: Residential, Commercial, Land, Development
- **Location**: Full address and region

---

### 2.2 Allsop — Largest UK Commercial Auctioneer

**URL:** https://www.allsop.co.uk
**Scale:** 667 properties sold in last 12 months, 31.2% market share (England & Wales)

#### How They Price Guide Lots

Allsop publishes catalogues 7 times per year with ~150 lots each, totaling ~GBP 100M per catalogue:
- Guide prices are based on comparable sales, location, and market conditions
- **90% of assets sell at or above guide price** (within 3 weeks post-auction)
- 2025 performance: 466 commercial lots, GBP 308M raised, 85% success rate

#### Technology

- Invested **GBP 1M+** pre-COVID into bespoke Auction Management System
- Powered by EIG technology infrastructure
- Online auctions increased frequency from 6 to 8 per year
- Database of **50,000+ investors** with transparent bidding visibility
- Real-time competitive pricing driven by visible buyer interest

#### Data for Russian Product

Allsop's transparency model is instructive:
- All bidders see what the next highest bidder offers
- Transparent pricing creates trust and higher participation
- Institutional investor database enables repeat engagement

---

### 2.3 iamsold — Modern Method of Auction (MMoA)

**URL:** https://www.iamsold.co.uk
**Scale:** 7,000+ estate agent branch partners, 10,000+ properties sold in 2023

#### Modern Method of Auction vs. Traditional

| Feature | Traditional Auction | Modern Method (iamsold) |
|---------|-------------------|----------------------|
| Timeline | 28 days to complete | 56 days to complete |
| Bidding | In-room or live online | Online 24/7 |
| Deposit | 10% on hammer fall | Reservation fee upfront |
| Legal packs | Required before auction | Prepared during process |
| Certainty | Exchange on hammer | Exchange within 28 days |

#### Technology Platform

- **24/7 online bidding** with bid limits and progress tracking
- **Secure platform** with identity verification
- **Agent integration**: 6,500+ branches use the system
- **Auction Passport**: Cross-platform buyer authentication

#### UK Guide Price → Sold Price Tracking

**Methodology (regulated by ASA since 2014):**
- Guide price must be within +/- 10% of reserve price
- Reserve is set by seller with auctioneer's advice

**Performance benchmarks:**
- Single-entry lots: average 120% of guide price (20% premium)
- Repeat lots (re-listed): stabilize around 100% of original guide
- SDL Auctions average: 16% premium above guide
- Industry average: 15-25% premium above guide price

**Key insight for Russian product:** The UK's ASA regulation of guide prices creates trust. Russia needs similar transparency — showing expected price vs. actual outcome builds credibility.

---

## 3. Germany Zwangsversteigerung

German forced auctions (Zwangsversteigerung) are **court-administered** through Amtsgericht (district courts) — a very different model from US/UK.

### 3.1 How German Court Auctions Work

#### Legal Framework (ZVG — Gesetz uber die Zwangsversteigerung)

```
Creditor files for     Court orders          Court-appointed appraiser    Auction at
forced sale at    →    Zwangsversteigerung →  determines Verkehrswert  →  Amtsgericht
Amtsgericht            proceedings            (market value)              (district court)
```

#### Critical Bidding Thresholds

- **Verkehrswert**: Court-determined market value (by certified appraiser)
- **50% threshold**: Minimum first bid = 50% of Verkehrswert (below this, any bidder can object)
- **70% threshold**: Below this, creditors can deny the award (Zuschlag)
- **No maximum**: Bids can exceed Verkehrswert

#### Auction Process

1. **Announcement**: Published 4-6 weeks before auction via ZVG-Portal
2. **Bietstunde**:30-minute minimum bidding period at the court
3. **Zuschlag**: Judge awards property to highest bidder
4. **Payment**: Full payment due within specified period (usually 4-6 weeks)
5. **Verteilungstermin**: Distribution of proceeds to creditors

### 3.2 ZVG-Portal — Official Government Platform

**URL:** https://www.zvg-portal.de
**Operated by:** Joint platform of German state justice administrations
**Live since:** March 1, 2007

#### Data Fields Published

- Amtsgericht (district court) name and location
- Aktenzeichen (case file number)
- Property type and address
- Verkehrswert (court-appraised market value)
- Auction date and time
- Property description
- Sometimes: photos and appraiser reports

**Limitations:** No historical results, no analytics, no price tracking. Pure announcement portal.

### 3.3 Zwangsversteigerung.de — Commercial Aggregator

**URL:** https://www.zwangsversteigerung.de
**Scale:** 3,700+ current auction properties from 500+ district courts

#### Search and Filter Capabilities

- **Location**: KFZ-Kennzeichen (license plate code), PLZ (postal code), city name, case number, UNIKA-ID
- **Property type**: Condominiums, single/double-family homes, commercial
- **Market value range**: EUR 0 to EUR 600,000+
- **Rooms**: 1-2 through 5+
- **Living space**: 40m2 to 120m2+
- **Repeat auction**: Yes/No filter
- **Historic preservation**: Yes/No filter

#### Premium Tools

- **Limit-Ermittler** (Limit Calculator): Calculates maximum bid based on renovation cost, expected resale value
- **Statistical archives**: Historical auction data
- **Expert appraiser directory**: Find certified property appraisers
- **Legal advisor network**: Auction-specialized lawyers

### 3.4 Argetra — Market Leader (Commercial)

**URL:** https://www.argetra.de
**HQ:** Ratingen, Germany

#### Premium Services

- **FullService subscription**: Complete property data with appraisals, exposees, original images
- **Personal search agent**: Daily email alerts for matching properties
- **Monthly foreclosure calendar**: Print/PDF with all regional auction dates
- **Forecasts**: Properties expected to come to auction up to 12 months ahead

#### ZVG-Datenanalyse (Analytics Subsidiary)

Argetra's analytics arm provides institutional clients (banks, insurers, real estate firms):
- **Market research**: Comprehensive foreclosure market analysis
- **Portfolio assessment**: Valuation of distressed property portfolios
- **Value adjustment modeling**: Price discovery factoring in procedure duration using **net present value** approach
- **Trend analysis**: Foreclosure volume trends and forecasts

### 3.5 Third-Party Data Tools

**ZVG-Portal Scraper (Apify):**
- URL: https://apify.com/signalflow/zvg-portal-scraper
- Automated extraction from official portal
- Outputs: Clean JSON/Excel/CSV
- Auto-calculates: 50% minimum bid, 70% creditor threshold
- Designed for: investors, Fix & Flip professionals, analysts

**Key insight for Russian product:** Germany's court-administered system is the closest analog to Russian bankruptcy auctions (torgi.gov.ru). The 50%/70% thresholds create natural "discount to value" metrics. A Russian tool should calculate similar thresholds from starting prices.

---

## 4. Australia — Auction Capital of the World

Australia is unique: **auctions are the primary method of residential property sale** (60%+ in Melbourne/Sydney), not just for distressed properties. This creates the world's richest auction analytics ecosystem.

### 4.1 CoreLogic / Cotality — Real-Time Tracking

**URL:** https://www.corelogic.com.au (now branded Cotality)
**Auction results:** https://www.cotality.com/au/our-data/auction-results
**Developer portal:** https://developer.corelogic.asia

#### Clearance Rate — The Key Metric

The auction clearance rate is Australia's **most-watched real estate indicator**, more influential than price indices.

**Calculation formula:**
```
Clearance Rate = (Properties sold at/before/after auction) / (Total known auction results)
                                                            including passed-in and withdrawn
```

**Reporting cadence:**
- **Sunday morning**: Preliminary results released (partial data)
- **Progressive updates**: Throughout the week as results are collected
- **Thursday**: Final clearance rate published
- CoreLogic collects **99% of all auction results** each week on average

**Preliminary vs. Final discrepancy:**
- Can differ significantly (e.g., preliminary 71.3% → final 65.3%)
- Historical data uses final rates; current week shows preliminary
- This discrepancy is itself a market signal

#### 2025 Performance Data

- 71.2% preliminary clearance rate (first time above 70% since September prior year)
- Weekly volumes: 1,700-2,000 homes per week in peak periods
- Melbourne: 845 homes per week at peak
- Sydney: 796 homes per week at peak

#### CLIP — Property Identification

Cotality's **CLIP (Cotality Integrated Property)** is a Machine Learning-driven record identifier:
- Uniquely identifies properties across vast datasets
- Enables cross-referencing auction results with property data
- Similar concept to ATTOM's persistent ID

#### RP Data Platform

CoreLogic's RP Data provides:
- Property-level auction results
- Historical auction performance
- Comparable sales data
- Automated valuation models
- Suburb-level analytics

### 4.2 SQM Research — Alternative Methodology

**URL:** https://sqmresearch.com.au
**Methodology:** https://sqmresearch.com.au/auctions_methodology.php

#### How SQM Differs from CoreLogic/Domain

SQM Research takes a fundamentally different approach:

| Aspect | CoreLogic/Domain | SQM Research |
|--------|-----------------|--------------|
| Reporting | Preliminary on Sunday | Single list on Tuesday |
| Data source | Agent-reported results | Monitoring listing changes |
| Auction universe | Confirmed auctions only | ALL scheduled auctions |
| Missing data | 0-1% missing | Catches 20-40% others miss |
| Method | Divide sold by reported | Divide sold by total listed |

**SQM's methodology:**
1. Monitor online listings from major providers weekly
2. Track ALL fields: address, type, agent, auction date/time
3. **Wait several days** until agents change advertisements to reflect outcomes
4. The advertisement status change IS the result confirmation
5. Count ALL scheduled auctions (not just agent-confirmed ones)

**Why this matters:** Domain's preliminary results divide sold by reported (excluding non-reported auctions). This can overstate clearance rates by 5-10 percentage points on weak weekends when agents don't report poor results.

### 4.3 Domain Auction Results

**URL:** https://www.domain.com.au

Domain provides:
- Weekly auction results by suburb
- Price tracking (guide estimate vs. sold price)
- Passed-in vs. sold statistics
- Agent performance data
- Suburb-level auction activity maps

### 4.4 Pre-Auction Analytics — Reserve Price Setting

Australia's pre-auction period (typically 3-4 weeks) generates unique analytics:

**Reserve price setting process:**
1. Agent conducts **comparative market analysis** (similar properties sold within 90 days)
2. During campaign, tracks **buyer interest**: inspections, inquiries, registrations
3. **48 hours before auction**: Agent + auctioneer meet vendor to set reserve
4. Reserve incorporates: comps, current competition, market trends, property condition, buyer registrations

**Pre-auction data signals:**
- Number of registered bidders (strong predictor of outcome)
- Inspection attendance
- Price guide requests from potential buyers
- Comparable recent sales
- Days on market for similar properties

**Emerging technology:**
- AI/ML models predicting bidder demand and willingness to pay
- Real-time reserve adjustments based on market conditions
- Predictive analytics from historical clearance rate patterns

### 4.5 Clearance Rate as Market Predictor

**How clearance rates predict market direction:**

```
Clearance Rate    Market Signal
>75%              Strong seller's market, prices rising
65-75%            Balanced market
55-65%            Cooling market, prices stabilizing
<55%              Buyer's market, prices likely falling
```

- Clearance rates are a **leading indicator** (predict price changes 1-3 months ahead)
- Weekly frequency gives much faster signals than monthly price indices
- Regional clearance rates identify micro-market divergences
- Seasonal patterns (winter dip, spring peak) must be normalized

**Key insight for Russian product:** Australia proves that auction data is a real-time market health indicator. Even for a non-auction market like Russia, tracking торги (auction) clearance rates for bankrupt/distressed property would provide unique market intelligence no one else offers.

---

## 5. Distressed Property Scoring Models

### 5.1 PropStream — Foreclosure Factor

**URL:** https://www.propstream.com
**Scale:** 160M+ property records

#### Foreclosure Factor Score

PropStream's core scoring model predicts likelihood of default within the next 12 months:

**Score range:** Very Low → Low → Medium → High → Very High

**Input data points:**
- Tax information
- Income sources
- Home values
- Loan structure
- Homeowner behavior patterns

**Performance metrics:**
- Focusing on scores **80+** captures **95.5%** of properties that will enter foreclosure (NOD or Lis Pendens) within 12 months
- This is remarkable accuracy for a predictive model

#### Property Condition AI

PropStream also uses photo-based AI:
- Analyzes MLS photos to assess property condition
- Based on **Fannie Mae's Appraisal characteristics**
- **99% accuracy** on photo analysis
- Scores: Exterior, Interior, Kitchen, Bathroom separately
- Uses this for "as-is" valuation

#### Wholesale Value Algorithm

- AVM machine-learning algorithm
- Set at **70% of AI-calculated estimated value**
- Quick deal valuation for wholesalers/flippers

### 5.2 BatchLeads — BatchRank (800+ Data Points)

**URL:** https://batchleads.io

#### BatchRank Scoring

- Analyzes **800+ data points** per property
- AI & ML algorithms rank properties by distress likelihood
- Identifies properties likely to sell at a discount (on-market or off-market)
- Designed for wholesalers and investors

**Deal conversion rates:**
- BatchLeads: ~1 deal per 250-300 records
- PropStream: ~1 deal per 400-500 records

### 5.3 Goliath Data — "David" Predictive Model

**URL:** https://goliathdata.com

#### David AI Model

Goliath's AI model "David" scores motivation by weighing:
- Ownership tenure
- Local market trends
- Payment delays
- Online activity signals
- Demographic indicators

**Performance:** ~1 deal per 75-100 records (highest conversion rate in the industry)

**Integration:** Feeds directly into nurturing workflows (automated outreach sequences)

### 5.4 HouseCanary — Propensity to Sell Model

**URL:** https://www.housecanary.com

#### Model Architecture

- Machine learning algorithms trained on massive historical datasets
- Iterative error minimization across many training cycles
- Inputs: public records, MLS data, proprietary sources

**Scoring output:**
- Probability scores from 0-100%
- Actionable range: **87-95%** scores for high-probability listings
- AVM accuracy: **3.1% median absolute percentage error**
- Sale price prediction: within **2.5% accuracy**

**Data quality:**
- Thousands of data sources, normalized and curated
- Both AI-driven and manual quality control
- Image recognition for property condition assessment

### 5.5 Datazapp — Seller Scores

**URL:** https://www.datazapp.com

Assigns seller scores from **1-100** based on ~25 data points:
- Individual factors
- Family/household factors
- Property characteristics
- Score indicates likelihood to sell within **6-12 months**

### 5.6 Generic Scoring Model Architecture

Based on published methodologies across platforms, a distressed property scoring model typically includes:

```
SCORING MODEL COMPONENTS
========================

1. FINANCIAL DISTRESS (Weight: 30-40%)
   ├── Mortgage delinquency status
   ├── Tax delinquency (years, amount)
   ├── Lien status and amounts
   ├── Negative equity indicators
   ├── Bankruptcy filings
   └── Foreclosure stage

2. OWNER MOTIVATION (Weight: 20-25%)
   ├── Length of ownership (5-7+ years = higher)
   ├── Absentee owner status
   ├── Divorce records
   ├── Death/probate records
   ├── Age (72+ = downsizing likelihood)
   └── Multiple property ownership

3. PROPERTY CONDITION (Weight: 15-20%)
   ├── Year built / age
   ├── Photo-based AI condition assessment
   ├── Permit history (recent work = better condition)
   ├── Code violations
   └── Vacancy indicators

4. MARKET CONTEXT (Weight: 15-20%)
   ├── Discount to estimated value
   ├── Days on market (if listed)
   ├── Local price trends
   ├── Comparable sales velocity
   └── Seasonal patterns

5. DEAL ECONOMICS (Weight: 5-10%)
   ├── Potential ARV (After Repair Value)
   ├── Estimated renovation cost
   ├── Expected profit margin
   ├── Holding costs
   └── Exit strategy viability
```

**Key insight for Russian product:** The scoring model for Russia would need to adapt:
- **Financial distress**: Tax debt (FNS), utility debts, FSSP proceedings, bankruptcy filings (EFRSB)
- **Owner motivation**: Emigration records, multiple ownership, inheritance cases
- **Property condition**: Limited photo data, rely on year built, renovation permits
- **Market context**: Cadastral value vs. listing price, time on Avito/CIAN
- **Deal economics**: ARV from comparable renovated units

---

## 6. Real-Time Auction Intelligence

### 6.1 Who Does It Best?

**Tier 1 — Real-time during auction:**
- **Auction.com Bid Interact**: Real-time REO auction monitoring, instant reserve changes, live bid acceptance
- **Allsop (UK)**: Real-time online bidding with transparent bid visibility
- **EIG SaleVision**: In-room displays with live bid tracking and internet broadcasting

**Tier 2 — Same-day results:**
- **CoreLogic (Australia)**: Sunday morning preliminary results, 99% capture rate
- **Domain (Australia)**: Weekly results by suburb

**Tier 3 — Delayed but comprehensive:**
- **SQM Research (Australia)**: Tuesday publication with most complete dataset
- **ATTOM (US)**: Monthly reports with complete pipeline data
- **EIG (UK)**: Post-auction results within weeks with premium/discount calculations

### 6.2 How Clearance Rates Predict Market Direction

Australia has proven this relationship most rigorously:

**Leading indicator properties:**
- Clearance rate changes precede price changes by 1-3 months
- A sustained drop below 60% almost always predicts price falls
- A sustained rise above 70% predicts price increases
- Volume matters: low-volume weekends produce volatile rates

**Adjustments needed:**
- Seasonal normalization (spring peak, winter trough)
- Preliminary vs. final correction (preliminary typically 3-5% higher)
- Withdrawn auction treatment (counted as "not sold" in honest calculations)
- "Sold after auction" handling (CoreLogic includes these; some don't)

### 6.3 Bidder Behavior Analytics

**What Auction.com's AuctionSync captures:**
- Individual bidder patterns across auctions
- Bid increment behavior (aggressive vs. conservative bidding)
- Win rate by bidder category
- Geographic bidding preferences
- Price sensitivity curves

**What this enables:**
- Predicting likely sale price based on registered bidder profiles
- Identifying underserved markets (few bidders = opportunity)
- Targeting specific bidders for specific property types
- Optimizing reserve prices based on expected bidder behavior

### 6.4 Post-Auction Analytics

**Best implementations:**

**Auction.com Portfolio Interact:**
- Sold vs. reserve price analysis
- Time-to-disposition tracking
- Bidder conversion rates
- Portfolio-level performance metrics

**EIG (UK):**
- Guide price vs. sold price tracking
- Premium/discount by property type and region
- Auction house performance comparison
- Historical success rates

**CoreLogic (Australia):**
- Clearance rate trends (weekly, monthly, quarterly)
- Median auction price by suburb
- Days on market for auction vs. private treaty
- Passed-in rate tracking

---

## 7. Best UX Patterns for Auction Analytics

### 7.1 Map-Based Search

**Best implementations:**

**PropertyRadar:**
- Polygon, Rectangle, and Radius drawing tools
- Heatmap overlays (value, ownership duration, owner age, turnover)
- Color-coded markers by distress level
- Seamless zoom from city level to parcel level

**ATTOM Property Navigator:**
- Custom-drawn search areas
- Neighborhood, school district, and boundary layers
- Parcel boundary visualization
- Flood zone overlays

**Auction.com:**
- List, Split, and Map layout options
- Filter by state, county, property type
- Real-time inventory updates
- Mobile-responsive map interface

**PropStream (2025 Map Interface):**
- AI-powered data visualization
- Property condition overlays
- Foreclosure Factor heatmaps
- Draw-to-search tools

### 7.2 Discount to Market Display

**Best patterns observed:**

```
PROPERTY CARD LAYOUT (best practice)
====================================
[Property Photo]    [Map Pin on minimap]

123 Main Street, Anytown
3 bed | 2 bath | 1,450 sqft | Built 1985

ESTIMATED VALUE:     $320,000
AUCTION PRICE:       $224,000   ← bold, large font
DISCOUNT:            -30%       ← color-coded (green = deep discount)

[Progress bar: 0% ----[====]---- 100% of market value]

Foreclosure Stage:   Notice of Sale ← status badge
Days in Pipeline:    127
Opening Bid:         $180,000
Bidder Count:        7           ← if available

[SAVE] [ALERT] [SHARE] [BID NOW]
```

**Key elements:**
- Discount percentage prominently displayed (color-coded: green >25%, yellow 10-25%, red <10%)
- Visual progress bar showing price relative to market value
- Pipeline stage indicator
- Bidder count or interest level (social proof)

### 7.3 Price History Display

**Best patterns:**

```
PRICE HISTORY TIMELINE
======================
2019-03    Purchased for $280,000       ●
2020-11    Assessed at $310,000         ○
2022-06    Refinanced $250,000          ○
2023-09    Notice of Default filed      ●  ← RED marker
2024-01    Notice of Trustee Sale       ●  ← RED marker
2024-03    Auction: Opening bid $195,000 ●  ← CURRENT
           Est. Market Value: $335,000   --- (dotted line)
```

- Timeline format (vertical or horizontal)
- Color-coded events (purchases = blue, distress = red, valuations = gray)
- Current market value as a reference line
- Loan balance vs. value gap visualization

### 7.4 Lot Scoring Display

**Best patterns from PropStream and BatchLeads:**

```
DEAL SCORE: 87/100    ★★★★☆
=============================
Financial Distress:   ████████░░  HIGH
Owner Motivation:     ██████░░░░  MEDIUM
Property Condition:   ██████████  EXCELLENT
Market Discount:      █████████░  STRONG
Deal Economics:       ███████░░░  GOOD

TOP SIGNALS:
• Tax delinquent 2 years ($12,400)
• Absentee owner (out-of-state)
• Listed 180+ days
• 28% below estimated value
```

- Single composite score (0-100) for quick scanning
- Component breakdown bars
- Top contributing signals listed
- Color gradient from red (risky) to green (opportunity)

### 7.5 Alert/Notification Systems

**Best implementations:**

**PropertyRadar Signals:**
- Event-driven triggers (new filing, price change, status change)
- Multi-channel: email, SMS, push notification, direct mail
- Frequency control: instant, daily digest, weekly summary
- Custom criteria (fires only for properties matching saved search)

**CoreLogic (Australia):**
- Weekly clearance rate alerts
- Suburb-level activity notifications
- Price threshold alerts

**Auction.com Foreclosure Interact:**
- Mobile push notifications for auction status changes
- Venue-level tracking
- Cleared/canceled property alerts

**Best practice notification hierarchy:**

```
NOTIFICATION PRIORITY LEVELS
=============================
HIGH (Push + SMS + Email):
  • New auction matching saved search
  • Price drop below threshold
  • Auction within 24 hours
  • Bid outranked

MEDIUM (Push + Email):
  • New listing in tracked area
  • Status change (NOD → NTS)
  • Weekly market summary

LOW (Email only / in-app):
  • Market trend updates
  • Similar properties sold
  • Educational content
```

### 7.6 Dashboard Patterns

**Portfolio Interact (Auction.com) for Sellers:**
```
┌─────────────────────────────────────────────────────┐
│  PORTFOLIO OVERVIEW                                  │
│  Total Assets: 1,247  |  Active Auctions: 89        │
│  Avg. Days to Sale: 47  |  Avg. Discount: -22%      │
├──────────────┬──────────────┬───────────────────────┤
│ PRICING      │ PERFORMANCE  │ BIDDER ACTIVITY        │
│ OPTIMIZATION │ TRENDS       │                        │
│              │              │ ■■■■■■■░░░  78%        │
│ 23 assets    │  ↗ +5% vs    │ bid coverage           │
│ over market  │  last month  │                        │
│              │              │ 12 assets with         │
│ 7 assets     │  ↘ -3% avg   │ bids within range      │
│ within range │  discount    │ of reserve             │
├──────────────┴──────────────┴───────────────────────┤
│  [MAP VIEW]  [LIST VIEW]  [ANALYTICS]  [EXPORT]     │
└─────────────────────────────────────────────────────┘
```

**Investor Dashboard (PropertyRadar-style):**
```
┌─────────────────────────────────────────────────────┐
│  MY WATCHLIST                    [+ New Search]      │
│                                                      │
│  Saved Searches: 5  |  New Matches Today: 23        │
│  Active Signals: 12  |  Properties Tracked: 340     │
├─────────────────────────────────────────────────────┤
│  HEAT MAP: [Distress Level ▼]  [Region ▼]           │
│  ┌─────────────────────────────────────────┐        │
│  │         [Interactive Map with           │        │
│  │          color-coded heatmap]           │        │
│  │                                         │        │
│  └─────────────────────────────────────────┘        │
├─────────────────────────────────────────────────────┤
│  TOP DEALS TODAY          Sort: [Deal Score ▼]       │
│  1. 123 Main St ........... Score: 94  Disc: -35%   │
│  2. 456 Oak Ave ........... Score: 91  Disc: -28%   │
│  3. 789 Pine Rd ........... Score: 87  Disc: -31%   │
└─────────────────────────────────────────────────────┘
```

---

## 8. Key Takeaways for a Russian Product

### 8.1 What Russia Has That Others Don't

| Data Source | Russian Equivalent | Accessibility |
|-------------|-------------------|---------------|
| Foreclosure filings | FSSP proceedings (fssp.gov.ru) | Public, parseable |
| Court auction listings | torgi.gov.ru, bankrot.fedresurs.ru | Public, parseable |
| Property records | Rosreestr (EGRN extracts) | Paid API available |
| Tax delinquency | FNS data | Limited public access |
| Property listings | Avito, CIAN, Domclick | Parseable |
| Cadastral value | Rosreestr cadastral map | Public, free |
| Bankruptcy proceedings | EFRSB (bankrot.fedresurs.ru) | Public, parseable |

### 8.2 Product Architecture Inspired by Best Practices

```
RUSSIAN DISTRESSED PROPERTY ANALYTICS — ARCHITECTURE
=====================================================

DATA LAYER (Like ATTOM)
├── torgi.gov.ru parser → auction lots + results
├── bankrot.fedresurs.ru parser → bankruptcy proceedings
├── fssp.gov.ru parser → enforcement proceedings
├── Rosreestr API → property data + cadastral value
├── Avito/CIAN parser → market listings + prices
└── Unified Property ID → links across all sources

ANALYTICS LAYER (Like PropertyRadar + PropStream)
├── Discount Calculator: auction price vs. cadastral vs. market
├── Deal Score (0-100): financial distress + location + condition + economics
├── "Likelihood to sell below market" model
├── Clearance Rate: % of lots sold at first auction
├── Regional heatmaps: distress concentration
└── Price prediction: expected auction outcome

REAL-TIME LAYER (Like Auction.com + CoreLogic)
├── New lot alerts (by region, type, price, discount)
├── Auction result tracking (sold/unsold/withdrawn)
├── Price change notifications
├── Pipeline tracking: filing → scheduled → auction → result
└── Weekly/monthly clearance rate reports

UX LAYER (Best of PropertyRadar + Auction.com)
├── Map-based search with polygon/radius tools
├── Heatmaps (distress level, discount depth, turnover)
├── Property cards with discount %, deal score, timeline
├── Alert system (Telegram, email, push)
├── Saved searches + watchlists
└── Portfolio dashboard for repeat investors
```

### 8.3 Unique Opportunities for Russia

1. **No competition**: There is no PropertyRadar or ATTOM equivalent in Russia. torgi.gov.ru is a bare-bones listing portal.

2. **Court auction transparency gap**: Russian bankruptcy auctions are opaque. Tracking clearance rates, discount-to-cadastral ratios, and regional patterns would be genuinely new intelligence.

3. **Cross-referencing opportunity**: Linking FSSP + EFRSB + Rosreestr + Avito data creates a 360-degree distressed property profile that doesn't exist today.

4. **Telegram-native distribution**: Unlike US/UK where email dominates, Russian users expect Telegram alerts. Build Telegram-first.

5. **Cadastral value as benchmark**: Russia's cadastral value system provides a government-set benchmark similar to Germany's Verkehrswert. Discount to cadastral value is a natural metric.

6. **Step-down auction model**: Russian bankruptcy auctions typically follow first auction → repeat auction (at lower price) → public offer (further reduced). Tracking which stage each lot is at and the expected discount at each stage is unique analytics.

### 8.4 Minimum Viable Product

Based on the global best practices, a Russian MVP should include:

1. **Data aggregation** from torgi.gov.ru + bankrot.fedresurs.ru (like ZVG-Portal scraper for Germany)
2. **Discount calculation** vs. cadastral value (like UK guide price vs. sold price tracking)
3. **Deal scoring** (simplified version: discount depth + location + property type) (like PropStream Foreclosure Factor)
4. **Map-based search** with region/city/type filters (like PropertyRadar)
5. **Telegram alerts** for new lots matching saved criteria (like PropertyRadar Signals)
6. **Weekly clearance rate** by region (like CoreLogic Australia)
7. **Auction result tracking** — sold/unsold/price achieved (like EIG UK)

---

## Sources

### US Platforms
- [Auction.com Platform Transformation](https://www.housingwire.com/articles/47314-transforming-the-auctioncom-platform/)
- [Auction.com Bid Interact](https://www.housingwire.com/articles/50022-auctioncom-adds-bid-interact-to-its-portfolio-interact-dashboard/)
- [ATTOM Data — Foreclosure Data](https://www.attomdata.com/data/foreclosure-data/)
- [ATTOM API Documentation](https://api.developer.attomdata.com/docs)
- [PropertyRadar Features](https://www.propertyradar.com/features-overview)
- [PropertyRadar Criteria Glossary](https://help.propertyradar.com/en/articles/2507682-criteria-glossary-2007-2025)
- [Sundae Marketplace](https://sundae.com/)
- [Xome Platform](https://www.xome.com/)
- [PropStream Predictive AI](https://www.propstream.com/predictive-ai)
- [BatchLeads AI Scoring](https://batchleads.io/blog/ai-in-real-estate-find-motivated-seller-leads-faster-with-batchleads)
- [Goliath Data vs. PropStream vs. BatchLeads](https://goliathdata.com/goliath-data-vs-propstream-vs-batchleads-in-2025-for-real-estate-investors)
- [HouseCanary Propensity Model](https://www.housecanary.com/blog/case-study-propensity-model)
- [Datazapp Seller Scores](https://www.datazapp.com/introducing-seller-scores-motivated-market-segments/)
- [CWCOT Program Analysis — Urban Institute](https://www.urban.org/urban-wire/how-cwcot-program-could-deliver-even-more-benefits-fha-borrowers-and-homeowners-facing)

### UK Platforms
- [EIG Property Auctions](https://www.eigpropertyauctions.co.uk/)
- [EIG Auctioneer Services](https://www.eigpropertyauctions.co.uk/auctioneer-services)
- [Allsop Commercial Auctions](https://www.allsop.co.uk/auctions/commercial-auctions/)
- [Allsop — Online Auctions Reshaped Market](https://www.allsop.co.uk/insights/five-years-on-how-online-auctions-reshaped-the-commercial-real-estate-auction-market/)
- [iamsold Auction Platform](https://www.iamsold.co.uk/)
- [UK Guide Price Accuracy — SDL Auctions](https://www.sdlauctions.co.uk/latest-news/how-accurate-are-guide-prices-at-property-auctions/)
- [ASA Guide Price Rules](https://www.asa.org.uk/advice-online/auction-guide-prices-and-non-optional-charges.html)

### Germany Platforms
- [ZVG-Portal (Official)](https://www.zvg-portal.de/)
- [Zwangsversteigerung.de](https://www.zwangsversteigerung.de/)
- [Argetra](https://www.argetra.de/)
- [ZVG-Portal Scraper (Apify)](https://apify.com/signalflow/zvg-portal-scraper)
- [German ZVG Law (English)](https://www.gesetze-im-internet.de/englisch_zvg/englisch_zvg.html)
- [Justiz-Auktion.de](https://auctiondirectory.eu/listings/justiz-auktion-de-germanys-premier-judicial-auction-platform/)

### Australia Platforms
- [CoreLogic/Cotality Auction Results](https://www.cotality.com/au/our-data/auction-results)
- [CoreLogic Clearance Rate Trends](https://www.corelogic.com.au/news-research/news/2025/clearance-rates-on-the-upwards-trend)
- [SQM Research Auction Results](https://sqmresearch.com.au/auction_results.php)
- [SQM Methodology Deep Dive](https://www.curtisassociates.com.au/a-deep-dive-into-sydneys-auction-clearance-rates-how-they-are-reported-has-got-to-change/)
- [Cotality Developer Portal](https://developer.corelogic.asia/)
- [Reserve Price Setting — OpenAgent](https://www.openagent.com.au/blog/how-to-set-a-reserve-price)

### Scoring & Analytics
- [S&P CREST Scorecard](https://www.spglobal.com/marketintelligence/en/campaigns/commercial-real-estate-scorecard)
- [LightBox — Weighted Risk Scoring](https://www.lightboxre.com/insight/weighted-risk-scoring-models/)
- [Chimnie — Sale Propensity](https://www.chimnie.com/articles/sale-propensity)
- [BatchData — Likelihood to Sell](https://batchdata.io/blog/likelyhood-to-sell-data-in-real-estate-machine-learning-and-ai)
- [PropStream Intelligence](https://www.propstream.com/news/the-future-of-propstream-part-1-propstream-intelligence-is-here)

### UX & Platform Design
- [Auction Platform Development Guide](https://themindstudios.com/blog/real-estate-auction-platform-development/)
- [AuctionMethod Reporting & Analytics](https://www.auctionmethod.com/auction-reporting-analytics)
- [ATTOM Property Navigator](https://www.attomdata.com/solutions/property-navigator/)
- [Notification UX Guidelines — Smashing Magazine](https://www.smashingmagazine.com/2025/07/design-guidelines-better-notifications-ux/)

---

*Report compiled 2026-03-01. Data reflects publicly available information as of research date.*
