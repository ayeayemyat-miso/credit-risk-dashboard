"""
Risk assessment module for KBRA Credit Rating Model.
Assesses business risk and financial risk according to KBRA methodology.
"""

import numpy as np
import pandas as pd
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

from core import config

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Enums and Data Classes
# ----------------------------------------------------------------------
class RiskLevel(Enum):
    """Business risk classifications per KBRA methodology."""
    STRONG = "Strong"
    AVERAGE = "Average"
    WEAK = "Weak"


@dataclass
class BusinessRiskAssessment:
    """Container for business risk assessment results."""
    industry_risk: RiskLevel = RiskLevel.AVERAGE
    competitive_risk: RiskLevel = RiskLevel.AVERAGE
    liquidity_risk: RiskLevel = RiskLevel.AVERAGE
    
    industry_details: Dict = field(default_factory=dict)
    competitive_details: Dict = field(default_factory=dict)
    liquidity_details: Dict = field(default_factory=dict)
    
    def calculate_weighted_score(self) -> float:
        """Calculate weighted business risk score."""
        risk_values = {
            RiskLevel.STRONG: 1,
            RiskLevel.AVERAGE: 2,
            RiskLevel.WEAK: 3
        }
        
        score = (
            config.BUSINESS_RISK_WEIGHTS["industry"] * risk_values[self.industry_risk] +
            config.BUSINESS_RISK_WEIGHTS["competitive"] * risk_values[self.competitive_risk] +
            config.BUSINESS_RISK_WEIGHTS["liquidity"] * risk_values[self.liquidity_risk]
        )
        
        return score
    
    def to_dict(self) -> Dict:
        """Convert assessment to dictionary for reporting."""
        return {
            'industry_risk': self.industry_risk.value,
            'competitive_risk': self.competitive_risk.value,
            'liquidity_risk': self.liquidity_risk.value,
            'business_score': round(self.calculate_weighted_score(), 2)
        }


@dataclass
class FinancialRiskAssessment:
    """Container for financial risk assessment results."""
    size_score: float = 9.0
    profitability_score: float = 9.0
    cash_flow_score: float = 9.0
    leverage_score: float = 9.0
    coverage_score: float = 9.0
    
    def calculate_weighted_score(self) -> float:
        """Calculate weighted financial risk score."""
        score = (
            config.FINANCIAL_RISK_WEIGHTS["size"] * self.size_score +
            config.FINANCIAL_RISK_WEIGHTS["profitability"] * self.profitability_score +
            config.FINANCIAL_RISK_WEIGHTS["cash_flow"] * self.cash_flow_score +
            config.FINANCIAL_RISK_WEIGHTS["leverage"] * self.leverage_score +
            config.FINANCIAL_RISK_WEIGHTS["coverage"] * self.coverage_score
        )
        
        return score
    
    def to_dict(self) -> Dict:
        """Convert assessment to dictionary for reporting."""
        return {
            'size_score': self.size_score,
            'profitability_score': self.profitability_score,
            'cash_flow_score': self.cash_flow_score,
            'leverage_score': self.leverage_score,
            'coverage_score': self.coverage_score,
            'financial_score': round(self.calculate_weighted_score(), 2)
        }


