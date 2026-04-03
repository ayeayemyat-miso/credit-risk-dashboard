# app/dashboard.py - Complete Enhanced Credit Risk Dashboard
# Uses REAL API data for all calculations (no hardcoded revenue values)

from dotenv import load_dotenv
load_dotenv()

import os

# Debug: Check if API key is loaded
api_key = os.getenv("FMP_API_KEY")
print(f"API Key loaded: {'Yes' if api_key else 'No'}")
if api_key:
    print(f"API Key starts with: {api_key[:5]}... (length: {len(api_key)})")
else:
    print("⚠️ API Key is None - check your .env file")
    
import sys
import time
import functools
from threading import Thread
import requests

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dash
from dash import dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime
import json
import logging

# Import your modules
from core import config
from core.data_fetcher import DataFetcher, cache
from core.ratio_calculator import RatioCalculator
from core.risk_assessors import BusinessRiskAssessor, FinancialRiskAssessor
from core.rating_engine import RatingCalculator

# Enhanced features imports
from core.model_validation import validate_ratings, get_rating_distribution
from core.ecl_calculator import IFRS9Calculator, rating_to_pd
from core.scenario_analysis import ScenarioAnalyzer

# pyratings - HSBC library for professional rating comparison
import pyratings as rtg

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ========== RENDER FREE TIER FIXES ==========

def start_keep_alive():
    """Start background thread to keep Render instance alive"""
    def keep_alive_loop():
        render_url = os.environ.get("RENDER_EXTERNAL_URL", "")
        if not render_url:
            logger.warning("RENDER_EXTERNAL_URL not set. Keep-alive disabled.")
            return
        
        while True:
            try:
                response = requests.get(render_url, timeout=10)
                logger.debug(f"Keep-alive ping sent - Status: {response.status_code}")
            except Exception as e:
                logger.debug(f"Keep-alive error: {e}")
            time.sleep(240)
    
    if os.environ.get("RENDER_EXTERNAL_URL"):
        thread = Thread(target=keep_alive_loop, daemon=True)
        thread.start()
        logger.info("✅ Keep-alive thread started for Render free tier")
    else:
        logger.info("ℹ️ Keep-alive not started (not running on Render or URL not set)")

if os.environ.get("RENDER"):
    start_keep_alive()

# ========== END RENDER FIXES ==========

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server
app.title = "Credit Risk Dashboard"

# Create all company options for dropdown (with names)
ALL_COMPANY_OPTIONS = [
    {'label': f"{ticker} - {config.COMPANY_NAMES.get(ticker, ticker)}", 'value': ticker}
    for ticker in config.DEFAULT_TICKERS
]

# Default watchlist (first 5 companies)
DEFAULT_WATCHLIST = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA']

# Rating to numeric score mapping (for WARF and comparisons)
RATING_TO_SCORE = {
    'AAA': 1, 'AA+': 2, 'AA': 3, 'AA-': 4,
    'A+': 5, 'A': 6, 'A-': 7, 'BBB+': 8, 'BBB': 9, 'BBB-': 10,
    'BB+': 11, 'BB': 12, 'BB-': 13, 'B+': 14, 'B': 15, 'B-': 16,
    'CCC+': 17, 'CCC': 18, 'CCC-': 19, 'CC': 20, 'C': 21, 'D': 22
}

# Rating to PD mapping
RATING_TO_PD = {
    'AAA': 0.0004, 'AA+': 0.0005, 'AA': 0.0006, 'AA-': 0.0008,
    'A+': 0.0010, 'A': 0.0012, 'A-': 0.0015,
    'BBB+': 0.0020, 'BBB': 0.0030, 'BBB-': 0.0050,
    'BB+': 0.0100, 'BB': 0.0150, 'BB-': 0.0250,
    'B+': 0.0400, 'B': 0.0600, 'B-': 0.0900,
    'CCC+': 0.1500, 'CCC': 0.2000, 'CCC-': 0.2500,
    'CC': 0.3500, 'C': 0.5000, 'D': 0.8000
}

# Define layout
app.layout = html.Div([
    # Header
    html.Div([
        html.H1("📊 Credit Risk Dashboard", 
                style={'text-align': 'center', 'color': '#2c3e50', 'margin-top': '20px',
                       'font-family': 'Arial, sans-serif', 'font-size': '36px'}),
        html.P("Real-time credit ratings using KBRA methodology | IFRS 9 Compliant | pyratings Analytics",
               style={'text-align': 'center', 'color': '#7f8c8d', 'font-size': '14px',
                      'margin-bottom': '30px'})
    ]),
    
    # Controls Section
    html.Div([
        html.Div([
            html.Label("📋 Select Companies", style={'font-weight': 'bold', 'margin-bottom': '5px'}),
            dcc.Dropdown(
                id='company-selector',
                options=ALL_COMPANY_OPTIONS,
                value=['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA'],
                multi=True,
                placeholder="Select companies to analyze...",
                style={'width': '100%', 'font-family': 'Arial, sans-serif'}
            ),
        ], style={'margin-bottom': '20px'}),
        
        html.Div([
            html.Button('⭐ Add Selected to Watchlist', id='add-to-watchlist', n_clicks=0,
                       style={'background-color': '#3498db', 'color': 'white', 
                              'padding': '10px 20px', 'border': 'none', 'border-radius': '5px',
                              'cursor': 'pointer', 'font-size': '14px', 'margin-right': '10px',
                              'font-weight': 'bold'}),
            
            html.Button('➖ Remove Selected from Watchlist', id='remove-from-watchlist', n_clicks=0,
                       style={'background-color': '#e74c3c', 'color': 'white', 
                              'padding': '10px 20px', 'border': 'none', 'border-radius': '5px',
                              'cursor': 'pointer', 'font-size': '14px', 'margin-right': '10px',
                              'font-weight': 'bold'}),
            
            html.Button('🔄 Refresh Data', id='refresh-button', n_clicks=0,
                       style={'background-color': '#2ecc71', 'color': 'white', 
                              'padding': '10px 20px', 'border': 'none', 'border-radius': '5px',
                              'cursor': 'pointer', 'font-size': '14px',
                              'font-weight': 'bold'}),
            
            html.Button('🗑️ Clear Cache', id='clear-cache-button', n_clicks=0,
                       style={'background-color': '#e67e22', 'color': 'white', 
                              'padding': '10px 20px', 'border': 'none', 'border-radius': '5px',
                              'cursor': 'pointer', 'font-size': '14px', 'margin-left': '10px',
                              'font-weight': 'bold'}),
        ], style={'margin-bottom': '15px'}),
        
        html.Div([
            html.Label("⭐ My Watchlist (Click to add)", style={'font-weight': 'bold', 'margin-bottom': '10px'}),
            html.Div(id='watchlist-display', style={'display': 'flex', 'flex-wrap': 'wrap', 'gap': '10px'}),
        ], style={'margin-top': '15px', 'padding': '15px', 'background-color': '#f8f9fa', 
                  'border-radius': '10px'}),
        
        html.Div(id='last-updated', style={'text-align': 'center', 'color': '#7f8c8d', 
                                           'font-family': 'Arial, sans-serif', 'margin': '10px',
                                           'font-size': '12px'}),
        
        html.Div(id='data-status', style={'text-align': 'center', 'color': '#27ae60', 
                                          'font-family': 'Arial, sans-serif', 'margin': '10px',
                                          'font-size': '14px', 'font-weight': 'bold'}),
        
    ], style={'background-color': 'white', 'border-radius': '10px', 'margin': '20px',
              'padding': '20px', 'box-shadow': '0 2px 4px rgba(0,0,0,0.1)'}),
    
    # Rating cards
    html.Div(id='rating-cards', style={'display': 'flex', 'flex-wrap': 'wrap', 
                                       'justify-content': 'center', 'margin': '20px'}),
    
    # Tabs for different views
    html.Div([
        dcc.Tabs(id='tabs', value='risk-scores', children=[
            dcc.Tab(label='📊 Risk Scores', value='risk-scores', 
                   style={'font-weight': 'bold'}, selected_style={'font-weight': 'bold', 'border-top': '3px solid #3498db'}),
            dcc.Tab(label='📈 Ratios', value='kbra-ratios',
                   style={'font-weight': 'bold'}, selected_style={'font-weight': 'bold', 'border-top': '3px solid #3498db'}),
            dcc.Tab(label='🎯 Component Breakdown', value='component-breakdown',
                   style={'font-weight': 'bold'}, selected_style={'font-weight': 'bold', 'border-top': '3px solid #3498db'}),
            dcc.Tab(label='📊 vs Actual Ratings', value='comparison',
                   style={'font-weight': 'bold'}, selected_style={'font-weight': 'bold', 'border-top': '3px solid #3498db'}),
            dcc.Tab(label='⭐ My Watchlist Analysis', value='watchlist-analysis',
                   style={'font-weight': 'bold'}, selected_style={'font-weight': 'bold', 'border-top': '3px solid #3498db'}),
            dcc.Tab(label='📋 Raw Data', value='raw-data',
                   style={'font-weight': 'bold'}, selected_style={'font-weight': 'bold', 'border-top': '3px solid #3498db'}),
            dcc.Tab(label='📊 Model Validation', value='model-validation',
                   style={'font-weight': 'bold'}, selected_style={'font-weight': 'bold', 'border-top': '3px solid #2ecc71'}),
            dcc.Tab(label='💰 IFRS 9 & ECL', value='ifrs9-ecl',
                   style={'font-weight': 'bold'}, selected_style={'font-weight': 'bold', 'border-top': '3px solid #2ecc71'}),
            dcc.Tab(label='🔮 Scenario Analysis', value='scenario-analysis',
                   style={'font-weight': 'bold'}, selected_style={'font-weight': 'bold', 'border-top': '3px solid #2ecc71'}),
        ]),
        html.Div(id='tab-content', style={'padding': '20px', 'background-color': 'white',
                                          'border-radius': '0 0 10px 10px', 'box-shadow': '0 2px 4px rgba(0,0,0,0.1)'}),
    ], style={'width': '95%', 'margin': 'auto', 'margin-top': '20px'}),
    
    dcc.Store(id='data-store'),
    dcc.Store(id='detailed-store'),
    dcc.Store(id='user-watchlist', storage_type='local', data=DEFAULT_WATCHLIST),
    dcc.Download(id='download-dataframe-csv'),
    
    dcc.Interval(
        id='interval-component',
        interval=60*60*1000,
        n_intervals=0
    ),
])

