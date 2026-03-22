# core/config.py
"""
Configuration file for Credit Risk Dashboard.
Contains all constants, thresholds, and mapping tables.
"""

import pandas as pd
import os

# ----------------------------------------------------------------------
# Company Data - Loaded from CSV
# ----------------------------------------------------------------------

def load_companies():
    """Load company data from CSV file"""
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'companies.csv')
    try:
        df = pd.read_csv(csv_path)
        return df.to_dict('records')
    except Exception as e:
        print(f"Error loading companies: {e}")
        # Fallback data (only if CSV fails)
        return [
            {'ticker': 'AAPL', 'name': 'Apple Inc.', 'sector': 'Technology', 'watch': 'Yes'},
            {'ticker': 'MSFT', 'name': 'Microsoft Corp.', 'sector': 'Technology', 'watch': 'Yes'},
            {'ticker': 'GOOGL', 'name': 'Alphabet Inc.', 'sector': 'Technology', 'watch': 'Yes'},
            {'ticker': 'NVDA', 'name': 'NVIDIA Corp.', 'sector': 'Semiconductors', 'watch': 'Yes'},
            {'ticker': 'TSLA', 'name': 'Tesla Inc.', 'sector': 'Auto', 'watch': 'Yes'},
            {'ticker': 'WMT', 'name': 'Walmart Inc.', 'sector': 'Retail', 'watch': 'Yes'},
            {'ticker': 'MCD', 'name': "McDonald's Corp.", 'sector': 'Retail', 'watch': 'Yes'},
            {'ticker': 'COST', 'name': 'Costco Wholesale Corp.', 'sector': 'Retail', 'watch': 'Yes'},
            {'ticker': 'HD', 'name': 'Home Depot Inc.', 'sector': 'Retail', 'watch': 'Yes'},
            {'ticker': 'UNH', 'name': 'UnitedHealth Group Inc.', 'sector': 'Healthcare', 'watch': 'Yes'},
            {'ticker': 'XOM', 'name': 'Exxon Mobil Corp.', 'sector': 'Energy', 'watch': 'Yes'},
            {'ticker': 'JPM', 'name': 'JPMorgan Chase & Co.', 'sector': 'Financial', 'watch': 'Yes'},
            {'ticker': 'V', 'name': 'Visa Inc.', 'sector': 'Financial', 'watch': 'Yes'},
            {'ticker': 'MA', 'name': 'Mastercard Inc.', 'sector': 'Financial', 'watch': 'Yes'},
            {'ticker': 'PG', 'name': 'Procter & Gamble Co.', 'sector': 'Consumer Staples', 'watch': 'Yes'},
            {'ticker': 'KO', 'name': 'Coca-Cola Co.', 'sector': 'Beverages', 'watch': 'Yes'},
            {'ticker': 'PFE', 'name': 'Pfizer Inc.', 'sector': 'Pharmaceuticals', 'watch': 'Yes'},
            {'ticker': 'JNJ', 'name': 'Johnson & Johnson', 'sector': 'Healthcare', 'watch': 'Yes'},
            {'ticker': 'CAT', 'name': 'Caterpillar Inc.', 'sector': 'Industrials', 'watch': 'Yes'},
            {'ticker': 'BA', 'name': 'Boeing Co.', 'sector': 'Aerospace', 'watch': 'Yes'},
            {'ticker': 'IBM', 'name': 'IBM Corp.', 'sector': 'Technology', 'watch': 'Yes'},
            {'ticker': 'ORCL', 'name': 'Oracle Corp.', 'sector': 'Technology', 'watch': 'Yes'},
            {'ticker': 'ADBE', 'name': 'Adobe Inc.', 'sector': 'Technology', 'watch': 'Yes'},
            {'ticker': 'AMD', 'name': 'AMD Inc.', 'sector': 'Semiconductors', 'watch': 'Yes'},
            {'ticker': 'INTC', 'name': 'Intel Corp.', 'sector': 'Semiconductors', 'watch': 'Yes'},
            {'ticker': 'AMZN', 'name': 'Amazon.com Inc.', 'sector': 'Retail', 'watch': 'Yes'},
            {'ticker': 'NFLX', 'name': 'Netflix Inc.', 'sector': 'Media', 'watch': 'Yes'},
            {'ticker': 'META', 'name': 'Meta Platforms Inc.', 'sector': 'Media', 'watch': 'Yes'},
        ]