# ----------------------------------------------------------------------
# Business Risk Assessor
# ----------------------------------------------------------------------
class BusinessRiskAssessor:
    """Assess business risk based on KBRA methodology."""
    
    @classmethod
    def assess_all(cls, data: Dict) -> BusinessRiskAssessment:
        """
        Perform complete business risk assessment.
        
        Args:
            data: Dictionary of company financial data
            
        Returns:
            BusinessRiskAssessment object
        """
        assessment = BusinessRiskAssessment()
        
        # Assess each component
        assessment.industry_risk = cls._assess_industry_risk(data)
        assessment.competitive_risk = cls._assess_competitive_risk(data)
        assessment.liquidity_risk = cls._assess_liquidity_risk(data)
        
        return assessment
    
    @classmethod
    def _assess_industry_risk(cls, data: Dict) -> RiskLevel:
        """
        Assess industry risk based on sector.
        
        Args:
            data: Company data with sector information
            
        Returns:
            RiskLevel (STRONG, AVERAGE, or WEAK)
        """
        sector = data.get('sector', 'Unknown')
        industry_risk = config.INDUSTRY_RISK_RANKING.get(sector, "Medium")
        
        if industry_risk in ["Low", "Medium-Low"]:
            return RiskLevel.STRONG
        elif industry_risk in ["Medium", "Medium-High"]:
            return RiskLevel.AVERAGE
        else:  # High, Very High
            return RiskLevel.WEAK
    
    @classmethod
    def _assess_competitive_risk(cls, data: Dict) -> RiskLevel:
        """
        Assess competitive risk based on company size and market position.
        
        Args:
            data: Company financial data
            
        Returns:
            RiskLevel (STRONG, AVERAGE, or WEAK)
        """
        revenue = data.get('revenue', 0) or 0
        market_cap = data.get('market_cap', 0) or 0
        
        # Size-based assessment
        if revenue > 100e9 or market_cap > 500e9:  # Mega-cap
            return RiskLevel.STRONG
        elif revenue > 25e9 or market_cap > 100e9:  # Large-cap
            return RiskLevel.AVERAGE
        else:  # Mid/small-cap
            return RiskLevel.WEAK
    
    @classmethod
    def _assess_liquidity_risk(cls, data: Dict) -> RiskLevel:
        """
        Assess liquidity risk based on cash flow and debt levels.
        
        Args:
            data: Company financial data
            
        Returns:
            RiskLevel (STRONG, AVERAGE, or WEAK)
        """
        cash = data.get('cash', 0) or 0
        operating_cf = data.get('operating_cf', 0) or 0
        total_debt = data.get('total_debt', 0) or 0
        
        if total_debt == 0:
            # No debt is excellent for liquidity
            return RiskLevel.STRONG
        
        # Calculate liquidity ratio (cash + operating CF) / debt
        liquidity_ratio = (cash + operating_cf) / total_debt if total_debt > 0 else float('inf')
        
        if liquidity_ratio > 1.5:
            return RiskLevel.STRONG
        elif liquidity_ratio > 0.8:
            return RiskLevel.AVERAGE
        else:
            return RiskLevel.WEAK


# ----------------------------------------------------------------------
# Financial Risk Assessor
# ----------------------------------------------------------------------
class FinancialRiskAssessor:
    """Assess financial risk based on KBRA methodology."""
    
    @classmethod
    def assess_all(cls, data: Dict, ratios: Dict) -> FinancialRiskAssessment:
        """
        Perform complete financial risk assessment.
        
        Args:
            data: Raw financial data
            ratios: Calculated financial ratios
            
        Returns:
            FinancialRiskAssessment object
        """
        assessment = FinancialRiskAssessment()
        
        # Score each component using Table 8 thresholds
        assessment.size_score = cls._score_metric(
            ratios.get('revenue_bn', np.nan), 
            'size_revenue_bn'
        )
        
        assessment.profitability_score = cls._score_metric(
            ratios.get('ebit_margin', np.nan), 
            'ebit_margin'
        )
        
        assessment.cash_flow_score = cls._score_metric(
            ratios.get('fcf_to_debt', np.nan), 
            'fcf_to_debt'
        )
        
        assessment.leverage_score = cls._score_metric(
            ratios.get('debt_to_ebitda', np.nan), 
            'debt_to_ebitda'
        )
        
        assessment.coverage_score = cls._score_metric(
            ratios.get('ebit_interest', np.nan), 
            'ebit_interest'
        )
        
        return assessment
    
    @classmethod
    def _score_metric(cls, value: float, metric_name: str) -> float:
        """
        Convert metric value to score on 1-18 scale using Table 8 thresholds.
        
        Args:
            value: The metric value to score
            metric_name: Name of the metric (lookup in FINANCIAL_THRESHOLDS)
            
        Returns:
            Score from 1-18 (lower is better)
        """
        # Handle special cases
        if pd.isna(value):
            return 9.0  # Default middle score
        
        # Handle infinite values (perfect scores)
        if value == np.inf:
            return 1.0  # Perfect score
        
        thresholds = config.FINANCIAL_THRESHOLDS.get(metric_name)
        if not thresholds:
            return 9.0
        
        # Determine if lower is better or higher is better
        lower_is_better = metric_name in ["debt_to_ebitda", "debt_to_capital"]
        
        for score in [1, 3, 6, 9, 12, 15, 18]:
            threshold = thresholds.get(score)
            if threshold is not None:
                if lower_is_better:
                    # For these metrics, lower values are better
                    if value <= threshold:
                        return score
                else:
                    # For these metrics, higher values are better
                    if value >= threshold:
                        return score
        
        # If we get here, return worst score
        return 18.0


# ----------------------------------------------------------------------
# Convenience functions
# ----------------------------------------------------------------------
def assess_business_risk(data: Dict) -> BusinessRiskAssessment:
    """Convenience function to assess business risk."""
    return BusinessRiskAssessor.assess_all(data)


def assess_financial_risk(data: Dict, ratios: Dict) -> FinancialRiskAssessment:
    """Convenience function to assess financial risk."""
    return FinancialRiskAssessor.assess_all(data, ratios)