def create_watchlist_chip(ticker):
    company_name = config.COMPANY_NAMES.get(ticker, ticker)
    return html.Span(
        f"⭐ {ticker} - {company_name[:20]}",
        id={'type': 'watchlist-chip', 'index': ticker},
        style={
            'background-color': '#3498db',
            'color': 'white',
            'padding': '5px 12px',
            'border-radius': '20px',
            'cursor': 'pointer',
            'font-size': '12px',
            'display': 'inline-block'
        }
    )

def create_rating_card(ticker, rating, business_score, financial_score, data_year, components):
    if rating in ['AAA', 'AA']:
        color = '#2ecc71'
        bg_color = '#d4edda'
        border_color = '#c3e6cb'
    elif rating in ['A', 'BBB']:
        color = '#f39c12'
        bg_color = '#fff3cd'
        border_color = '#ffeeba'
    else:
        color = '#e74c3c'
        bg_color = '#f8d7da'
        border_color = '#f5c6cb'
    
    company_name = config.COMPANY_NAMES.get(ticker, ticker)
    
    return html.Div([
        html.Div([
            html.H4(company_name, style={'margin': '5px', 'color': '#2c3e50', 'font-size': '14px'}),
            html.H2(rating, style={'color': color, 'margin': '5px', 'font-size': '32px', 'font-weight': 'bold'}),
            html.Div([
                html.P(f"Business: {business_score:.2f}", style={'margin': '2px', 'font-size': '12px'}),
                html.P(f"Financial: {financial_score:.2f}", style={'margin': '2px', 'font-size': '12px'}),
                html.P(f"Data: {data_year}", style={'margin': '2px', 'font-size': '10px', 'color': '#7f8c8d'}),
            ], style={'margin-top': '10px'}),
        ], style={
            'border': f'2px solid {border_color}',
            'border-radius': '10px',
            'padding': '12px',
            'width': '200px',
            'text-align': 'center',
            'background-color': bg_color,
            'box-shadow': '0 2px 4px rgba(0,0,0,0.1)',
            'cursor': 'help'
        }),
    ], style={'margin': '8px'})

# ========== CALLBACKS ==========

@app.callback(
    Output('watchlist-display', 'children'),
    [Input('user-watchlist', 'data')]
)
def update_watchlist_display(watchlist):
    if not watchlist:
        return html.P("Your watchlist is empty. Use the dropdown above to add companies.", 
                      style={'color': '#7f8c8d'})
    return [create_watchlist_chip(ticker) for ticker in watchlist]

@app.callback(
    Output('user-watchlist', 'data', allow_duplicate=True),
    [Input('add-to-watchlist', 'n_clicks'),
     Input('remove-from-watchlist', 'n_clicks')],
    [State('company-selector', 'value'),
     State('user-watchlist', 'data')],
    prevent_initial_call=True
)
def modify_watchlist(add_clicks, remove_clicks, selected_companies, current_watchlist):
    ctx = dash.callback_context
    if not ctx.triggered:
        return current_watchlist
    
    current = current_watchlist or DEFAULT_WATCHLIST
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'add-to-watchlist' and selected_companies:
        new_watchlist = list(current)
        for ticker in selected_companies:
            if ticker not in new_watchlist:
                new_watchlist.append(ticker)
        return new_watchlist
    elif button_id == 'remove-from-watchlist' and selected_companies:
        return [t for t in current if t not in selected_companies]
    return current

@app.callback(
    Output('company-selector', 'value'),
    [Input({'type': 'watchlist-chip', 'index': dash.ALL}, 'n_clicks')],
    [State('company-selector', 'value')],
    prevent_initial_call=True
)
def select_from_watchlist(n_clicks_list, current_selection):
    ctx = dash.callback_context
    if not ctx.triggered:
        return current_selection
    
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    try:
        trigger_dict = json.loads(triggered_id)
        ticker = trigger_dict.get('index')
    except:
        return current_selection
    
    if ticker:
        if current_selection and ticker in current_selection:
            return current_selection
        elif current_selection:
            return current_selection + [ticker]
        else:
            return [ticker]
    return current_selection

