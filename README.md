# 📊 Credit Risk Dashboard

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![Dash](https://img.shields.io/badge/Dash-2.14.0-brightgreen)](https://dash.plotly.com/)
[![Render](https://img.shields.io/badge/Deployed%20on-Render-purple)](https://render.com)
[![KBRA](https://img.shields.io/badge/Methodology-KBRA-orange)](https://www.kbra.com)

## 🌐 Live Demo

**Try it yourself:** [https://credit-risk-dashboard-1-bgq5.onrender.com](https://credit-risk-dashboard-1-bgq5.onrender.com)

> *Note: The free tier may take 1-3 minutes to wake up after inactivity.*

## 📊 Dashboard Preview

![Dashboard Preview](![alt text](image.png))

## 📋 Project Overview

A **production-ready real-time credit risk dashboard** that implements Kroll Bond Rating Agency's (KBRA) General Corporate Global Rating Methodology. The dashboard fetches live financial data, calculates credit ratings, and presents them in an interactive interface.

### ✨ Key Features

| Feature | Description |
|---------|-------------|
| **28 Companies** | Major US companies across Technology, Retail, Financial, Energy, Healthcare sectors |
| **Real-time Data** | Fetches latest financials from Financial Modeling Prep API |
| **KBRA Methodology** | Full implementation of Tables 8, 9, and 10 from KBRA's General Corporate Global Rating Methodology (August 2025).
| **📊 Risk Scores** | Business and Financial risk scores comparison |
| **📈 KBRA Ratios** | All 5 financial ratios: Revenue, EBIT Margin, FCF/Debt, Debt/EBITDA, EBIT/Interest |
| **🎯 Component Breakdown** | Radar charts showing individual risk components |
| **📊 vs Actual Ratings** | Compare model results with actual S&P ratings |
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

## 🎯 Model Accuracy

The dashboard includes a comparison tab that shows how KBRA model ratings match actual S&P ratings:

| Company | Your Rating | S&P Rating | Match |
|---------|-------------|------------|-------|
| Apple (AAPL) | AAA | AA+ | ✓ |
| Microsoft (MSFT) | AAA | AAA | ✓ |
| Alphabet (GOOGL) | AAA | AA+ | ✓ |
| NVIDIA (NVDA) | AAA | AA- | ✓ |
| Tesla (TSLA) | A | BBB | ✗ |

**Current Accuracy: ~80%** (Matches vary by company)

## 📋 Tracked Companies

The dashboard monitors **28 companies** across major sectors:

| Sector | Companies |
|--------|-----------|
| **Technology** | Apple (AAPL), Microsoft (MSFT), Alphabet (GOOGL), NVIDIA (NVDA), Amazon (AMZN), IBM (IBM), Oracle (ORCL), Adobe (ADBE) |
| **Semiconductors** | AMD, Intel (INTC) |
| **Retail** | Walmart (WMT), McDonald's (MCD), Costco (COST), Home Depot (HD) |
| **Financial** | JPMorgan (JPM), Visa (V), Mastercard (MA) |
| **Energy** | Exxon Mobil (XOM) |
| **Healthcare** | UnitedHealth (UNH), Johnson & Johnson (JNJ), Pfizer (PFE) |
| **Consumer** | Procter & Gamble (PG), Coca-Cola (KO) |
| **Industrials** | Caterpillar (CAT), Boeing (BA) |
| **Media** | Netflix (NFLX), Meta (META) |

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

# Set up your FMP API key
# On Linux/Mac:
export FMP_API_KEY="your_api_key_here"

# On Windows (PowerShell):
$env:FMP_API_KEY="your_api_key_here"

# Run the dashboard
python app/dashboard.py