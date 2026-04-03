"""
ecl_calculator.py - IFRS 9 Expected Credit Loss
"""

import pandas as pd
import numpy as np

def rating_to_pd(rating):
    """Map KBRA rating to Probability of Default"""
    pd_map = {
        'AAA': 0.0004, 'AA+': 0.0005, 'AA': 0.0006, 'AA-': 0.0008,
        'A+': 0.0010, 'A': 0.0012, 'A-': 0.0015,
        'BBB+': 0.0020, 'BBB': 0.0030, 'BBB-': 0.0050,
        'BB+': 0.0100, 'BB': 0.0150, 'BB-': 0.0250,
        'B+': 0.0400, 'B': 0.0600, 'B-': 0.0900,
        'CCC+': 0.1500, 'CCC': 0.2000, 'CCC-': 0.2500,
        'CC': 0.3500, 'C': 0.5000, 'D': 0.8000
    }
    return pd_map.get(rating, 0.1000)

class IFRS9Calculator:
    """IFRS 9 ECL calculation with staging"""
    
    def __init__(self, lgd_senior=0.35, lgd_unsecured=0.55):
        self.lgd_senior = lgd_senior
        self.lgd_unsecured = lgd_unsecured
    
    def calculate_ecl(self, company):
        """Calculate ECL for a single company"""
        rating = company.get('final_rating', 'BBB')
        if pd.isna(rating):
            rating = 'BBB'
        pd_score = rating_to_pd(rating)
        
        revenue = company.get('revenue', 1000000000)
        if pd.isna(revenue):
            revenue = 1000000000
        ead = revenue * 0.3
        
        sector = company.get('sector', 'Technology')
        if pd.isna(sector):
            sector = 'Technology'
        
        if sector in ['Financial', 'Technology', 'Healthcare']:
            lgd = self.lgd_senior
        else:
            lgd = self.lgd_unsecured
        
        ecl_12m = pd_score * lgd * ead
        
        return {
            'pd': pd_score,
            'lgd': lgd,
            'ead': ead,
            'ecl_12m': ecl_12m,
            'company': company.get('name', company.get('symbol', 'Unknown')),
            'rating': rating,
            'symbol': company.get('symbol', company.get('ticker', ''))
        }
    
    def assign_stage(self, current_pd, previous_pd=None):
        """Assign IFRS 9 stage based on PD"""
        if current_pd > 0.20:
            return 3
        if previous_pd is not None and previous_pd > 0:
            relative_increase = current_pd / previous_pd
            absolute_increase = current_pd - previous_pd
            if relative_increase >= 2.0 or absolute_increase >= 0.015:
                return 2
        return 1
    
    def calculate_portfolio_ecl(self, companies_df, historical_ratings_df=None):
        """Calculate ECL for entire portfolio"""
        results = []
        total_ecl = 0
        stage_counts = {1: 0, 2: 0, 3: 0}
        
        historical_lookup = {}
        if historical_ratings_df is not None and len(historical_ratings_df) > 0:
            for _, row in historical_ratings_df.iterrows():
                symbol = row.get('symbol', '')
                if symbol:
                    historical_lookup[symbol] = row.get('rating', 'BBB')
        
        for _, company in companies_df.iterrows():
            ecl_data = self.calculate_ecl(company)
            
            previous_pd = None
            symbol = company.get('symbol', company.get('ticker', ''))
            if symbol in historical_lookup:
                prev_rating = historical_lookup[symbol]
                previous_pd = rating_to_pd(prev_rating)
            
            stage = self.assign_stage(ecl_data['pd'], previous_pd)
            
            if stage == 1:
                lifetime_ecl = ecl_data['ecl_12m']
            elif stage == 2:
                lifetime_ecl = ecl_data['ecl_12m'] * 1.5
            else:
                lifetime_ecl = ecl_data['ecl_12m'] * 2.0
            
            results.append({
                **ecl_data,
                'stage': stage,
                'ecl_lifetime': lifetime_ecl
            })
            
            total_ecl += lifetime_ecl
            stage_counts[stage] = stage_counts.get(stage, 0) + 1
        
        avg_pd = np.mean([r['pd'] for r in results]) if results else 0
        total_exposure = sum([r['ead'] for r in results])
        coverage_ratio = total_ecl / total_exposure if total_exposure > 0 else 0
        
        return {
            'companies': results,
            'total_ecl': total_ecl,
            'stage_breakdown': stage_counts,
            'avg_pd': avg_pd,
            'coverage_ratio': coverage_ratio,
            'total_exposure': total_exposure
        }