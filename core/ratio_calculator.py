"""
Financial ratio calculator for KBRA Credit Rating Model.
Calculates all ratios required by the KBRA methodology.
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class RatioCalculator:
    """Calculate financial ratios based on KBRA methodology."""
    
    @staticmethod
    def calculate_all(data: Dict) -> Dict:
        """
        Calculate all required financial ratios from raw data.
        
        Args:
            data: Dictionary of raw financial data from DataFetcher
            
        Returns:
            Dictionary of calculated ratios
        """
        ratios = {}
        
        # Extract values with defaults
        revenue = data.get('revenue')
        ebit = data.get('ebit')
        ebitda = data.get('ebitda')
        total_assets = data.get('total_assets')
        total_debt = data.get('total_debt', 0)
        cash = data.get('cash', 0)
        operating_cf = data.get('operating_cf', 0)
        capex = data.get('capex', 0)
        interest = data.get('interest_expense', 1.0)
        
        # Log what we're working with
        logger.debug(f"Calculating ratios for {data.get('ticker')}")
        
        # ----- Size Metrics -----
        # Revenue in billions (for scoring)
        if revenue and revenue > 0:
            ratios['revenue_bn'] = revenue / 1_000_000_000
        else:
            ratios['revenue_bn'] = np.nan
        
        # ----- Profitability Metrics -----
        # EBIT Margin
        if revenue and revenue > 0 and ebit and ebit > 0:
            ratios['ebit_margin'] = ebit / revenue
        else:
            ratios['ebit_margin'] = np.nan
        
        # EBITDA Margin (additional metric for analysis)
        if revenue and revenue > 0 and ebitda and ebitda > 0:
            ratios['ebitda_margin'] = ebitda / revenue
        else:
            ratios['ebitda_margin'] = np.nan
        
        # Return on Assets (ROA)
        if total_assets and total_assets > 0 and ebitda and ebitda > 0:
            ratios['roa'] = ebitda / total_assets
        else:
            ratios['roa'] = np.nan
        
        # ----- Cash Flow Metrics -----
        # Free Cash Flow
        if operating_cf and capex:
            # Capex is usually negative, so we add it
            fcf = operating_cf - abs(capex)
            ratios['fcf'] = fcf
        else:
            fcf = None
            ratios['fcf'] = np.nan
        
        # FCF to Debt
        if total_debt > 0 and fcf and fcf != 0:
            ratios['fcf_to_debt'] = fcf / total_debt
        elif total_debt == 0:
            # No debt is perfect
            ratios['fcf_to_debt'] = np.inf
        else:
            ratios['fcf_to_debt'] = np.nan
        
        # ----- Leverage Metrics -----
        # Debt to EBITDA
        if ebitda and ebitda > 0 and total_debt > 0:
            ratios['debt_to_ebitda'] = total_debt / ebitda
        elif ebitda and ebitda > 0 and total_debt == 0:
            ratios['debt_to_ebitda'] = 0  # No debt
        else:
            ratios['debt_to_ebitda'] = np.nan
        
        # Net Debt to EBITDA (adjusted for cash)
        if ebitda and ebitda > 0 and total_debt > 0:
            net_debt = total_debt - cash
            if net_debt > 0:
                ratios['net_debt_to_ebitda'] = net_debt / ebitda
            else:
                ratios['net_debt_to_ebitda'] = 0  # Net cash position
        else:
            ratios['net_debt_to_ebitda'] = np.nan
        
        # Debt to Capital
        if total_debt > 0 and data.get('total_equity'):
            total_capital = total_debt + data['total_equity']
            if total_capital > 0:
                ratios['debt_to_capital'] = total_debt / total_capital
            else:
                ratios['debt_to_capital'] = np.nan
        else:
            ratios['debt_to_capital'] = np.nan
        
        # ----- Coverage Metrics -----
        # EBIT to Interest
        if ebit and ebit > 0 and interest and interest != 0:
            ratios['ebit_interest'] = ebit / abs(interest)
        else:
            ratios['ebit_interest'] = np.nan
        
        # EBITDA to Interest
        if ebitda and ebitda > 0 and interest and interest != 0:
            ratios['ebitda_interest'] = ebitda / abs(interest)
        else:
            ratios['ebitda_interest'] = np.nan
        
        # ----- Additional Metrics for Analysis -----
        # Cash to Debt
        if total_debt > 0:
            ratios['cash_to_debt'] = cash / total_debt
        elif total_debt == 0 and cash > 0:
            ratios['cash_to_debt'] = np.inf  # Infinite (no debt)
        else:
            ratios['cash_to_debt'] = np.nan
        
        # Operating Cash Flow to Debt
        if total_debt > 0 and operating_cf and operating_cf > 0:
            ratios['ocf_to_debt'] = operating_cf / total_debt
        elif total_debt == 0 and operating_cf > 0:
            ratios['ocf_to_debt'] = np.inf
        else:
            ratios['ocf_to_debt'] = np.nan
        
        # Current Ratio (if we have current assets/liabilities)
        # This is a placeholder - would need current assets/liabilities from balance sheet
        
        return ratios
    
    @staticmethod
    def get_key_metrics(ratios: Dict) -> Dict:
        """
        Extract only the key metrics needed for KBRA scoring.
        
        Args:
            ratios: Full dictionary of calculated ratios
            
        Returns:
            Dictionary with only KBRA-relevant metrics
        """
        key_metrics = {}
        
        # Metrics used in KBRA scoring
        metrics = [
            'revenue_bn',
            'ebit_margin',
            'roa',
            'fcf_to_debt',
            'debt_to_ebitda',
            'debt_to_capital',
            'ebit_interest',
            'ebitda_interest'
        ]
        
        for metric in metrics:
            if metric in ratios:
                key_metrics[metric] = ratios[metric]
            else:
                key_metrics[metric] = np.nan
        
        return key_metrics
    
    @staticmethod
    def format_ratios_for_display(ratios: Dict) -> Dict:
        """
        Format ratios for display in reports.
        
        Args:
            ratios: Dictionary of calculated ratios
            
        Returns:
            Dictionary with formatted values
        """
        formatted = {}
        
        for key, value in ratios.items():
            if isinstance(value, float):
                if 'margin' in key or 'roa' in key:
                    # Format as percentage
                    formatted[key] = f"{value*100:.1f}%"
                elif 'bn' in key:
                    # Format as billions with 1 decimal
                    formatted[key] = f"${value:.1f}B"
                elif 'debt' in key.lower() and 'ebitda' in key.lower():
                    # Format as ratio with 2 decimals
                    formatted[key] = f"{value:.2f}x"
                elif value == np.inf:
                    formatted[key] = "∞"
                elif pd.isna(value):
                    formatted[key] = "N/A"
                else:
                    # Default formatting
                    formatted[key] = f"{value:.2f}"
            else:
                formatted[key] = str(value)
        
        return formatted


# Convenience function
def calculate_ratios(data: Dict) -> Dict:
    """Convenience function to calculate ratios."""
    return RatioCalculator.calculate_all(data)