"""
Data fetching module using Financial Modeling Prep (FMP) API
Updated to use /stable/ endpoints with full error handling and market cap fix
"""
from dotenv import load_dotenv
load_dotenv()

import os
import pandas as pd
import requests
import numpy as np
import logging
import time
import diskcache
import os
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Setup cache (24 hours)
cache = diskcache.Cache('data/cache')

# Get API key from environment variable (set in Render)
API_KEY = os.environ.get("FMP_API_KEY", "")

# Warn if API key is missing
if not API_KEY:
    logger.warning("⚠️ FMP_API_KEY environment variable not set! Please set it in Render dashboard.")

class DataFetcher:
    """Fetch financial data from Financial Modeling Prep API."""
    
    @classmethod
    def fetch_company_data(cls, ticker: str, force_refresh: bool = False) -> Optional[Dict]:
        """Fetch data with caching."""
        
        cache_key = f"company_data_{ticker}"
        
        # Check cache first (24 hour cache)
        if not force_refresh and cache_key in cache:
            logger.debug(f"{ticker}: Using cached data")
            return cache[cache_key]
        
        try:
            logger.info(f"{ticker}: Fetching from FMP...")
            
            # 1. Get company profile (for sector info)
            profile_url = f"https://financialmodelingprep.com/stable/profile?symbol={ticker}&apikey={API_KEY}"
            profile_response = requests.get(profile_url)
            
            if profile_response.status_code != 200:
                logger.error(f"{ticker}: Profile API error {profile_response.status_code}")
                return None
                
            profile_data = profile_response.json()
            
            if not profile_data or len(profile_data) == 0:
                logger.error(f"{ticker}: No profile data")
                return None
            
            profile = profile_data[0]
            
            # 2. Get market cap from quote endpoint (more reliable)
            try:
                quote_url = f"https://financialmodelingprep.com/stable/quote?symbol={ticker}&apikey={API_KEY}"
                quote_response = requests.get(quote_url)
                if quote_response.status_code == 200:
                    quote_data = quote_response.json()
                    if quote_data and len(quote_data) > 0:
                        market_cap = quote_data[0].get('marketCap', 0)
                        if market_cap:
                            profile['mktCap'] = market_cap
                            logger.debug(f"{ticker}: Market cap from quote: ${market_cap:,.0f}")
            except Exception as e:
                logger.debug(f"{ticker}: Could not fetch quote data: {e}")
            
            # 3. Get income statement (most recent annual)
            income_url = f"https://financialmodelingprep.com/stable/income-statement?symbol={ticker}&apikey={API_KEY}"
            income_response = requests.get(income_url)
            
            if income_response.status_code != 200:
                logger.error(f"{ticker}: Income statement API error {income_response.status_code}")
                return None
                
            income_data = income_response.json()
            
            # 4. Get balance sheet
            balance_url = f"https://financialmodelingprep.com/stable/balance-sheet-statement?symbol={ticker}&apikey={API_KEY}"
            balance_response = requests.get(balance_url)
            
            if balance_response.status_code != 200:
                logger.error(f"{ticker}: Balance sheet API error {balance_response.status_code}")
                return None
                
            balance_data = balance_response.json()
            
            # 5. Get cash flow statement
            cash_url = f"https://financialmodelingprep.com/stable/cash-flow-statement?symbol={ticker}&apikey={API_KEY}"
            cash_response = requests.get(cash_url)
            
            if cash_response.status_code != 200:
                logger.error(f"{ticker}: Cash flow API error {cash_response.status_code}")
                return None
                
            cash_data = cash_response.json()
            
            # Check if we have data
            if not income_data or len(income_data) == 0:
                logger.error(f"{ticker}: No income statement data")
                return None
                
            if not balance_data or len(balance_data) == 0:
                logger.error(f"{ticker}: No balance sheet data")
                return None
                
            if not cash_data or len(cash_data) == 0:
                logger.error(f"{ticker}: No cash flow data")
                return None
            
            # Extract data (use most recent - first in array)
            income = income_data[0]
            balance = balance_data[0]
            cash = cash_data[0]
            
            # Map FMP sectors to your sector names
            sector_map = {
                'Technology': 'Technology Hardware',
                'Healthcare': 'Health Care Services',
                'Consumer Cyclical': 'Retail',
                'Consumer Defensive': 'Retail',
                'Communication Services': 'Media & Entertainment',
                'Energy': 'Oil & Gas',
                'Financial Services': 'Financial Services',
                'Industrials': 'Auto Manufacturers',
                'Real Estate': 'Real Estate',
                'Utilities': 'Utilities',
                'Basic Materials': 'Basic Materials'
            }
            
            sector = profile.get('sector', 'Unknown')
            mapped_sector = sector_map.get(sector, sector)
            
            # Handle banks specially (they might have different data structure)
            if mapped_sector == 'Financial Services' and ticker == 'JPM':
                logger.info(f"{ticker}: Bank detected - using adjusted data")
                # For banks, we might need to adjust calculations
                pass
            
            # Build data dictionary matching your model's expected format
            data = {
                "ticker": ticker,
                "sector": mapped_sector,
                "data_year": income.get('date', str(datetime.now().year - 1)),
                "revenue": float(income.get('revenue', 0)),
                "ebitda": float(income.get('ebitda', 0)),
                "ebit": float(income.get('operatingIncome', 0)),
                "total_debt": float(balance.get('totalDebt', 0)),
                "cash": float(balance.get('cashAndCashEquivalents', 0)),
                "total_assets": float(balance.get('totalAssets', 0)),
                "total_equity": float(balance.get('totalEquity', 0)),
                "interest_expense": float(income.get('interestExpense', 1.0)) or 1.0,
                "operating_cf": float(cash.get('operatingCashFlow', 0)),
                "capex": float(cash.get('capitalExpenditure', 0)),
                "market_cap": float(profile.get('mktCap', 0)),
                "info": {
                    "sector": sector,
                    "companyName": profile.get('companyName', ''),
                    "industry": profile.get('industry', ''),
                    "exchange": profile.get('exchangeShortName', ''),
                    "currency": profile.get('currency', 'USD')
                }
            }
            
            # Cache for 24 hours
            cache.set(cache_key, data, expire=86400)
            logger.info(f"{ticker}: Data cached successfully")
            
            # Rate limit: be respectful (2 seconds between calls)
            time.sleep(2)
            
            return data
            
        except Exception as e:
            logger.error(f"{ticker}: Error – {e}")
            return None
    
    @classmethod
    def fetch_multiple_tickers(cls, tickers: List[str]) -> List[Dict]:
        """Fetch data for multiple tickers."""
        results = []
        for ticker in tickers:
            data = cls.fetch_company_data(ticker)
            if data:
                results.append(data)
        return results
    
    @classmethod
    def clear_cache(cls):
        """Clear the data cache."""
        cache.clear()
        logger.info("Cache cleared")

# Export
__all__ = ['DataFetcher', 'cache']