# Load companies from CSV
COMPANIES = load_companies()

# Create mappings from CSV
COMPANY_NAMES = {c['ticker']: c['name'] for c in COMPANIES}
COMPANY_SECTORS = {c['ticker']: c['sector'] for c in COMPANIES}

# DEFAULT_TICKERS - all companies with watch=Yes
DEFAULT_TICKERS = [c['ticker'] for c in COMPANIES if c.get('watch') == 'Yes']

# Company to sector mapping (for compatibility)
COMPANY_SECTOR_MAP = {c['ticker']: c['sector'] for c in COMPANIES}

# ----------------------------------------------------------------------
# KBRA Rating Table (Table 10 from methodology)
# ----------------------------------------------------------------------
RATING_TABLE = {
    "Strong": {
        "AAA": (None, 1.5),
        "AA": (1.5, 4.5),
        "A": (3, 7.5),
        "BBB": (6, 10.5),
        "BB": (9.5, 13.5),
        "B": (13.5, None),
        "CCC or below": (None, None)
    },
    "Average": {
        "AAA": (None, 1.5),
        "AA": (None, 3),
        "A": (3, 9.5),
        "BBB": (7.5, 12),
        "BB": (9, 16.5),
        "B": (12, 18),
        "CCC or below": (16.5, None)
    },
    "Weak": {
        "AAA": (None, None),
        "AA": (None, None),
        "A": (None, 3),
        "BBB": (None, 7.5),
        "BB": (None, 9),
        "B": (None, 18),
        "CCC or below": (9, None)
    }
}

# ----------------------------------------------------------------------
# Financial metrics scoring thresholds (Table 8 from methodology)
# ----------------------------------------------------------------------
FINANCIAL_THRESHOLDS = {
    "size_revenue_bn": {
        1: 30, 3: 20, 6: 10, 9: 3, 12: 1, 15: 0.5, 18: 0
    },
    "ebit_margin": {
        1: 0.60, 3: 0.30, 6: 0.20, 9: 0.15, 12: 0.125, 15: 0.05, 18: 0
    },
    "roa": {
        1: 0.10, 3: 0.07, 6: 0.055, 9: 0.04, 12: 0.03, 15: 0.025, 18: 0
    },
    "fcf_to_debt": {
        1: 0.45, 3: 0.25, 6: 0.15, 9: 0.075, 12: 0.00, 15: -0.05, 18: -1.0
    },
    "rcf_to_debt": {
        1: 0.60, 3: 0.40, 6: 0.25, 9: 0.20, 12: 0.15, 15: 0.07, 18: 0
    },
    "debt_to_ebitda": {
        1: 1.0, 3: 1.5, 6: 2.5, 9: 3.5, 12: 4.5, 15: 6.0, 18: 100
    },
    "debt_to_capital": {
        1: 0.20, 3: 0.30, 6: 0.40, 9: 0.50, 12: 0.60, 15: 0.70, 18: 1.0
    },
    "ebit_interest": {
        1: 16, 3: 10, 6: 6, 9: 4, 12: 3, 15: 2, 18: 0
    },
    "ebitda_interest": {
        1: 20, 3: 16, 6: 10, 9: 6, 12: 4, 15: 1, 18: 0
    }
}

# ----------------------------------------------------------------------
# Industry risk rankings
# ----------------------------------------------------------------------
INDUSTRY_RISK_RANKING = {
    "Technology Hardware": "Medium-High",
    "Technology Software": "Medium",
    "Semiconductors": "Medium-High",
    "Retail": "Medium",
    "Health Care Services": "Medium",
    "Auto Manufacturers": "High",
    "Media & Entertainment": "Medium-High",
    "Oil & Gas": "Very High",
    "Financial Services": "Medium",
    "Utilities": "Low",
    "Healthcare": "Medium",
    "Consumer Cyclical": "Medium",
    "Consumer Defensive": "Medium-Low",
    "Industrials": "Medium",
    "Energy": "Very High",
    "Basic Materials": "High",
    "Communication Services": "Medium-High",
    "Real Estate": "Medium",
    "Technology": "Medium-High",
    "Auto": "High",
    "Financial": "Medium",
    "Consumer Staples": "Medium-Low",
    "Beverages": "Medium",
    "Pharmaceuticals": "Medium",
    "Aerospace": "Medium-High",
    "Media": "Medium-High"
}

