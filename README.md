# 📊 End-to-End Credit Risk Modelling & Reporting Suite

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![Dash](https://img.shields.io/badge/Dash-2.14.0-brightgreen)](https://dash.plotly.com/)
[![Render](https://img.shields.io/badge/Deployed%20on-Render-purple)](https://render.com)
[![KBRA](https://img.shields.io/badge/Methodology-KBRA-orange)](https://www.kbra.com)
[![IFRS 9](https://img.shields.io/badge/Compliance-IFRS%209-blue)](https://www.ifrs.org)
[![pyratings](https://img.shields.io/badge/pyratings-HSBC-red)](https://hsbc.github.io/pyratings/)

## 🌐 Live Demo

**Try it yourself:** [[https://credit-risk-dashboard-1-bgq5.onrender.com](https://credit-risk-dashboard-tix8.onrender.com)]

> *Note: The free tier may take 1-3 minutes to wake up after inactivity.*

## 📊 Dashboard Preview

![Dashboard Preview](![alt text](image-1.png))

## 📋 Project Overview

A **production-ready end-to-end credit risk modelling and reporting suite** that implements Kroll Bond Rating Agency's (KBRA) General Corporate Global Rating Methodology, enhanced with IFRS 9 Expected Credit Loss calculations, professional rating analytics using HSBC's pyratings library, and interactive stress testing scenarios.

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| **25+ Companies** | Major US companies across Technology, Retail, Financial, Energy, Healthcare, Media sectors |
| **Real-time Data** | Fetches latest financials from Financial Modeling Prep API |
| **KBRA Methodology** | Full implementation of Tables 8, 9, and 10 from KBRA's General Corporate Global Rating Methodology (August 2025) |
| **📊 Risk Scores** | Business and Financial risk scores comparison with data period tracking |
| **📈 Financial Ratios** | All 5 key ratios: Revenue ($B), EBIT Margin %, FCF/Debt, Debt/EBITDA, EBIT/Interest, ROA % |
| **🎯 Component Breakdown** | Radar charts showing individual financial risk components |
| **📊 vs Actual Ratings** | Compare model results with actual S&P ratings (with period alignment and confidence indicators) |
| **📊 Model Validation** | Statistical validation metrics including Accuracy, Cohen's Kappa, and notch analysis using pyratings |
| **💰 IFRS 9 & ECL** | Expected Credit Loss calculations with staging (Stage 1/2/3) and WARF (Weighted Average Rating Factor) |
| **🔮 Scenario Analysis** | Stress testing with GDP and interest rate shocks |
| **⭐ Watchlist** | Save favorite companies (persists in browser) |
| **📋 Raw Data** | Detailed table with all metrics |
| **📥 Export Data** | Download analysis as CSV |

## 📈 Methodology

### Business Risk Assessment (40% weight)

| Component | Weight |
|-----------|--------|
| Industry Risk | 40% |
| Competitive Risk | 35% |
| Liquidity Risk | 25% |

### Financial Risk Assessment (60% weight)

| Component | Weight |
|-----------|--------|
| Size (Revenue) | 10% |
| Profitability (EBIT Margin) | 20% |
| Cash Flow (FCF/Debt) | 25% |
| Leverage (Debt/EBITDA) | 25% |
| Coverage (EBIT/Interest) | 20% |

## 🎯 Model Validation

The dashboard includes comprehensive validation metrics comparing KBRA model ratings with actual S&P ratings:

| Metric | Description | Current Performance |
|--------|-------------|---------------------|
| **Exact Match** | Perfect rating alignment | ~12-20% |
| **Within 1 Notch** | Ratings within 1 level (industry standard) | ~84% |
| **Within 2 Notches** | Ratings within 2 levels | ~88% |
| **Cohen's Kappa** | Agreement beyond chance (>0.7 = strong) | ~0.23-0.30 |

> **Note:** KBRA uses a simplified scale (no +/- modifiers) while S&P uses a full scale with modifiers. Ratings within 1-2 notches are considered aligned per industry standards.

## 💰 IFRS 9 Expected Credit Loss (ECL)

The dashboard implements IFRS 9 compliant ECL calculations:

| Component | Description |
|-----------|-------------|
| **PD** | Probability of Default mapped from KBRA ratings using S&P historical default rates |
| **LGD** | Loss Given Default (35% for senior secured, 55% for unsecured) |
| **EAD** | Exposure at Default (estimated as 30% of annual revenue) |
| **Staging** | Stage 1 (12-month ECL), Stage 2/3 (Lifetime ECL based on SICR) |
| **WARF** | Weighted Average Rating Factor - industry standard portfolio quality metric |

## 🔮 Scenario Analysis

Interactive stress testing with:

| Shock | Impact on PD |
|-------|--------------|
| **GDP Decline (-2%)** | PD increases by ~50% |
| **GDP Growth (+2%)** | PD decreases by ~20% |
| **Interest Rate Increase** | Higher borrowing costs increase default risk |

## 📋 Tracked Companies

The dashboard monitors **25+ companies** across major sectors:

| Sector | Companies |
|--------|-----------|
| **Technology** | Apple (AAPL), Microsoft (MSFT), Alphabet (GOOGL), NVIDIA (NVDA), Amazon (AMZN), IBM (IBM), Adobe (ADBE) |
| **Semiconductors** | AMD, Intel (INTC) |
| **Retail** | Walmart (WMT), Starbucks (SBUX), Costco (COST), Lowe's (LOW) |
| **Financial** | JPMorgan (JPM), Visa (V) |
| **Energy** | Exxon Mobil (XOM) |
| **Healthcare** | UnitedHealth (UNH), Johnson & Johnson (JNJ), Pfizer (PFE) |
| **Consumer** | PepsiCo (PEP), Coca-Cola (KO) |
| **Industrials** | Boeing (BA) |
| **Media** | Netflix (NFLX), Meta (META) |

## 🛠️ Technology Stack

| Technology | Purpose |
|------------|---------|
| **Python 3.12** | Core programming language |
| **Dash / Plotly** | Interactive dashboard framework |
| **Dash Bootstrap Components** | Professional UI components |
| **Financial Modeling Prep API** | Real-time financial data |
| **pyratings (HSBC)** | Professional rating analytics and notch calculations |
| **Render** | Cloud deployment (free tier) |
| **Pandas / NumPy** | Data manipulation and calculations |

## 📊 Data Sources

| Data Type | Source |
|-----------|--------|
| **Financial Statements** | FMP API (real-time) |
| **KBRA Ratings** | Calculated from financial data |
| **S&P Ratings** | Manually curated (as of December 2025) |
| **Rating Analytics** | pyratings (HSBC open-source library) |

## 🚀 Quick Start

### Prerequisites
- Python 3.12 or higher
- A [Financial Modeling Prep API key](https://financialmodelingprep.com/) (free tier available)

### Installation & Setup

```bash
# Clone the repository
git clone https://github.com/ayeayemyat-miso/credit-risk-dashboard.git
cd credit-risk-dashboard

# Install dependencies
pip install -r requirements.txt

# Install pyratings (HSBC rating analytics library)
pip install pyratings

# Set up your FMP API key
# On Linux/Mac:
export FMP_API_KEY="your_api_key_here"

# On Windows (PowerShell):
$env:FMP_API_KEY="your_api_key_here"

# Run the dashboard
python app/dashboard.py
