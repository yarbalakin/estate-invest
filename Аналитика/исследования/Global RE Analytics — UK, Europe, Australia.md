# Global Real Estate Analytics & Valuation: Deep Technical Research

## Table of Contents

1. [UK -- The Most Transparent RE Market](#1-uk)
2. [UK Data Infrastructure (The Gold Standard)](#2-uk-data-infrastructure)
3. [Germany](#3-germany)
4. [France](#4-france)
5. [Australia](#5-australia)
6. [Scandinavia](#6-scandinavia)
7. [Key Takeaways for Russia](#7-key-takeaways-for-russia)

---

## 1. UK -- The Most Transparent RE Market

### 1.1 HM Land Registry Price Paid Data

The cornerstone of UK property transparency. **Every residential property transaction** in England & Wales at actual sale price (not asking price) is published as open data.

**Data Fields (16 columns):**

| # | Field | Description |
|---|-------|-------------|
| 1 | Transaction Unique ID | Auto-generated reference for each sale |
| 2 | Price | Actual sale price from transfer deed |
| 3 | Date of Transfer | Completion date from transfer deed |
| 4 | Postcode | Property postcode |
| 5 | Property Type | D=Detached, S=Semi, T=Terraced, F=Flat, O=Other |
| 6 | Old/New | Y=Newly built, N=Established |
| 7 | Duration | F=Freehold, L=Leasehold |
| 8 | PAON | Primary addressable object (house number/name) |
| 9 | SAON | Secondary addressable object (flat number) |
| 10 | Street | Street name |
| 11 | Locality | Locality |
| 12 | Town/City | Town or city |
| 13 | District | District |
| 14 | County | County |
| 15 | PPD Category | A=Standard price, B=Additional (e.g. right-to-buy) |
| 16 | Record Status | A=Addition, C=Change, D=Delete (monthly files only) |

**Access Methods:**
- **Bulk download**: Single CSV (4.3 GB, all transactions from 1995), yearly files, or monthly delta files -- [gov.uk/government/statistical-data-sets/price-paid-data-downloads](https://www.gov.uk/government/statistical-data-sets/price-paid-data-downloads)
- **SPARQL endpoint**: `http://landregistry.data.gov.uk/landregistry/query` -- 400M+ triples, full linked data -- [landregistry.data.gov.uk](https://landregistry.data.gov.uk/)
- **Report builder**: Geographic query tool at [landregistry.data.gov.uk/app/ppd](https://landregistry.data.gov.uk/app/ppd)
- **R package**: `uklr` on CRAN for programmatic access
- **License**: Open Government Licence -- completely free

**Key insight**: 20M+ transactions since 1995, updated monthly. This is **actual sale prices** from legal deed transfers, not self-reported or asking prices.

### 1.2 Zoopla Estimate (Consumer AVM)

**How it works**: Powered by Hometrack (Zoopla subsidiary, acquired for GBP 120M). Uses a statistical model combining machine learning and comparable sales analysis.

**Data sources**:
- HM Land Registry Price Paid data
- Registers of Scotland
- Royal Mail postal data
- Ordnance Survey mapping
- Mortgage valuation data (via Hometrack's lender relationships)
- Property listings from Zoopla's own portal

**Methodology**:
- Analyses "comps" -- comparable properties sold in the same area
- Variables: bedrooms, bathrooms, sq footage, location, neighborhood desirability, amenities proximity, market volatility
- Updated monthly
- Produces a **confidence score** (High/Medium/Low) based on data freshness and number of local comparables

**Accuracy**: Varies significantly. In areas with many comparable sales (London terraced houses), quite good. For rural or unusual properties, can be off by 15-20%.

### 1.3 Hometrack Professional AVM

The **institutional-grade** AVM that powers UK mortgage lending. Separate from the consumer Zoopla Estimate.

**Market position**:
- **18 of top 20 UK mortgage lenders** use Hometrack AVM
- First AVM accredited by Moody's, S&P, and Fitch
- 50M+ valuations per year
- ~1,600 mortgage origination AVMs daily
- 24M portfolio AVMs annually

**Methodology (multi-layer)**:
1. **Comparable sales model**: Finds nearby properties with similar characteristics
2. **Adjustment model**: Machine learning layer using past valuations and proprietary property database
3. **Condition model**: NLP-based, analyzes property listing text to detect condition indicators
4. **Energy performance integration**: EPC data for property attributes
5. **Confidence scoring**: Each valuation gets a confidence level

**Accuracy**: 80% of valuations within 10% of surveyor's recommended value.

**Economic impact**: Estimated GBP 70M annual savings by replacing physical surveys.

### 1.4 Rightmove Online Agent Valuation (Launched October 2025)

**Not an AVM** -- this is a lead-generation product connecting homeowners with local agents.

**How it works**:
1. Homeowner submits property details + images on Rightmove
2. Local agents receive the lead
3. Agents provide an estimated valuation range with personalized message
4. AI-assisted writing tool helps agents craft responses

**Performance**: 83% click-through rate, fastest-growing product launch in Rightmove history, valuation leads up 50% YoY.

### 1.5 PropertyData.co.uk

Professional analytics platform that **aggregates 24+ official UK data sources** into a unified interface and API.

**Data sources aggregated**: Land Registry, Rightmove, Zoopla, OnTheMarket, EPC, ONS Census, Ordnance Survey, VOA, Royal Mail.

**Key analytics tools**:
- **Local Data Tool**: Area-level dashboard (pricing, GBP/sqft, rents, yields, demographics)
- **Comparables Analysis**: Sold/rental comps for any property
- **AVM**: GBP/sqft-based valuations with PDF reports
- **Sourcing Lists**: Algorithm-curated investment properties updated daily
- **Browser Extension**: Live data overlay on Rightmove/Zoopla/OnTheMarket listings
- **API**: 62+ endpoints, GET-only, JSON responses

**Pricing**: GBP 14-60/month, API from GBP 28/month.

### 1.6 MousePrice

**Database**: 90M property images, 20M sold price records, 18M historic estate agency listings, 2M surveyor records, 2M EPCs, 3M floor plans.

**Features**: 40 filters + 300 individual attributes for off-market identification, customizable heatmaps, assisted valuation (choose your own comps, generate branded PDF reports).

### 1.7 Essential Information Group (EIG) -- Auction Analytics

**The only comprehensive UK auction database.**

**Coverage**: 600,000+ lots sold in database, 850,000+ properties tracked, 38,000+ new lots annually (GBP 4.7B+ value), works with 400+ auction houses.

**Services**: Searchable database (current + all past lots), live auction broadcasting + online bidding, catalogue creation for auctioneers, legal pack hosting, portfolio analysis for investment banks.

### 1.8 UK Auction Houses -- Result Tracking

- **Allsop**: UK's #1 property auctioneer. All past results published.
- **SDL Auctions**: Digital-first approach, national coverage. Past results with final sold prices.
- **Savills Auctions**: Premium market, quarterly auctions.

All three publish: guide price, sold price, lot description, property type, location.

---

## 2. UK Data Infrastructure (The Gold Standard)

### 2.1 The Data Ecosystem -- How It All Connects

```
UPRN (Unique Property Reference Number)
         |
         v
   [Property Identity Layer]
         |
    +-----------+-----------+-----------+-----------+
    |           |           |           |           |
Land Registry  EPC       Council Tax  Ordnance    Royal Mail
(sold prices)  (energy+   (value      Survey      (postcodes)
               attributes) bands)     (mapping)
```

**UPRN** is the universal key. Every addressable location in Great Britain has one (~40M UPRNs). This allows cross-referencing between all datasets.

### 2.2 Land Registry -- Open Transaction Data

- **What**: Every residential sale at actual price, since 1995
- **Volume**: 20M+ transactions
- **Format**: CSV, Linked Data (SPARQL), report builder
- **Update**: Monthly
- **Cost**: Free (Open Government Licence)

### 2.3 EPC (Energy Performance Certificates) -- Property Attributes

- **Volume**: ~30M certificates for England & Wales
- **Key data**: Property type, floor area (sqm), rooms, construction age, wall type, roof type, windows, heating type, energy rating (A-G), CO2 emissions
- **API**: REST API with search by address, postcode, local authority
  - Endpoint: `https://epc.opendatacommunities.org/api/v1/domestic/`
  - Formats: JSON, CSV, bulk download
- **Cost**: Free

**Why this matters**: EPC provides the **physical attributes** that Land Registry lacks. Combining them via UPRN/address creates a rich property profile.

### 2.4 Council Tax Bands -- Value Indicator

- Every property banded A-H based on 1 April 1991 value
- Published by Valuation Office Agency (VOA)
- Free lookup at gov.uk

### 2.5 Ordnance Survey -- Mapping & UPRN

- **OS Open UPRN**: All 40M UPRNs with coordinates. Free download.
- **AddressBase**: 29M postal addresses + local authority data + OS property data.
- **OS MasterMap**: Detailed building footprints, boundaries, topology.

### 2.6 How These Datasets Are Combined for Valuation

1. **Identity resolution**: Match property to UPRN
2. **Transaction history**: Pull all historical sales from Land Registry PPD
3. **Physical attributes**: Pull from EPC
4. **Value band**: Pull Council Tax band as sanity check
5. **Geospatial context**: Ordnance Survey for distance to amenities
6. **Comparable selection**: Find similar properties that sold recently
7. **Price adjustment**: Hedonic regression or ML model
8. **Confidence scoring**: Based on comps, data freshness, uniqueness

---

## 3. Germany

### 3.1 ImmoScout24 -- Valuation Tool

Germany's largest property portal. Their "Immobilienbewertung":

**Methodology**: Hedonic valuation model + AVM comparing with thousands of similar properties. Uses both asking prices AND actual sale prices from Gutachterausschuss data.

**Accuracy**: ~9.9% average deviation from expert appraisals.

### 3.2 PriceHubble -- Pan-European AVM

Swiss proptech, active in **11 countries**. 200+ employees.

**API** (docs.pricehubble.com):
- **Valuation endpoint**: Up to 50 valuations per call
- **Property Tracker**: Ongoing monitoring with market trends
- **Dossier system**: Create property profiles
- Base URL: `https://api.pricehubble.com/api/v1/`

**Compliance**: Externally audited by Big 4 firm for EBA Guidelines.

### 3.3 Gutachterausschuss -- The UNIQUE German System

**Legally mandated** system for collecting actual transaction prices.

**How it works**:
1. Every purchase requires a **notarized contract**
2. By law (Section 195 BauGB), notaries MUST send a copy to the local Gutachterausschuss
3. Committee anonymizes and enters data into **Kaufpreissammlung**
4. Statistical methods applied to explain price differences

**Not fully open** like UK -- subject to data protection, but available for statistical/anonymized purposes.

### 3.4 BORIS -- Bodenrichtwertinformationssystem

**Standard land value information system**. Open data, free.

- **BORIS-D** (federal portal): bodenrichtwerte-boris.de -- free, no registration
- Standard land values per square meter for zones across all of Germany
- License: "Data License Germany -- Attribution -- Version 2.0" (open data)
- Only land values, NOT property values

---

## 4. France

### 4.1 DVF (Demandes de Valeurs Foncieres) -- Open Transaction Data

Since **May 2019**, France publishes ALL property transactions as open data.

**Coverage**: All metropolitan France, past 5 years. Update: semi-annual.

**Data formats** (DVF+ enhanced version):
- SQL files for PostgreSQL/PostGIS (17 tables)
- GeoPackage (.gpkg)
- CSV

**Key fields**: Transaction ID, date, value, full address, property type, built surface, rooms, land area, Carrez surface, cadastral identifiers.

**Access**:
- **Official portal**: data.gouv.fr
- **Interactive map**: app.dvf.etalab.gouv.fr
- **DVF+ (enhanced)**: datafoncier.cerema.fr
- **API**: github.com/datagouv/api-dvf
- **License**: Licence Ouverte v2.0

### 4.2 MeilleursAgents -- French AVM Platform

**Algorithm**: Gradient boosting tree regression (~1000 trees, 10+ years of R&D).

**Data sources**:
1. State DVF transactions (past 5 years)
2. BIEN database (Ile-de-France notaries)
3. 12,000+ partner agencies reporting in real-time

**Coverage**: 1,352 cities with detailed price maps, 1,036 price indices.

### 4.3 SeLoger

ML models combining listings + DVF sold data + socio-demographic data and POI. 1,000+ price indices across France.

---

## 5. Australia

### 5.1 CoreLogic Australia -- Dominant Data Provider

Near-monopoly on property data.

**RP Data Platform**: 10M+ property records, 98% coverage, 40+ years history, 1M+ new data points monthly.

**Key difference from UK**: Property data is NOT free open data. CoreLogic charges for access.

**API**: Available at corelogic.com.au/software-solutions/corelogic-apis.

### 5.2 REA Group (realestate.com.au) -- RealEstimate + AI

**RealEstimate**: Free instant property estimate powered by **PropTrack** (acquired 2018).

**realAssist (2025-2026)**: AI-powered conversational companion (OpenAI partnership). Users can ask questions about their valuation.

**Unique data**: REA sees demand-side signals (search patterns, saved properties) that no government dataset captures.

### 5.3 Domain.com.au

**Pricefinder platform**: 13M+ residences, 30+ years of sales data. AVM coverage 90-95% of homes.

### 5.4 Australian Auction Culture -- Real-Time Tracking

60%+ of properties in Melbourne sold at auction.

**REIV (Real Estate Institute of Victoria)** -- sets the standard:
- Data reported directly by agents after each auction
- Clearance rate published **3 times per week**: Saturday night (preliminary), Sunday night (updated), Wednesday (final, 95%+ coverage)
- Tracks: sold price, reserve met/not met, passed in, withdrawn, postponed

**Current metrics (Feb 2026)**: Sydney 71.6% clearance rate, median house price at auction AUD 2.09M.

---

## 6. Scandinavia

### 6.1 Hemnet (Sweden) -- ~90% Market Coverage

Dominant portal. 90% of all properties sold in Sweden listed on Hemnet.

**Sold prices ("Slutpriser")**: Final selling prices displayed on the platform. Creates market-wide transparency.

**Property register**: Lantmateriet -- Property Price Register API available.

### 6.2 Boliga (Denmark)

**Data source**: OIS (Public Information Server), receiving data from SKAT (tax authority).

Features: original asking price vs. sold price, price per sqm, sales history.

### 6.3 Norway -- Kartverket

**Matrikkelen (Cadastre)** + **Grunnboken (Land Registry)**. Public access, search by property ID only.

### 6.4 Common Patterns

All Nordic countries share:
1. Government-mandated transaction registration
2. Public access to transaction data
3. Digital-first (APIs and online databases)
4. High social trust (prices are public)
5. Dominant portals (Hemnet, Boliga, Finn.no)

---

## 7. Key Takeaways for Russia

### 7.1 What Makes the Best Markets Work

| Factor | UK | Germany | France | Australia | Scandinavia |
|--------|-----|---------|--------|-----------|-------------|
| Open transaction prices | Full (free) | Partial (committee) | Full (since 2019) | Paid (CoreLogic) | Full (public) |
| Universal property ID | UPRN (40M) | Flurstuck-Nr | Parcelle cadastrale | Property ID | Fastighets-ID |
| Physical attributes open data | EPC (30M) | Partial | DVF (limited) | No (paid) | Partial |
| AVM ecosystem maturity | Very high | Medium-high | Medium | High | Medium |
| Auction tracking | EIG + auction houses | Minimal | Minimal | Very high (REIV) | Moderate |

### 7.2 What Russia Can Replicate Without Government

1. **Listing-based comparable analysis** -- what ImmoScout24 does with asking prices
2. **Proprietary transaction database** -- like CoreLogic Australia (track every confirmed sale)
3. **AVM on listing data** -- MeilleursAgents-style gradient boosting
4. **Auction tracking** -- EIG model applied to torgi.gov.ru/ЕФРСБ
5. **UX patterns worth copying**:
   - PropertyData browser extension (overlay data on CIAN/Avito)
   - Hemnet sold price display
   - REIV three-stage publication (preliminary -> updated -> final)
   - PriceHubble confidence scoring
   - REA Group AI assistant (explain valuation changes)

### 7.3 What Requires Government Cooperation

1. **Open transaction data** (UK/France model) -- Rosreestr has this but doesn't publish
2. **Universal property ID** linking all datasets (like UPRN)
3. **EPC equivalent** -- building energy passports as open data with API

### 7.4 The Core Insight

The UK market works because of a **positive feedback loop**:

```
Open data (Land Registry)
  -> Enables AVMs (Hometrack, Zoopla)
    -> Creates transparency
      -> Builds trust
        -> More transactions
          -> More data
            -> Better AVMs
```

The French DVF example (launched 2019) shows that **a single policy decision** can unlock the entire chain within a few years. The Australian model shows that even without open data, a commercial entity (CoreLogic) can build the infrastructure over decades -- but it creates a monopoly.

---

*Research completed 2026-03-01*