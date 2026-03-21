"""
Configuration file for KBRA Credit Rating Model.
Contains all constants, thresholds, and mapping tables.
"""

# Company to sector mapping (for your 10 companies)
COMPANY_SECTOR_MAP = {
    'AAPL': 'Technology Hardware',
    'MSFT': 'Technology Hardware',
    'NVDA': 'Technology Hardware',
    'GOOGL': 'Media & Entertainment',
    'WMT': 'Retail',
    'MCD': 'Retail',
    'HD': 'Retail',
    'TSLA': 'Auto Manufacturers',
    'XOM': 'Oil & Gas',
    'UNH': 'Health Care Services'
}

# KBRA Rating Table (Table 10 from methodology)
# Maps business risk category and financial score to final rating
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

# Financial metrics scoring thresholds (Table 8 from methodology)
# Maps metric values to scores on 1-18 scale (lower score = better)
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

# Industry risk rankings (simplified)
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
    "Real Estate": "Medium"
}

# Risk weights for business risk assessment
BUSINESS_RISK_WEIGHTS = {
    "industry": 0.40,
    "competitive": 0.35,
    "liquidity": 0.25
}

# Risk values mapping
RISK_VALUES = {
    "Strong": 1,
    "Average": 2,
    "Weak": 3
}

# Financial risk weights
FINANCIAL_RISK_WEIGHTS = {
    "size": 0.10,
    "profitability": 0.20,
    "cash_flow": 0.25,
    "leverage": 0.25,
    "coverage": 0.20
}

# Default tickers for analysis
DEFAULT_TICKERS = ['AAPL', 'MSFT', 'NVDA', 'WMT', 'MCD', 'UNH', 'TSLA', 'GOOGL', 'XOM', 'HD']

# Actual S&P ratings for validation
ACTUAL_RATINGS = {
    'AAPL': 'AA+',
    'MSFT': 'AAA',
    'NVDA': 'AA-',
    'WMT': 'AA',
    'MCD': 'BBB+',
    'UNH': 'A+',
    'TSLA': 'BBB',
    'GOOGL': 'AA+',
    'XOM': 'AA-',
    'HD': 'A'
}

# Output file names
OUTPUT_FILES = {
    'excel': 'kbra_ratings_{timestamp}.xlsx',
    'summary': 'output/reports/summary_{timestamp}.csv',
    'charts': 'output/charts/{chart_name}_{timestamp}.png'
}
