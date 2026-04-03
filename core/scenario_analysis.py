"""
scenario_analysis.py - Stress testing and what-if scenarios
"""

import numpy as np
import pandas as pd
from core.ecl_calculator import rating_to_pd, IFRS9Calculator

class ScenarioAnalyzer:
    """Stress testing and scenario analysis"""
    
    def __init__(self, companies_df):
        self.companies_df = companies_df
        self.base_ecl_calc = IFRS9Calculator()
    
    def get_base_ecl(self):
        """Calculate baseline ECL"""
        total = 0
        for _, company in self.companies_df.iterrows():
            rating = company.get('final_rating', 'BBB')
            if pd.isna(rating):
                rating = 'BBB'
            pd_score = rating_to_pd(rating)
            revenue = company.get('revenue', 1000000000)
            if pd.isna(revenue):
                revenue = 1000000000
            ead = revenue * 0.3
            total += pd_score * 0.45 * ead
        return total
    
    def macroeconomic_scenario(self, gdp_shock, interest_rate_change):
        """Apply macro stress to PDs"""
        if gdp_shock < 0:
            pd_multiplier = 1 + (abs(gdp_shock) * 0.25)
        else:
            pd_multiplier = 1 + (gdp_shock * 0.1)
        
        pd_multiplier = max(0.5, min(3.0, pd_multiplier))
        
        stressed_ecl_total = 0
        company_details = []
        
        for _, company in self.companies_df.iterrows():
            rating = company.get('final_rating', 'BBB')
            if pd.isna(rating):
                rating = 'BBB'
            base_pd = rating_to_pd(rating)
            stressed_pd = min(0.50, base_pd * pd_multiplier)
            
            revenue = company.get('revenue', 1000000000)
            if pd.isna(revenue):
                revenue = 1000000000
            ead = revenue * 0.3
            lgd = 0.45
            stressed_ecl = stressed_pd * lgd * ead
            
            stressed_ecl_total += stressed_ecl
            
            company_details.append({
                'name': company.get('name', company.get('ticker', 'Unknown')),
                'symbol': company.get('ticker', ''),
                'base_pd': base_pd,
                'stressed_pd': stressed_pd,
                'stressed_ecl': stressed_ecl
            })
        
        base_ecl = self.get_base_ecl()
        ecl_increase_pct = ((stressed_ecl_total - base_ecl) / base_ecl * 100) if base_ecl > 0 else 0
        
        company_details.sort(key=lambda x: x['stressed_ecl'], reverse=True)
        
        return {
            'scenario': f'GDP {gdp_shock:+.1f}%, Interest Rates {interest_rate_change:+.1f}%',
            'pd_multiplier': pd_multiplier,
            'base_ecl': base_ecl,
            'stressed_ecl': stressed_ecl_total,
            'ecl_increase_pct': ecl_increase_pct,
            'worst_affected': company_details[:5]
        }
    
    def sector_shock(self, sector, severity_percent):
        """Apply sector-specific shock"""
        sector_df = self.companies_df[self.companies_df['sector'] == sector]
        
        if len(sector_df) == 0:
            return {'error': f'Sector {sector} not found'}
        
        total_exposure = 0
        total_base_ecl = 0
        total_stressed_ecl = 0
        
        for _, company in sector_df.iterrows():
            rating = company.get('final_rating', 'BBB')
            if pd.isna(rating):
                rating = 'BBB'
            base_pd = rating_to_pd(rating)
            stressed_pd = min(0.50, base_pd * (1 + severity_percent))
            
            revenue = company.get('revenue', 1000000000)
            if pd.isna(revenue):
                revenue = 1000000000
            ead = revenue * 0.3
            total_exposure += ead
            
            base_ecl = base_pd * 0.45 * ead
            stressed_ecl = stressed_pd * 0.45 * ead
            
            total_base_ecl += base_ecl
            total_stressed_ecl += stressed_ecl
        
        return {
            'sector': sector,
            'severity': f'{severity_percent*100:.0f}%',
            'companies_affected': len(sector_df),
            'total_exposure': total_exposure,
            'base_ecl': total_base_ecl,
            'stressed_ecl': total_stressed_ecl,
            'increase_pct': ((total_stressed_ecl - total_base_ecl) / total_base_ecl * 100) if total_base_ecl > 0 else 0
        }