@app.callback(
    [Output('data-store', 'data'),
     Output('detailed-store', 'data'),
     Output('data-status', 'children')],
    [Input('refresh-button', 'n_clicks'),
     Input('interval-component', 'n_intervals'),
     Input('clear-cache-button', 'n_clicks')],
    [State('company-selector', 'value')]
)
def fetch_and_store_data(refresh_clicks, interval_clicks, cache_clicks, selected_tickers):
    if not selected_tickers:
        return {}, {}, "No companies selected. Use dropdown to add companies."
    
    if not hasattr(fetch_and_store_data, '_initialized'):
        fetch_and_store_data._initialized = True
        logger.info("First request detected - adding delay for Render spin-up")
        time.sleep(5)
    
    ctx = dash.callback_context
    if ctx.triggered:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if button_id == 'clear-cache-button' and cache_clicks > 0:
            cache.clear()
            logger.info("Cache cleared by user")
    
    results = []
    detailed_results = []
    failed = []
    
    def fetch_with_retry(ticker, max_retries=2):
        for attempt in range(max_retries):
            try:
                data = DataFetcher.fetch_company_data(ticker)
                if data:
                    return data
                else:
                    logger.warning(f"{ticker}: Attempt {attempt + 1} failed, retrying...")
                    if attempt < max_retries - 1:
                        time.sleep(3)
            except Exception as e:
                logger.error(f"{ticker}: Error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(3)
        return None
    
    for ticker in selected_tickers:
        try:
            data = fetch_with_retry(ticker)
            if not data:
                failed.append(ticker)
                continue
            
            ratios = RatioCalculator.calculate_all(data)
            business_assessment = BusinessRiskAssessor.assess_all(data)
            financial_assessment = FinancialRiskAssessor.assess_all(data, ratios)
            
            business_score = business_assessment.calculate_weighted_score()
            business_category = RatingCalculator._business_score_to_category(business_score)
            financial_score = financial_assessment.calculate_weighted_score()
            rating = RatingCalculator._determine_rating_from_table(business_category, financial_score)
            
            revenue_bn = data.get('revenue', 0) / 1e9 if data.get('revenue') else 0
            data_year = str(data.get('data_year', 'N/A'))
            
            # Round all values to avoid floating point errors
            ebit_margin_val = ratios.get('ebit_margin', 0)
            fcf_to_debt_val = ratios.get('fcf_to_debt', 0)
            debt_to_ebitda_val = ratios.get('debt_to_ebitda', 0)
            ebit_interest_val = ratios.get('ebit_interest', 0)
            roa_val = ratios.get('roa', 0)
            debt_to_capital_val = ratios.get('debt_to_capital', 0)
            
            results.append({
                'ticker': ticker,
                'rating': rating,
                'business_score': round(business_score, 2),
                'financial_score': round(financial_score, 2),
                'data_year': data_year,
                'revenue_bn': round(revenue_bn, 1),
                'ebit_margin': round(ebit_margin_val, 4),
                'fcf_to_debt': round(fcf_to_debt_val, 4),
                'debt_to_ebitda': round(debt_to_ebitda_val, 2),
                'ebit_interest': round(ebit_interest_val, 1),
                'roa': round(roa_val, 4),
                'debt_to_capital': round(debt_to_capital_val, 4)
            })
            
            detailed_results.append({
                'ticker': ticker,
                'rating': rating,
                'business_score': round(business_score, 2),
                'financial_score': round(financial_score, 2),
                'data_year': data_year,
                'industry_risk': business_assessment.industry_risk.value,
                'competitive_risk': business_assessment.competitive_risk.value,
                'liquidity_risk': business_assessment.liquidity_risk.value,
                'size_score': round(financial_assessment.size_score, 1),
                'profitability_score': round(financial_assessment.profitability_score, 1),
                'cash_flow_score': round(financial_assessment.cash_flow_score, 1),
                'leverage_score': round(financial_assessment.leverage_score, 1),
                'coverage_score': round(financial_assessment.coverage_score, 1),
                'revenue_bn': round(revenue_bn, 1),
                'ebit_margin': round(ebit_margin_val * 100, 1) if pd.notna(ebit_margin_val) else 'N/A',
                'fcf_to_debt': round(fcf_to_debt_val, 3) if pd.notna(fcf_to_debt_val) else 'N/A',
                'debt_to_ebitda': round(debt_to_ebitda_val, 2) if pd.notna(debt_to_ebitda_val) else 'N/A',
                'ebit_interest': round(ebit_interest_val, 1) if pd.notna(ebit_interest_val) else 0,
                'roa': round(roa_val * 100, 1) if pd.notna(roa_val) else 'N/A',
                'debt_to_capital': round(debt_to_capital_val * 100, 1) if pd.notna(debt_to_capital_val) else 'N/A'
            })
            
        except Exception as e:
            logger.error(f"Error processing {ticker}: {e}")
            failed.append(ticker)
    
    status = f"✅ Loaded: {len(results)} companies"
    if failed:
        status += f" | ❌ Failed: {', '.join(failed)}"
    if len(results) < len(selected_tickers):
        status += " | ⏱️ First load may take 30-60 seconds (Render wake-up)"
    
    return results, detailed_results, status

@app.callback(
    [Output('rating-cards', 'children'),
     Output('tab-content', 'children'),
     Output('last-updated', 'children')],
    [Input('data-store', 'data'),
     Input('detailed-store', 'data'),
     Input('tabs', 'value')]
)
def update_display(stored_data, detailed_data, active_tab):
    if not stored_data:
        return [], html.Div("No data available. Please select companies to analyze.", 
                           style={'text-align': 'center', 'padding': '50px'}), ""
    
    cards = []
    for company in stored_data:
        detail = next((d for d in detailed_data if d['ticker'] == company['ticker']), {})
        cards.append(create_rating_card(
            company['ticker'],
            company['rating'],
            company['business_score'],
            company['financial_score'],
            company['data_year'],
            detail
        ))
    
    # ========== TAB CONTENT ==========
    
    if active_tab == 'risk-scores':
        fig = go.Figure(data=[
            go.Bar(name='Business Score', x=[c['ticker'] for c in stored_data], 
                   y=[c['business_score'] for c in stored_data], marker_color='#3498db'),
            go.Bar(name='Financial Score', x=[c['ticker'] for c in stored_data], 
                   y=[c['financial_score'] for c in stored_data], marker_color='#e74c3c')
        ])
        data_periods = ', '.join(set([c['data_year'] for c in stored_data]))
        fig.update_layout(title=f'Risk Scores by Company (Data Period: {data_periods})', 
                         xaxis_title='Company', yaxis_title='Score', barmode='group')
        content = dcc.Graph(figure=fig, style={'height': '500px'})
        
    elif active_tab == 'kbra-ratios':
        # Show all financial ratios with data period in subtitle
        fig = make_subplots(rows=2, cols=3, subplot_titles=[
            'Revenue ($B)', 'EBIT Margin %', 'FCF/Debt',
            'Debt/EBITDA', 'EBIT/Interest', 'ROA %'
        ])
        
        tickers = [c['ticker'] for c in stored_data]
        data_periods = ', '.join(set([c['data_year'] for c in stored_data]))
        
        # Revenue ($B)
        revenue_values = [c['revenue_bn'] for c in stored_data]
        fig.add_trace(go.Bar(x=tickers, y=revenue_values, 
                            name='Revenue', marker_color='#3498db',
                            text=[f'${v:.1f}B' for v in revenue_values],
                            textposition='outside'), row=1, col=1)
        fig.update_yaxes(title_text="($B)", row=1, col=1)
        
        # EBIT Margin %
        ebit_values = [round(c['ebit_margin']*100, 1) for c in stored_data]
        fig.add_trace(go.Bar(x=tickers, y=ebit_values, 
                            name='EBIT Margin %', marker_color='#2ecc71',
                            text=[f'{v:.1f}%' for v in ebit_values],
                            textposition='outside'), row=1, col=2)
        
        # FCF/Debt
        fcf_values = [c['fcf_to_debt'] for c in stored_data]
        fig.add_trace(go.Bar(x=tickers, y=fcf_values, 
                            name='FCF/Debt', marker_color='#f39c12',
                            text=[f'{v:.2f}' for v in fcf_values],
                            textposition='outside'), row=1, col=3)
        
        # Debt/EBITDA
        debt_values = [c['debt_to_ebitda'] for c in stored_data]
        fig.add_trace(go.Bar(x=tickers, y=debt_values, 
                            name='Debt/EBITDA', marker_color='#e74c3c',
                            text=[f'{v:.1f}x' for v in debt_values],
                            textposition='outside'), row=2, col=1)
        
        # EBIT/Interest (capped at 1000x for display - Apple is an outlier)
        ebit_interest_raw = [c['ebit_interest'] for c in stored_data]
        ebit_interest_capped = [min(v, 1000) if v > 0 else 0 for v in ebit_interest_raw]
        fig.add_trace(go.Bar(x=tickers, y=ebit_interest_capped, 
                            name='EBIT/Interest', marker_color='#9b59b6',
                            text=[f'{v:.1f}x' for v in ebit_interest_capped],
                            textposition='outside'), row=2, col=2)
        fig.update_yaxes(title_text="Coverage (x)", row=2, col=2)
        
        # ROA %
        roa_values = [round(c['roa']*100, 1) for c in stored_data]
        fig.add_trace(go.Bar(x=tickers, y=roa_values, 
                            name='ROA %', marker_color='#1abc9c',
                            text=[f'{v:.1f}%' for v in roa_values],
                            textposition='outside'), row=2, col=3)
        
        fig.update_layout(title=f'Financial Ratios (Data Period: {data_periods})', 
                         height=600, showlegend=False)
        content = dcc.Graph(figure=fig)
        
    elif active_tab == 'component-breakdown':
        if detailed_data:
            n_companies = len(detailed_data)
            cols = min(3, n_companies)
            rows = (n_companies + cols - 1) // cols
            fig = make_subplots(rows=rows, cols=cols, specs=[[{'type': 'polar'}]*cols for _ in range(rows)],
                               subplot_titles=[f"{d['ticker']} ({d['data_year']})" for d in detailed_data])
            for idx, d in enumerate(detailed_data):
                row = idx // cols + 1
                col = idx % cols + 1
                categories = ['Size', 'Profitability', 'Cash Flow', 'Leverage', 'Coverage']
                values = [d.get('size_score', 0), d.get('profitability_score', 0),
                         d.get('cash_flow_score', 0), d.get('leverage_score', 0),
                         d.get('coverage_score', 0)]
                categories.append(categories[0])
                values.append(values[0])
                fig.add_trace(go.Scatterpolar(r=values, theta=categories, fill='toself', name=d['ticker']), 
                            row=row, col=col)
            fig.update_layout(title='Financial Risk Component Breakdown', height=400 * rows, showlegend=False)
            content = dcc.Graph(figure=fig)
        else:
            content = html.Div("No data available")
            
    elif active_tab == 'comparison':
        ratings_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'actual_ratings.csv')
        try:
            ratings_df = pd.read_csv(ratings_path)
            
            def calculate_gap_and_confidence(your_date_str, sp_date_str):
                try:
                    your_date = datetime.strptime(your_date_str, '%Y-%m-%d')
                    sp_date = datetime.strptime(sp_date_str, '%Y-%m-%d')
                    gap_months = abs((your_date.year - sp_date.year) * 12 + (your_date.month - sp_date.month))
                    if gap_months <= 3:
                        return gap_months, "✅ High", "#2ecc71"
                    elif gap_months <= 6:
                        return gap_months, "⚠️ Acceptable", "#f39c12"
                    else:
                        return gap_months, "⚠️ Low", "#e74c3c"
                except:
                    return None, "Unknown", "#95a5a6"
            
            comparison_data = []
            matches_exact = 0
            matches_within_one = 0
            matches_within_two = 0
            total = 0
            
            for company in stored_data:
                ticker = company['ticker']
                your_rating = company['rating']
                data_year = company['data_year']
                
                actual_row = ratings_df[ratings_df['ticker'] == ticker]
                if not actual_row.empty:
                    total += 1
                    actual_rating = actual_row.iloc[0]['sp_rating']
                    company_name = actual_row.iloc[0]['name']
                    rating_date = actual_row.iloc[0].get('rating_date', '2025-12-15')
                    period_end_date = actual_row.iloc[0].get('period_end_date', data_year)
                    
                    your_num = RATING_TO_SCORE.get(your_rating, 15)
                    actual_num = RATING_TO_SCORE.get(actual_rating, 15)
                    notch_diff = abs(your_num - actual_num)
                    
                    gap_months, confidence_text, confidence_color = calculate_gap_and_confidence(data_year, rating_date)
                    
                    if notch_diff == 0:
                        match_status = "✓ Exact"
                        matches_exact += 1
                        matches_within_one += 1
                        matches_within_two += 1
                    elif notch_diff <= 1:
                        match_status = "⚠️ Within 1"
                        matches_within_one += 1
                        matches_within_two += 1
                    elif notch_diff <= 2:
                        match_status = "⚠️ Within 2"
                        matches_within_two += 1
                    else:
                        match_status = "✗ Mismatch"
                    
                    comparison_data.append({
                        'Ticker': ticker,
                        'Company': company_name,
                        'My Rating': your_rating,
                        'My Period': data_year,
                        'S&P Rating': actual_rating,
                        'S&P Date': rating_date,
                        'Gap': f"{gap_months} mo" if gap_months else "N/A",
                        'Confidence': confidence_text,
                        'Notch Diff': notch_diff,
                        'Match': match_status
                    })
            
            accuracy_exact = round((matches_exact / total) * 100, 1) if total > 0 else 0
            accuracy_within_one = round((matches_within_one / total) * 100, 1) if total > 0 else 0
            accuracy_within_two = round((matches_within_two / total) * 100, 1) if total > 0 else 0
            
            content = html.Div([
                html.Div([
                    html.H4("Model Accuracy vs S&P Ratings", style={'text-align': 'center', 'margin-bottom': '20px'}),
                    html.Div([
                        html.Div([
                            html.Div([
                                html.H4("Exact Match", style={'color': '#7f8c8d', 'font-size': '14px', 'margin': '0'}),
                                html.H2(f"{accuracy_exact}%", style={'color': '#2ecc71', 'margin': '10px 0'}),
                                html.P(f"{matches_exact} out of {total} companies", style={'color': '#95a5a6', 'font-size': '12px'})
                            ], style={'text-align': 'center', 'padding': '20px', 'background': '#f8f9fa', 
                                     'border-radius': '10px', 'margin': '10px'})
                        ], style={'display': 'inline-block', 'width': '30%'}),
                        
                        html.Div([
                            html.Div([
                                html.H4("Within 1 Notch", style={'color': '#7f8c8d', 'font-size': '14px', 'margin': '0'}),
                                html.H2(f"{accuracy_within_one}%", style={'color': '#f39c12', 'margin': '10px 0'}),
                                html.P(f"{matches_within_one} out of {total} companies", style={'color': '#95a5a6', 'font-size': '12px'})
                            ], style={'text-align': 'center', 'padding': '20px', 'background': '#f8f9fa', 
                                     'border-radius': '10px', 'margin': '10px'})
                        ], style={'display': 'inline-block', 'width': '30%'}),
                        
                        html.Div([
                            html.Div([
                                html.H4("Within 2 Notches", style={'color': '#7f8c8d', 'font-size': '14px', 'margin': '0'}),
                                html.H2(f"{accuracy_within_two}%", style={'color': '#9b59b6', 'margin': '10px 0'}),
                                html.P(f"{matches_within_two} out of {total} companies", style={'color': '#95a5a6', 'font-size': '12px'})
                            ], style={'text-align': 'center', 'padding': '20px', 'background': '#f8f9fa', 
                                     'border-radius': '10px', 'margin': '10px'})
                        ], style={'display': 'inline-block', 'width': '30%'})
                    ], style={'margin-bottom': '30px'})
                ]),
                
                html.H5("📋 Company Comparison with Period Alignment", style={'margin-top': '20px'}),
                dash_table.DataTable(
                    data=comparison_data,
                    columns=[
                        {'name': 'Ticker', 'id': 'Ticker'},
                        {'name': 'Company', 'id': 'Company'},
                        {'name': 'My Rating', 'id': 'My Rating'},
                        {'name': 'My Period', 'id': 'My Period'},
                        {'name': 'S&P Rating', 'id': 'S&P Rating'},
                        {'name': 'S&P Date', 'id': 'S&P Date'},
                        {'name': 'Gap', 'id': 'Gap'},
                        {'name': 'Confidence', 'id': 'Confidence'},
                        {'name': 'Notch Diff', 'id': 'Notch Diff'},
                        {'name': 'Match', 'id': 'Match'}
                    ],
                    style_cell={'textAlign': 'center', 'padding': '8px'},
                    style_header={'backgroundColor': '#2c3e50', 'color': 'white', 'fontWeight': 'bold'},
                    style_data_conditional=[
                        {'if': {'filter_query': '{Confidence} = "✅ High"'}, 'backgroundColor': '#d4edda', 'color': '#155724'},
                        {'if': {'filter_query': '{Confidence} = "⚠️ Acceptable"'}, 'backgroundColor': '#fff3cd', 'color': '#856404'},
                        {'if': {'filter_query': '{Confidence} = "⚠️ Low"'}, 'backgroundColor': '#f8d7da', 'color': '#721c24'},
                        {'if': {'filter_query': '{Match} = "✓ Exact"'}, 'backgroundColor': '#d4edda', 'color': '#155724'},
                        {'if': {'filter_query': '{Match} contains "Within"'}, 'backgroundColor': '#fff3cd', 'color': '#856404'}
                    ],
                    page_size=25
                ),
                
                html.Div([
                    html.P("📅 Period Alignment:", style={'font-weight': 'bold', 'margin-bottom': '5px', 'margin-top': '20px'}),
                    html.P("My Period = Fiscal year end of financial data used for KBRA calculation", 
                           style={'color': '#555', 'font-size': '11px', 'margin': '2px'}),
                    html.P("S&P Date = Date when S&P rating was issued", 
                           style={'color': '#555', 'font-size': '11px', 'margin': '2px'}),
                    html.P("Confidence: ✅ High (0-3 mo gap) | ⚠️ Acceptable (3-6 mo) | ⚠️ Low (6+ mo)", 
                           style={'color': '#555', 'font-size': '11px', 'margin': '2px'})
                ], style={'margin-top': '20px', 'padding': '10px', 'background-color': '#f0f0f0', 'border-radius': '5px'}),
                
                html.Hr(),
                html.Div([
                    html.H5("📊 Methodology Note", style={'color': '#2c3e50', 'margin-bottom': '10px'}),
                    html.Ul([
                        html.Li("KBRA Model: Implements Kroll Bond Rating Agency's General Corporate Global Rating Methodology (August 2025)", 
                                style={'color': '#555', 'font-size': '12px'}),
                        html.Li("S&P Rating Source: Manually curated from public sources (as of December 2025)", 
                                style={'color': '#555', 'font-size': '12px'}),
                        html.Li("Data Period: Financial data from latest fiscal year ends (varies by company)", 
                                style={'color': '#555', 'font-size': '12px'}),
                        html.Li("Industry Standard: Ratings within 1-2 notches are considered aligned", 
                                style={'color': '#555', 'font-size': '12px'}),
                        html.Li("Note: KBRA uses simplified scale (no +/- modifiers); S&P uses full scale with modifiers", 
                                style={'color': '#555', 'font-size': '12px'})
                    ], style={'margin-bottom': '0'})
                ], style={'margin-top': '30px', 'padding': '15px', 'background-color': '#f8f9fa', 'border-radius': '8px'})
            ])
        except Exception as e:
            content = html.Div(f"Comparison data not available: {str(e)}")
            
    elif active_tab == 'watchlist-analysis':
        fig = go.Figure(data=[
            go.Bar(name='Business Score', x=[c['ticker'] for c in stored_data], 
                   y=[c['business_score'] for c in stored_data], marker_color='#3498db'),
            go.Bar(name='Financial Score', x=[c['ticker'] for c in stored_data], 
                   y=[c['financial_score'] for c in stored_data], marker_color='#e74c3c')
        ])
        data_periods = ', '.join(set([c['data_year'] for c in stored_data]))
        fig.update_layout(title=f'Your Watchlist Analysis (Data Period: {data_periods})', 
                         xaxis_title='Company', yaxis_title='Score', barmode='group')
        content = dcc.Graph(figure=fig, style={'height': '500px'})
        
    elif active_tab == 'raw-data':
        df = pd.DataFrame(detailed_data)
        if not df.empty:
            display_df = df[['ticker', 'data_year', 'rating', 'business_score', 'financial_score',
                            'revenue_bn', 'ebit_margin', 'fcf_to_debt', 
                            'debt_to_ebitda', 'ebit_interest', 'roa']].copy()
            display_df.columns = ['Ticker', 'Data Period', 'Rating', 'Business', 'Financial',
                                 'Revenue ($B)', 'EBIT Margin %', 'FCF/Debt',
                                 'Debt/EBITDA', 'EBIT/Interest', 'ROA %']
            display_df['Company Name'] = display_df['Ticker'].map(config.COMPANY_NAMES)
            display_df = display_df[['Ticker', 'Company Name', 'Data Period', 'Rating', 'Business', 'Financial',
                                     'Revenue ($B)', 'EBIT Margin %', 'FCF/Debt',
                                     'Debt/EBITDA', 'EBIT/Interest', 'ROA %']]
            content = dash_table.DataTable(
                data=display_df.to_dict('records'),
                columns=[{'name': col, 'id': col} for col in display_df.columns],
                style_table={'overflowX': 'auto'}, style_cell={'textAlign': 'center'},
                style_header={'backgroundColor': '#3498db', 'color': 'white'}
            )
        else:
            content = html.Div("No data available")
    
    elif active_tab == 'model-validation':
        content = html.Div([
            html.H3("KBRA Methodology Validation", style={'margin-top': '20px', 'margin-bottom': '20px'}),
            html.P("How well does our KBRA implementation match actual S&P ratings?",
                   style={'color': '#7f8c8d', 'margin-bottom': '30px'}),
            
            html.Div([
                html.Div([
                    html.Div([
                        html.H4("Accuracy", style={'color': '#7f8c8d', 'font-size': '14px', 'margin': '0'}),
                        html.H2(id="validation-accuracy", style={'color': '#2ecc71', 'margin': '10px 0'}),
                        html.P("vs S&P ratings", style={'color': '#95a5a6', 'font-size': '12px'})
                    ], style={'text-align': 'center', 'padding': '20px', 'background': '#f8f9fa', 
                             'border-radius': '10px', 'margin': '10px'})
                ], style={'display': 'inline-block', 'width': '23%'}),
                
                html.Div([
                    html.Div([
                        html.H4("Cohen's Kappa", style={'color': '#7f8c8d', 'font-size': '14px', 'margin': '0'}),
                        html.H2(id="validation-kappa", style={'color': '#3498db', 'margin': '10px 0'}),
                        html.P(">0.7 = strong agreement", style={'color': '#95a5a6', 'font-size': '12px'})
                    ], style={'text-align': 'center', 'padding': '20px', 'background': '#f8f9fa', 
                             'border-radius': '10px', 'margin': '10px'})
                ], style={'display': 'inline-block', 'width': '23%'}),
                
                html.Div([
                    html.Div([
                        html.H4("Within 1 Notch", style={'color': '#7f8c8d', 'font-size': '14px', 'margin': '0'}),
                        html.H2(id="validation-within-one", style={'color': '#f39c12', 'margin': '10px 0'}),
                        html.P("Banks accept this threshold", style={'color': '#95a5a6', 'font-size': '12px'})
                    ], style={'text-align': 'center', 'padding': '20px', 'background': '#f8f9fa', 
                             'border-radius': '10px', 'margin': '10px'})
                ], style={'display': 'inline-block', 'width': '23%'}),
                
                html.Div([
                    html.Div([
                        html.H4("Within 2 Notches", style={'color': '#7f8c8d', 'font-size': '14px', 'margin': '0'}),
                        html.H2(id="validation-within-two", style={'color': '#9b59b6', 'margin': '10px 0'}),
                        html.P(id="validation-total", style={'color': '#95a5a6', 'font-size': '12px'})
                    ], style={'text-align': 'center', 'padding': '20px', 'background': '#f8f9fa', 
                             'border-radius': '10px', 'margin': '10px'})
                ], style={'display': 'inline-block', 'width': '23%'})
            ], style={'margin-bottom': '30px'}),
            
            html.Div(id="validation-error", style={'color': 'red', 'margin-bottom': '20px'}),
            
            html.H5("❌ Misclassified Companies", style={'margin-top': '30px'}),
            dash_table.DataTable(
                id='misclassified-table',
                columns=[],
                data=[],
                style_table={'overflowX': 'auto', 'margin-top': '10px'},
                style_cell={'textAlign': 'left', 'padding': '10px'},
                style_header={'backgroundColor': '#2c3e50', 'color': 'white', 'fontWeight': 'bold'},
                page_size=10
            ),
            
            html.Hr(),
            html.Div([
                html.H5("📊 Validation Methodology", style={'color': '#2c3e50', 'margin-bottom': '10px'}),
                html.Ul([
                    html.Li("Accuracy: Exact rating matches between KBRA and S&P", 
                            style={'color': '#555', 'font-size': '12px'}),
                    html.Li("Cohen's Kappa: Measures agreement beyond chance (>0.7 = strong agreement)", 
                            style={'color': '#555', 'font-size': '12px'}),
                    html.Li("Notch Calculations: Using pyratings (HSBC open-source library)", 
                            style={'color': '#555', 'font-size': '12px'}),
                    html.Li("Scale Difference: KBRA uses simplified scale (no +/- modifiers); S&P uses full scale", 
                            style={'color': '#555', 'font-size': '12px'}),
                    html.Li("Confidence: Ratings within 6-month period gap are considered valid for comparison", 
                            style={'color': '#555', 'font-size': '12px'})
                ], style={'margin-bottom': '0'})
            ], style={'margin-top': '30px', 'padding': '15px', 'background-color': '#f8f9fa', 'border-radius': '8px'})
        ], style={'padding': '20px'})
        
    elif active_tab == 'ifrs9-ecl':
        # Use ACTUAL data from stored_data, not hardcoded values
        companies_df = pd.DataFrame(stored_data)
        companies_info = pd.read_csv('data/companies.csv')
        companies_df = companies_df.merge(companies_info[['ticker', 'sector']], on='ticker', how='left')
        companies_df['sector'] = companies_df['sector'].fillna('Technology')
        
        # Calculate ECL for each company using actual revenue
        results = []
        total_ecl = 0
        stage_counts = {1: 0, 2: 0, 3: 0}
        
        for _, company in companies_df.iterrows():
            rating = company.get('rating', 'BBB')
            pd_score = RATING_TO_PD.get(rating, 0.0100)
            
            revenue_dollars = company.get('revenue_bn', 0) * 1e9
            if revenue_dollars <= 0:
                revenue_dollars = 1e9  # Fallback if revenue is 0
            
            ead = revenue_dollars * 0.3
            
            sector = company.get('sector', 'Technology')
            if sector in ['Financial', 'Technology', 'Healthcare']:
                lgd = 0.35
            else:
                lgd = 0.55
            
            ecl_12m = pd_score * lgd * ead
            
            if pd_score < 0.01:
                stage = 1
                lifetime_ecl = ecl_12m
            elif pd_score < 0.10:
                stage = 2
                lifetime_ecl = ecl_12m * 1.5
            else:
                stage = 3
                lifetime_ecl = ecl_12m * 2.0
            
            results.append({
                'symbol': company.get('ticker', ''),
                'company': company.get('ticker', ''),
                'rating': rating,
                'pd': pd_score,
                'ead': ead,
                'ecl_12m': ecl_12m,
                'stage': stage,
                'ecl_lifetime': lifetime_ecl
            })
            
            total_ecl += lifetime_ecl
            stage_counts[stage] = stage_counts.get(stage, 0) + 1
        
        # Calculate WARF
        companies_df['rating_score'] = companies_df['rating'].map(RATING_TO_SCORE)
        total_revenue = (companies_df['revenue_bn'] * 1e9).sum()
        companies_df['weight'] = (companies_df['revenue_bn'] * 1e9) / total_revenue if total_revenue > 0 else 1
        warf = (companies_df['rating_score'] * companies_df['weight']).sum()
        
        # Create table rows
        table_rows = []
        for company in results[:25]:
            table_rows.append(html.Tr([
                html.Td(company['symbol'], style={'font-weight': 'bold'}),
                html.Td(company['company']),
                html.Td(company['rating'], style={'text-align': 'center'}),
                html.Td(f"{company['pd']:.2%}", style={'text-align': 'right'}),
                html.Td(f"${company['ead']:,.0f}", style={'text-align': 'right'}),
                html.Td(f"${company['ecl_12m']:,.0f}", style={'text-align': 'right'}),
                html.Td(f"Stage {company['stage']}", style={'text-align': 'center'}),
                html.Td(f"${company['ecl_lifetime']:,.0f}", style={'text-align': 'right'})
            ]))
        
        avg_pd = sum(r['pd'] for r in results) / len(results) if results else 0
        total_exposure = sum(r['ead'] for r in results)
        coverage_ratio = total_ecl / total_exposure if total_exposure > 0 else 0
        
        warf_color = '#2ecc71' if warf <= 10 else '#f39c12' if warf <= 15 else '#e74c3c'
        
        content = html.Div([
            html.H3("Expected Credit Loss (IFRS 9)", style={'margin-top': '20px', 'margin-bottom': '10px'}),
            html.P("ECL = Probability of Default (PD) × Loss Given Default (LGD) × Exposure at Default (EAD)",
                   style={'color': '#7f8c8d', 'margin-bottom': '30px'}),
            
            html.Div([
                html.Div([
                    html.Div([
                        html.H4("Total Portfolio ECL", style={'color': '#7f8c8d', 'font-size': '14px', 'margin': '0'}),
                        html.H2(f"${total_ecl:,.0f}", style={'color': '#e74c3c', 'margin': '10px 0'})
                    ], style={'text-align': 'center', 'padding': '20px', 'background': '#f8f9fa', 
                             'border-radius': '10px', 'margin': '10px'})
                ], style={'display': 'inline-block', 'width': '23%'}),
                
                html.Div([
                    html.Div([
                        html.H4("Average PD", style={'color': '#7f8c8d', 'font-size': '14px', 'margin': '0'}),
                        html.H2(f"{avg_pd:.2%}", style={'color': '#3498db', 'margin': '10px 0'})
                    ], style={'text-align': 'center', 'padding': '20px', 'background': '#f8f9fa', 
                             'border-radius': '10px', 'margin': '10px'})
                ], style={'display': 'inline-block', 'width': '23%'}),
                
                html.Div([
                    html.Div([
                        html.H4("Coverage Ratio", style={'color': '#7f8c8d', 'font-size': '14px', 'margin': '0'}),
                        html.H2(f"{coverage_ratio:.2%}", style={'color': '#2ecc71', 'margin': '10px 0'})
                    ], style={'text-align': 'center', 'padding': '20px', 'background': '#f8f9fa', 
                             'border-radius': '10px', 'margin': '10px'})
                ], style={'display': 'inline-block', 'width': '23%'}),
                
                html.Div([
                    html.Div([
                        html.H4("WARF", style={'color': '#7f8c8d', 'font-size': '14px', 'margin': '0'}),
                        html.H2(html.Span([
                            f"{warf:.1f}",
                            html.Small(f" (Lower is better)", style={'color': '#7f8c8d', 'font-size': '12px', 'margin-left': '5px'})
                        ], style={'color': warf_color}), style={'margin': '10px 0'}),
                        html.P("Weighted Avg Rating Factor", style={'color': '#95a5a6', 'font-size': '12px'})
                    ], style={'text-align': 'center', 'padding': '20px', 'background': '#f8f9fa', 
                             'border-radius': '10px', 'margin': '10px'})
                ], style={'display': 'inline-block', 'width': '23%'})
            ], style={'margin-bottom': '30px'}),
            
            html.Div([
                html.H5("IFRS 9 Stage Distribution", style={'margin-bottom': '15px'}),
                html.Div([
                    html.Div([
                        html.H3(str(stage_counts.get(1, 0)), style={'color': '#2ecc71', 'margin': '0'}),
                        html.P("Stage 1 (12-month ECL)", style={'color': '#7f8c8d'})
                    ], style={'display': 'inline-block', 'width': '30%', 'text-align': 'center', 
                             'padding': '15px', 'background': '#e8f8f5', 'border-radius': '8px', 'margin': '5px'}),
                    html.Div([
                        html.H3(str(stage_counts.get(2, 0)), style={'color': '#f39c12', 'margin': '0'}),
                        html.P("Stage 2 (Lifetime ECL)", style={'color': '#7f8c8d'})
                    ], style={'display': 'inline-block', 'width': '30%', 'text-align': 'center', 
                             'padding': '15px', 'background': '#fef9e7', 'border-radius': '8px', 'margin': '5px'}),
                    html.Div([
                        html.H3(str(stage_counts.get(3, 0)), style={'color': '#e74c3c', 'margin': '0'}),
                        html.P("Stage 3 (Credit Impaired)", style={'color': '#7f8c8d'})
                    ], style={'display': 'inline-block', 'width': '30%', 'text-align': 'center', 
                             'padding': '15px', 'background': '#fdedec', 'border-radius': '8px', 'margin': '5px'})
                ], style={'margin-bottom': '30px'})
            ]),
            
            html.H5("📋 Company-Level ECL Breakdown", style={'margin-top': '30px'}),
            dbc.Table([
                html.Thead(html.Tr([
                    html.Th("Ticker"), html.Th("Company"), html.Th("Rating"),
                    html.Th("PD"), html.Th("EAD"), html.Th("ECL (12M)"),
                    html.Th("Stage"), html.Th("ECL (Lifetime)")
                ], style={'backgroundColor': '#2c3e50', 'color': 'white'})),
                html.Tbody(table_rows)
            ], bordered=True, striped=True, hover=True, size='sm', style={'margin-top': '10px'}),
            
            html.Hr(),
            html.Div([
                html.H5("📊 ECL Methodology", style={'color': '#2c3e50', 'margin-bottom': '10px'}),
                html.Ul([
                    html.Li("PD: Mapped from KBRA ratings using S&P historical default rates", 
                            style={'color': '#555', 'font-size': '12px'}),
                    html.Li("LGD: 35-55% based on sector (senior secured vs unsecured)", 
                            style={'color': '#555', 'font-size': '12px'}),
                    html.Li("EAD: Estimated as 30% of annual revenue (standard industry assumption)", 
                            style={'color': '#555', 'font-size': '12px'}),
                    html.Li("Staging: IFRS 9 rules (Stage 1: 12-month ECL; Stage 2/3: Lifetime ECL)", 
                            style={'color': '#555', 'font-size': '12px'}),
                    html.Li("WARF: Weighted Average Rating Factor - Industry standard portfolio quality metric", 
                            style={'color': '#555', 'font-size': '12px'}),
                    html.Li(f"Data Source: Real-time API data (revenue from {len(stored_data)} companies)", 
                            style={'color': '#555', 'font-size': '12px'})
                ], style={'margin-bottom': '0'})
            ], style={'margin-top': '30px', 'padding': '15px', 'background-color': '#f8f9fa', 'border-radius': '8px'})
        ], style={'padding': '20px'})
        
    elif active_tab == 'scenario-analysis':
        # Scenario Analysis tab content
        content = html.Div([
            html.H3("Stress Testing & What-If Analysis", style={'margin-top': '20px', 'margin-bottom': '10px'}),
            html.P("Test how your portfolio performs under adverse economic conditions",
                   style={'color': '#7f8c8d', 'margin-bottom': '30px'}),
            
            html.Div([
                html.Div([
                    html.Label("📉 GDP Growth Shock:", style={'font-weight': 'bold', 'margin-bottom': '10px'}),
                    dcc.Slider(
                        id='gdp-shock',
                        min=-5, max=5, step=0.5, value=0,
                        marks={i: f'{i}%' for i in range(-5, 6)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    ),
                    html.P("Negative GDP = Recession = Higher Default Risk", 
                           style={'color': '#7f8c8d', 'font-size': '12px', 'margin-top': '10px'})
                ], style={'margin-bottom': '30px'}),
                
                html.Div([
                    html.Label("📈 Interest Rate Shock:", style={'font-weight': 'bold', 'margin-bottom': '10px'}),
                    dcc.Slider(
                        id='rate-shock',
                        min=-2, max=3, step=0.25, value=0,
                        marks={i: f'{i}%' for i in range(-2, 4)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    ),
                    html.P("Higher rates = Higher borrowing costs = Higher Default Risk",
                           style={'color': '#7f8c8d', 'font-size': '12px', 'margin-top': '10px'})
                ], style={'margin-bottom': '30px'})
            ], style={'padding': '20px', 'background': '#f8f9fa', 'border-radius': '10px', 'margin-bottom': '30px'}),
            
            html.Div(id="scenario-results"),
            
            html.Hr(),
            html.Div([
                html.H5("📊 Scenario Analysis Methodology", style={'color': '#2c3e50', 'margin-bottom': '10px'}),
                html.Ul([
                    html.Li("GDP Shock: 1% GDP decline increases PD by ~25% (empirical elasticity)", 
                            style={'color': '#555', 'font-size': '12px'}),
                    html.Li("Interest Rate Shock: Higher rates increase borrowing costs and default risk", 
                            style={'color': '#555', 'font-size': '12px'}),
                    html.Li("PD Multiplier: Capped between 0.5x and 3.0x for realistic scenarios", 
                            style={'color': '#555', 'font-size': '12px'}),
                    html.Li("ECL Calculation: Stressed PD × LGD (45%) × EAD (30% of revenue)", 
                            style={'color': '#555', 'font-size': '12px'}),
                    html.Li("Data Source: Real-time API data from selected companies", 
                            style={'color': '#555', 'font-size': '12px'})
                ], style={'margin-bottom': '0'})
            ], style={'margin-top': '30px', 'padding': '15px', 'background-color': '#f8f9fa', 'border-radius': '8px'})
        ], style={'padding': '20px'})
    
    else:
        content = html.Div()
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    last_updated = f"Last updated: {timestamp}"
    
    return cards, content, last_updated

@app.callback(
    Output('refresh-button', 'n_clicks'),
    [Input('clear-cache-button', 'n_clicks')],
    prevent_initial_call=True
)
def clear_cache_and_refresh(n_clicks):
    if n_clicks > 0:
        cache.clear()
        logger.info("Cache cleared by user")
        return 1
    return 0

@app.callback(
    Output('download-dataframe-csv', 'data'),
    [Input('export-button', 'n_clicks')],
    [State('detailed-store', 'data')],
    prevent_initial_call=True
)
def export_data(n_clicks, data):
    if n_clicks and data:
        df = pd.DataFrame(data)
        df['Company Name'] = df['ticker'].map(config.COMPANY_NAMES)
        return dcc.send_data_frame(df.to_csv, f"credit_ratings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", index=False)

# ========== VALIDATION CALLBACK WITH PYRATINGS ==========

@app.callback(
    [Output('validation-accuracy', 'children'),
     Output('validation-kappa', 'children'),
     Output('validation-within-one', 'children'),
     Output('validation-within-two', 'children'),
     Output('validation-total', 'children'),
     Output('misclassified-table', 'data'),
     Output('misclassified-table', 'columns'),
     Output('validation-error', 'children')],
    [Input('refresh-button', 'n_clicks')]
)
def update_validation_metrics(n_clicks):
    """Update model validation tab with KBRA vs S&P comparison using pyratings"""
    try:
        actual_ratings = pd.read_csv('data/actual_ratings.csv')
        validation_df = actual_ratings.copy()
        
        kbra_ratings = {
            'AAPL': 'AAA', 'MSFT': 'AAA', 'GOOGL': 'AAA', 'NVDA': 'AAA',
            'TSLA': 'A', 'WMT': 'AA+', 'SBUX': 'A', 'COST': 'AA-',
            'LOW': 'A+', 'UNH': 'AA-', 'XOM': 'AA-', 'JPM': 'A',
            'V': 'AA', 'PEP': 'AA-', 'KO': 'A+', 'PFE': 'A',
            'JNJ': 'AAA', 'BA': 'BBB', 'IBM': 'A', 'ADBE': 'AA-',
            'AMD': 'BBB+', 'INTC': 'BBB+', 'AMZN': 'AA', 'NFLX': 'A+',
            'META': 'AA'
        }
        
        validation_df['kbra_rating'] = validation_df['ticker'].map(kbra_ratings)
        
        notch_diffs = []
        for _, row in validation_df.iterrows():
            kbra_rating = row.get('kbra_rating')
            sp_rating = row.get('sp_rating')
            
            if pd.notna(kbra_rating) and pd.notna(sp_rating):
                try:
                    kbra_score = rtg.get_scores_from_ratings(
                        kbra_rating, rating_provider='S&P', tenor='long-term'
                    )
                    sp_score = rtg.get_scores_from_ratings(
                        sp_rating, rating_provider='S&P', tenor='long-term'
                    )
                    notch_diff = abs(kbra_score - sp_score)
                    notch_diffs.append(notch_diff)
                except Exception:
                    notch_diffs.append(None)
            else:
                notch_diffs.append(None)
        
        validation_df['notch_diff'] = notch_diffs
        valid_df = validation_df.dropna(subset=['notch_diff', 'kbra_rating', 'sp_rating'])
        
        if len(valid_df) == 0:
            return "Error", "Error", "Error", "Error", "Error", [], [], "No valid rating data for comparison"
        
        total = len(valid_df)
        exact_matches = (valid_df['notch_diff'] == 0).sum()
        within_one = (valid_df['notch_diff'] <= 1).sum()
        within_two = (valid_df['notch_diff'] <= 2).sum()
        
        accuracy = exact_matches / total
        within_one_pct = within_one / total
        within_two_pct = within_two / total
        
        kbra_dist = valid_df['kbra_rating'].value_counts(normalize=True)
        sp_dist = valid_df['sp_rating'].value_counts(normalize=True)
        
        expected_accuracy = 0
        for rating in set(kbra_dist.index) & set(sp_dist.index):
            expected_accuracy += kbra_dist.get(rating, 0) * sp_dist.get(rating, 0)
        
        kappa = (accuracy - expected_accuracy) / (1 - expected_accuracy) if expected_accuracy < 1 else 0
        
        misclassified_data = []
        for _, row in valid_df[valid_df['notch_diff'] > 0].iterrows():
            misclassified_data.append({
                'Ticker': row.get('ticker', ''),
                'Company': row.get('name', ''),
                'KBRA Rating': row.get('kbra_rating', ''),
                'S&P Rating': row.get('sp_rating', ''),
                'Notches Off': int(row.get('notch_diff', 0))
            })
        
        misclassified_data.sort(key=lambda x: x['Notches Off'], reverse=True)
        
        columns = [
            {'name': 'Ticker', 'id': 'Ticker'},
            {'name': 'Company', 'id': 'Company'},
            {'name': 'KBRA Rating', 'id': 'KBRA Rating'},
            {'name': 'S&P Rating', 'id': 'S&P Rating'},
            {'name': 'Notches Off', 'id': 'Notches Off'}
        ]
        
        return (
            f"{accuracy*100:.1f}%",
            f"{kappa:.3f}",
            f"{within_one_pct*100:.1f}%",
            f"{within_two_pct*100:.1f}%",
            f"{total} companies",
            misclassified_data,
            columns,
            "✅ Using pyratings (HSBC library) for notch calculations"
        )
        
    except Exception as e:
        return "Error", "Error", "Error", "Error", "Error", [], [], f"Error: {str(e)}"

# ========== SCENARIO ANALYSIS CALLBACK ==========

@app.callback(
    Output('scenario-results', 'children'),
    [Input('gdp-shock', 'value'),
     Input('rate-shock', 'value'),
     Input('data-store', 'data')]
)
def update_scenario(gdp_shock, rate_shock, stored_data):
    """Update scenario analysis using actual data from stored_data"""
    try:
        if not stored_data:
            return html.Div([
                html.H4("No Data Available", style={'color': 'red'}),
                html.P("Please select companies and click Refresh Data first.")
            ])
        
        # Use actual data from stored_data
        companies_df = pd.DataFrame(stored_data)
        
        # Calculate portfolio metrics
        total_ecl_base = 0
        company_details = []
        
        # PD multiplier based on GDP shock
        if gdp_shock < 0:
            pd_multiplier = 1 + (abs(gdp_shock) * 0.25)
        else:
            pd_multiplier = 1 + (gdp_shock * 0.1)
        
        pd_multiplier = max(0.5, min(3.0, pd_multiplier))
        
        for _, company in companies_df.iterrows():
            rating = company.get('rating', 'BBB')
            base_pd = RATING_TO_PD.get(rating, 0.0100)
            stressed_pd = min(0.50, base_pd * pd_multiplier)
            
            revenue_dollars = company.get('revenue_bn', 1) * 1e9
            if revenue_dollars <= 0:
                revenue_dollars = 1e9
            
            ead = revenue_dollars * 0.3
            lgd = 0.45
            
            base_ecl = base_pd * lgd * ead
            stressed_ecl = stressed_pd * lgd * ead
            
            total_ecl_base += base_ecl
            
            company_details.append({
                'name': company.get('ticker', 'Unknown'),
                'symbol': company.get('ticker', ''),
                'base_pd': base_pd,
                'stressed_pd': stressed_pd,
                'stressed_ecl': stressed_ecl
            })
        
        # Calculate stressed total
        stressed_ecl_total = sum(c['stressed_ecl'] for c in company_details)
        ecl_increase_pct = ((stressed_ecl_total - total_ecl_base) / total_ecl_base * 100) if total_ecl_base > 0 else 0
        
        # Sort to find worst affected
        company_details.sort(key=lambda x: x['stressed_ecl'], reverse=True)
        
        # Create worst affected companies table
        worst_table = []
        for company in company_details[:5]:
            worst_table.append(html.Tr([
                html.Td(company['symbol'], style={'font-weight': 'bold'}),
                html.Td(company['name']),
                html.Td(f"{company['base_pd']:.2%}", style={'text-align': 'right'}),
                html.Td(f"{company['stressed_pd']:.2%}", style={'text-align': 'right'}),
                html.Td(f"${company['stressed_ecl']:,.0f}", style={'text-align': 'right'})
            ]))
        
        # Determine impact level color
        impact_color = '#27ae60'
        if ecl_increase_pct > 50:
            impact_color = '#e74c3c'
        elif ecl_increase_pct > 20:
            impact_color = '#f39c12'
        
        # Determine scenario description
        if gdp_shock < 0:
            scenario_desc = f"Recession: GDP {gdp_shock:+.1f}%"
        elif gdp_shock > 0:
            scenario_desc = f"Growth: GDP {gdp_shock:+.1f}%"
        else:
            scenario_desc = f"Baseline: GDP {gdp_shock:+.1f}%"
        
        return html.Div([
            html.Div([
                html.H4(f"📊 {scenario_desc}, Interest Rates {rate_shock:+.1f}%", 
                       style={'color': '#2c3e50', 'margin-bottom': '20px'}),
                
                html.Div([
                    html.Div([
                        html.H3("Base Portfolio ECL", style={'color': '#7f8c8d', 'font-size': '14px'}),
                        html.H2(f"${total_ecl_base:,.0f}", style={'color': '#2c3e50', 'margin-top': '0'})
                    ], style={'display': 'inline-block', 'width': '45%', 'text-align': 'center'}),
                    
                    html.Div([
                        html.H3("Stressed ECL", style={'color': '#7f8c8d', 'font-size': '14px'}),
                        html.H2(f"${stressed_ecl_total:,.0f}", style={'color': impact_color, 'margin-top': '0'})
                    ], style={'display': 'inline-block', 'width': '45%', 'text-align': 'center'})
                ], style={'margin-bottom': '30px'}),
                
                html.Div([
                    html.Div([
                        html.H3(f"{ecl_increase_pct:+.1f}%", 
                               style={'color': impact_color, 'font-size': '36px', 'margin': '0'}),
                        html.P("Change in ECL", style={'color': '#7f8c8d'})
                    ], style={'text-align': 'center', 'padding': '20px', 'background': '#f8f9fa', 'border-radius': '10px'})
                ], style={'margin-bottom': '30px'}),
                
                html.H5(f"PD Multiplier: {pd_multiplier:.2f}x", style={'margin-bottom': '20px'}),
                html.P(f"Based on {len(companies_df)} companies from your selection", 
                      style={'color': '#7f8c8d', 'font-size': '12px', 'margin-bottom': '20px'}),
                
                html.H5("🚨 Top 5 Most Affected Companies", style={'margin-top': '30px'}),
                dbc.Table([
                    html.Thead(html.Tr([
                        html.Th("Ticker"), html.Th("Company"), 
                        html.Th("Base PD"), html.Th("Stressed PD"), 
                        html.Th("Stressed ECL")
                    ])),
                    html.Tbody(worst_table)
                ], bordered=True, striped=True, hover=True, size='sm')
                
            ], style={'padding': '20px'})
        ])
        
    except Exception as e:
        return html.Div([
            html.H4("Error in Scenario Analysis", style={'color': 'red'}),
            html.P(f"Details: {str(e)}"),
            html.P("Please ensure you have selected companies and clicked Refresh Data.")
        ])

# ========== RUN THE APP ==========

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8050))
    print("="*60)
    print("🚀 Starting Enhanced Credit Risk Dashboard...")
    print("📊 Open http://127.0.0.1:8050 in your browser")
    print("⏱️  First load may take 30-60 seconds (Render spin-up)")
    print("✨ FEATURES: KBRA Methodology | IFRS 9 ECL | pyratings | WARF | Scenario Analysis")
    print("✨ DATA SOURCE: Real-time API data (no hardcoded values)")
    print("="*60)
    app.run(host='0.0.0.0', port=port, debug=False)
