"""
model_validation.py - Statistical validation of rating methodology
"""

import pandas as pd
import numpy as np

RATING_ORDER = {
    'AAA': 1, 'AA+': 2, 'AA': 3, 'AA-': 4,
    'A+': 5, 'A': 6, 'A-': 7, 'BBB+': 8, 'BBB': 9,
    'BBB-': 10, 'BB+': 11, 'BB': 12, 'BB-': 13,
    'B+': 14, 'B': 15, 'B-': 16, 'CCC+': 17,
    'CCC': 18, 'CCC-': 19, 'CC': 20, 'C': 21, 'D': 22
}

def validate_ratings(companies_df):
    """Compare KBRA ratings vs actual S&P ratings"""
    df = companies_df.copy()
    
    if 'sp_rating' not in df.columns:
        return {'error': 'No S&P ratings found in data'}
    
    df = df.dropna(subset=['final_rating', 'sp_rating'])
    
    if len(df) == 0:
        return {'error': 'No comparison data available'}
    
    df['kbra_ordinal'] = df['final_rating'].map(RATING_ORDER)
    df['sp_ordinal'] = df['sp_rating'].map(RATING_ORDER)
    df = df.dropna(subset=['kbra_ordinal', 'sp_ordinal'])
    
    if len(df) == 0:
        return {'error': 'Rating mapping failed'}
    
    correct_matches = (df['kbra_ordinal'] == df['sp_ordinal']).sum()
    accuracy = correct_matches / len(df)
    
    expected_accuracy = 0
    for rating in set(df['kbra_ordinal']):
        p_kbra = (df['kbra_ordinal'] == rating).sum() / len(df)
        p_sp = (df['sp_ordinal'] == rating).sum() / len(df)
        expected_accuracy += p_kbra * p_sp
    
    kappa = (accuracy - expected_accuracy) / (1 - expected_accuracy) if expected_accuracy < 1 else 0
    
    diff = np.abs(df['kbra_ordinal'] - df['sp_ordinal'])
    within_one = (diff <= 1).sum() / len(df)
    within_two = (diff <= 2).sum() / len(df)
    
    misclassified = []
    for idx, row in df.iterrows():
        if row['kbra_ordinal'] != row['sp_ordinal']:
            misclassified.append({
                'symbol': row.get('symbol', row.get('ticker', '')),
                'name': row.get('name', ''),
                'final_rating': row['final_rating'],
                'sp_rating': row['sp_rating'],
                'diff_notches': abs(row['kbra_ordinal'] - row['sp_ordinal'])
            })
    
    misclassified.sort(key=lambda x: x['diff_notches'], reverse=True)
    
    return {
        'accuracy': round(accuracy, 3),
        'kappa': round(kappa, 3),
        'within_one_notch': round(within_one, 3),
        'within_two_notches': round(within_two, 3),
        'misclassified_count': len(misclassified),
        'misclassified': misclassified,
        'total_validated': len(df)
    }

def get_rating_distribution(companies_df):
    """Show distribution of KBRA ratings"""
    if 'final_rating' not in companies_df.columns:
        return {}
    return companies_df['final_rating'].value_counts().to_dict()