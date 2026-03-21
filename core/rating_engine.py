"""
Rating engine for KBRA Credit Rating Model.
Combines business and financial risk to determine final credit ratings.
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, Optional, Tuple

from core import config
from core.risk_assessors import BusinessRiskAssessment, FinancialRiskAssessment

logger = logging.getLogger(__name__)


class RatingCalculator:
    """Determine final credit rating using KBRA methodology."""
    
    @classmethod
    def calculate_rating(cls, 
                        business_assessment: BusinessRiskAssessment,
                        financial_assessment: FinancialRiskAssessment) -> str:
        """
        Calculate final credit rating from business and financial assessments.
        
        Args:
            business_assessment: BusinessRiskAssessment object
            financial_assessment: FinancialRiskAssessment object
            
        Returns:
            Credit rating string (e.g., 'AAA', 'AA', 'A', 'BBB', etc.)
        """
        # Calculate scores
        business_score = business_assessment.calculate_weighted_score()
        financial_score = financial_assessment.calculate_weighted_score()
        
        # Convert business score to category
        business_category = cls._business_score_to_category(business_score)
        
        # Determine rating using Table 10
        rating = cls._determine_rating_from_table(business_category, financial_score)
        
        logger.debug(f"Business Score: {business_score:.2f} ({business_category}), "
                    f"Financial Score: {financial_score:.2f} → Rating: {rating}")
        
        return rating
    
    @classmethod
    def _business_score_to_category(cls, business_score: float) -> str:
        """
        Convert business risk score to category (Strong/Average/Weak).
        
        Args:
            business_score: Weighted business risk score (1-3 scale)
            
        Returns:
            Business category string
        """
        if business_score < 1.5:
            return "Strong"
        elif business_score < 2.5:
            return "Average"
        else:
            return "Weak"
    
    @classmethod
    def _determine_rating_from_table(cls, business_category: str, financial_score: float) -> str:
        """
        Determine rating using Table 10 from KBRA methodology.
        
        Args:
            business_category: 'Strong', 'Average', or 'Weak'
            financial_score: Financial risk score (1-18 scale)
            
        Returns:
            Credit rating string
        """
        rating_map = config.RATING_TABLE.get(business_category, {})
        
        for rating, (lower, upper) in rating_map.items():
            # Handle special cases
            if lower is None and upper is None:
                continue
            
            # No lower bound (e.g., AAA for Average/Weak)
            if lower is None:
                if financial_score < upper:
                    return rating
            
            # No upper bound (e.g., B for Strong)
            elif upper is None:
                if financial_score >= lower:
                    return rating
            
            # Normal case with both bounds
            else:
                if lower <= financial_score < upper:
                    return rating
        
        return "NR"  # Not Rated
    
    @classmethod
    def get_rating_numeric(cls, rating: str) -> int:
        """
        Convert rating to numeric value for comparison.
        
        Args:
            rating: Credit rating string (e.g., 'AAA', 'AA', 'A')
            
        Returns:
            Numeric value (lower = better)
        """
        rating_map = {
            'AAA': 1,
            'AA': 2,
            'A': 3,
            'BBB': 4,
            'BB': 5,
            'B': 6,
            'CCC': 7,
            'CC': 8,
            'C': 9,
            'D': 10,
            'NR': 99
        }
        
        # Handle modifiers (+, -) by taking the base rating
        base_rating = rating[:2] if rating.startswith('AA') else rating[0]
        
        return rating_map.get(base_rating, 99)
    
    @classmethod
    def compare_ratings(cls, rating1: str, rating2: str) -> Tuple[bool, int]:
        """
        Compare two ratings and check if they match within tolerance.
        
        Args:
            rating1: First rating (e.g., your calculated rating)
            rating2: Second rating (e.g., actual S&P rating)
            
        Returns:
            Tuple of (is_match, notch_difference)
        """
        num1 = cls.get_rating_numeric(rating1)
        num2 = cls.get_rating_numeric(rating2)
        
        notch_diff = abs(num1 - num2)
        is_match = notch_diff <= 1  # Within 1 notch is considered a match
        
        return is_match, notch_diff


class KBRAAnalyzer:
    """Main analyzer class that orchestrates the entire rating process."""
    
    def __init__(self, tickers: list, actual_ratings: dict = None):
        """
        Initialize the analyzer with tickers and optional actual ratings.
        
        Args:
            tickers: List of stock tickers to analyze
            actual_ratings: Dictionary of actual S&P ratings for validation
        """
        self.tickers = tickers
        self.actual_ratings = actual_ratings or {}
        self.results = []
        self.detailed_results = []
        
    def add_result(self, ticker: str, data: Dict, business_assessment: BusinessRiskAssessment,
                  financial_assessment: FinancialRiskAssessment, rating: str, ratios: Dict):
        """
        Add a company's results to the results list.
        
        Args:
            ticker: Stock ticker
            data: Raw financial data
            business_assessment: Business risk assessment
            financial_assessment: Financial risk assessment
            rating: Calculated rating
            ratios: Calculated financial ratios
        """
        # Summary result
        self.results.append({
            'Ticker': ticker,
            'Sector': data.get('sector', 'Unknown'),
            'Company': data.get('company_name', ticker),
            'Actual': self.actual_ratings.get(ticker, 'N/A'),
            'KBRA_Rating': rating,
            'Business_Score': round(business_assessment.calculate_weighted_score(), 2),
            'Financial_Score': round(financial_assessment.calculate_weighted_score(), 2),
            'Business_Category': business_assessment.to_dict()['industry_risk'],
            'Debt/EBITDA': round(ratios.get('debt_to_ebitda', 0), 2) if pd.notna(ratios.get('debt_to_ebitda')) else 'NaN',
            'EBIT/Interest': round(ratios.get('ebit_interest', 0), 1) if pd.notna(ratios.get('ebit_interest')) else 'NaN',
            'FCF/Debt': round(ratios.get('fcf_to_debt', 0), 3) if pd.notna(ratios.get('fcf_to_debt')) else 'NaN',
            'EBIT_Margin': round(ratios.get('ebit_margin', 0) * 100, 1) if pd.notna(ratios.get('ebit_margin')) else 'NaN',
            'ROA': round(ratios.get('roa', 0) * 100, 1) if pd.notna(ratios.get('roa')) else 'NaN'
        })
        
        # Detailed result
        business_dict = business_assessment.to_dict()
        financial_dict = financial_assessment.to_dict()
        
        self.detailed_results.append({
            'Ticker': ticker,
            'Company': data.get('company_name', ticker),
            'Sector': data.get('sector', 'Unknown'),
            'Data_Year': data.get('data_year', 'N/A'),
            'Actual_Rating': self.actual_ratings.get(ticker, 'N/A'),
            'KBRA_Rating': rating,
            
            # Raw financials
            'Revenue ($B)': round(data.get('revenue', 0) / 1e9, 1) if data.get('revenue') else 'NaN',
            'EBITDA ($B)': round(data.get('ebitda', 0) / 1e9, 1) if data.get('ebitda') else 'NaN',
            'EBIT ($B)': round(data.get('ebit', 0) / 1e9, 1) if data.get('ebit') else 'NaN',
            'Total Debt ($B)': round(data.get('total_debt', 0) / 1e9, 1),
            'Cash ($B)': round(data.get('cash', 0) / 1e9, 1),
            'Total Assets ($B)': round(data.get('total_assets', 0) / 1e9, 1) if data.get('total_assets') else 'NaN',
            
            # Ratios
            'EBITDA Margin %': round(ratios.get('ebitda_margin', 0) * 100, 1) if pd.notna(ratios.get('ebitda_margin')) else 'NaN',
            'EBIT Margin %': round(ratios.get('ebit_margin', 0) * 100, 1) if pd.notna(ratios.get('ebit_margin')) else 'NaN',
            'Debt/EBITDA': round(ratios.get('debt_to_ebitda', 0), 2) if pd.notna(ratios.get('debt_to_ebitda')) else 'NaN',
            'Net Debt/EBITDA': round(ratios.get('net_debt_to_ebitda', 0), 2) if pd.notna(ratios.get('net_debt_to_ebitda')) else 'NaN',
            'FCF/Debt': round(ratios.get('fcf_to_debt', 0), 3) if pd.notna(ratios.get('fcf_to_debt')) else 'NaN',
            'EBIT/Interest': round(ratios.get('ebit_interest', 0), 1) if pd.notna(ratios.get('ebit_interest')) else 'NaN',
            'ROA %': round(ratios.get('roa', 0) * 100, 1) if pd.notna(ratios.get('roa')) else 'NaN',
            'Cash/Debt': round(ratios.get('cash_to_debt', 0), 2) if pd.notna(ratios.get('cash_to_debt')) else 'Inf',
            
            # Risk Scores
            'Industry Risk': business_dict['industry_risk'],
            'Competitive Risk': business_dict['competitive_risk'],
            'Liquidity Risk': business_dict['liquidity_risk'],
            'Business Risk Score': business_dict['business_score'],
            
            # Financial Component Scores
            'Size Score': financial_dict['size_score'],
            'Profitability Score': financial_dict['profitability_score'],
            'Cash Flow Score': financial_dict['cash_flow_score'],
            'Leverage Score': financial_dict['leverage_score'],
            'Coverage Score': financial_dict['coverage_score'],
            'Financial Risk Score': financial_dict['financial_score'],
            
            'Business Category': business_dict['industry_risk']
        })
    
    def get_summary_dataframe(self) -> pd.DataFrame:
        """Get summary results as DataFrame."""
        return pd.DataFrame(self.results)
    
    def get_detailed_dataframe(self) -> pd.DataFrame:
        """Get detailed results as DataFrame."""
        return pd.DataFrame(self.detailed_results)
    
    def calculate_accuracy(self) -> Dict:
        """
        Calculate accuracy metrics compared to actual ratings.
        
        Returns:
            Dictionary with accuracy statistics
        """
        if not self.results:
            return {}
        
        df = pd.DataFrame(self.results)
        
        # Calculate matches (within 1 notch)
        matches = 0
        notch_diffs = []
        
        for _, row in df.iterrows():
            if row['Actual'] != 'N/A' and row['KBRA_Rating'] != 'N/A':
                is_match, notch_diff = RatingCalculator.compare_ratings(
                    row['KBRA_Rating'], row['Actual']
                )
                if is_match:
                    matches += 1
                notch_diffs.append(notch_diff)
        
        total = len(df[df['Actual'] != 'N/A'])
        
        return {
            'total_companies': total,
            'matches': matches,
            'match_rate': round(matches / total * 100, 1) if total > 0 else 0,
            'avg_notch_diff': round(np.mean(notch_diffs), 2) if notch_diffs else 0
        }


# Convenience function
def calculate_rating(business_assessment, financial_assessment):
    """Convenience function to calculate rating."""
    return RatingCalculator.calculate_rating(business_assessment, financial_assessment)