# ----------------------------------------------------------------------
# Risk weights
# ----------------------------------------------------------------------
BUSINESS_RISK_WEIGHTS = {
    "industry": 0.40,
    "competitive": 0.35,
    "liquidity": 0.25
}

FINANCIAL_RISK_WEIGHTS = {
    "size": 0.10,
    "profitability": 0.20,
    "cash_flow": 0.25,
    "leverage": 0.25,
    "coverage": 0.20
}

# ----------------------------------------------------------------------
# Sector to CPGP mapping
# ----------------------------------------------------------------------
SECTOR_CPGP_MAP = {
    'Financial Services': 'Services and product focus',
    'Technology Hardware': 'Capital or asset focus',
    'Auto Manufacturers': 'Capital or asset focus',
    'Technology Software': 'Services and product focus',
    'Media & Entertainment': 'Services and product focus',
    'Retail': 'Services and product focus',
    'Oil & Gas': 'Commodity focus/scale driven',
    'Semiconductors': 'Capital or asset focus',
    'Technology': 'Capital or asset focus',
    'Auto': 'Capital or asset focus',
    'Financial': 'Services and product focus',
    'Healthcare': 'Services and product focus',
    'Consumer Staples': 'Services and product focus',
    'Beverages': 'Services and product focus',
    'Pharmaceuticals': 'Services and product focus',
    'Industrials': 'Capital or asset focus',
    'Aerospace': 'Capital or asset focus',
    'Media': 'Services and product focus',
    'Energy': 'Commodity focus/scale driven',
}

# ----------------------------------------------------------------------
# Profitability thresholds
# ----------------------------------------------------------------------
PROFITABILITY_THRESHOLDS = {
    'Technology Hardware': {'ebitda_margin': {'below': 12, 'above': 18}},
    'Auto Manufacturers': {'ebitda_margin': {'below': 6, 'above': 10}},
    'Technology Software': {'ebitda_margin': {'below': 25, 'above': 30}},
    'Media & Entertainment': {'ebitda_margin': {'below': 15, 'above': 30}},
    'Retail': {'ebitda_margin': {'below': 5, 'above': 10}},
    'Oil & Gas': {'ebitda_margin': {'below': 15, 'above': 25}},
    'Semiconductors': {'ebitda_margin': {'below': 20, 'above': 30}},
    'Financial Services': {'ebitda_margin': {'below': 15, 'above': 35}},
    'Technology': {'ebitda_margin': {'below': 20, 'above': 30}},
    'Auto': {'ebitda_margin': {'below': 6, 'above': 10}},
    'Healthcare': {'ebitda_margin': {'below': 15, 'above': 25}},
    'Consumer Staples': {'ebitda_margin': {'below': 12, 'above': 20}},
    'Beverages': {'ebitda_margin': {'below': 20, 'above': 30}},
    'Pharmaceuticals': {'ebitda_margin': {'below': 25, 'above': 35}},
    'Industrials': {'ebitda_margin': {'below': 10, 'above': 18}},
    'Aerospace': {'ebitda_margin': {'below': 10, 'above': 18}},
    'Media': {'ebitda_margin': {'below': 15, 'above': 25}},
    'Energy': {'ebitda_margin': {'below': 15, 'above': 25}},
}

VOLATILITY_ASSESSMENT = {
    'Technology Hardware': 3,
    'Auto Manufacturers': 4,
    'Technology Software': 2,
    'Media & Entertainment': 4,
    'Retail': 3,
    'Oil & Gas': 5,
    'Semiconductors': 4,
    'Financial Services': 3,
    'Technology': 3,
    'Auto': 4,
    'Healthcare': 3,
    'Consumer Staples': 2,
    'Beverages': 2,
    'Pharmaceuticals': 3,
    'Industrials': 3,
    'Aerospace': 4,
    'Media': 4,
    'Energy': 5,
}

# ----------------------------------------------------------------------
# Actual S&P ratings for validation (used in comparison tab)
# ----------------------------------------------------------------------
# These are loaded from CSV, but we also keep a fallback
def load_actual_ratings():
    """Load actual S&P ratings from CSV"""
    ratings_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'actual_ratings.csv')
    try:
        df = pd.read_csv(ratings_path)
        return {row['ticker']: row['sp_rating'] for _, row in df.iterrows()}
    except Exception as e:
        print(f"Error loading actual ratings: {e}")
        return {}

ACTUAL_RATINGS = load_actual_ratings()