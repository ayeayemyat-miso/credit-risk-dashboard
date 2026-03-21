# tests/test_fmp.py
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data_fetcher import DataFetcher

# Test with one company
print("Testing FMP data fetch for AAPL...")
data = DataFetcher.fetch_company_data('AAPL', force_refresh=True)

if data:
    print(f"\n✅ Success! Got data for AAPL")
    print(f"Data Year: {data['data_year']}")
    print(f"Revenue: ${data['revenue']:,.0f}")
    print(f"EBITDA: ${data['ebitda']:,.0f}")
    print(f"EBIT: ${data['ebit']:,.0f}")
    print(f"Total Debt: ${data['total_debt']:,.0f}")
    print(f"Cash: ${data['cash']:,.0f}")
    print(f"Sector: {data['sector']}")
    print(f"Market Cap: ${data['market_cap']:,.0f}")
else:
    print("❌ Failed to get data")