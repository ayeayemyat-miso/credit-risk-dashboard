# app/dashboard.py (Updated - With Render Free Tier Fixes)

import sys
import os
import time
import functools
from threading import Thread
import requests

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dash
from dash import dcc, html, Input, Output, State, dash_table
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

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ========== RENDER FREE TIER FIXES ==========

def start_keep_alive():
    """Start background thread to keep Render instance alive"""
    def keep_alive_loop():
        # Get your Render URL - you can set this as an environment variable
        render_url = os.environ.get("RENDER_EXTERNAL_URL", "")
        if not render_url:
            # Fallback - you'll need to set this
            logger.warning("RENDER_EXTERNAL_URL not set. Keep-alive disabled.")
            return
        
        while True:
            try:
                # Ping the app every 4 minutes
                response = requests.get(render_url, timeout=10)
                logger.debug(f"Keep-alive ping sent - Status: {response.status_code}")
            except Exception as e:
                logger.debug(f"Keep-alive error: {e}")
            time.sleep(240)  # 4 minutes (Render spins down after 15 mins of inactivity)
    
    # Only start if we have a URL
    if os.environ.get("RENDER_EXTERNAL_URL"):
        thread = Thread(target=keep_alive_loop, daemon=True)
        thread.start()
        logger.info("✅ Keep-alive thread started for Render free tier")
    else:
        logger.info("ℹ️ Keep-alive not started (not running on Render or URL not set)")

# Start keep-alive automatically when running on Render
if os.environ.get("RENDER"):
    start_keep_alive()

# ========== END RENDER FIXES ==========

# Initialize the Dash app
app = dash.Dash(__name__)
server = app.server
app.title = "Credit Risk Dashboard"

# Create all company options for dropdown (with names)
ALL_COMPANY_OPTIONS = [
    {'label': f"{ticker} - {config.COMPANY_NAMES.get(ticker, ticker)}", 'value': ticker}
    for ticker in config.DEFAULT_TICKERS
]

# Default watchlist (first 5 companies)
DEFAULT_WATCHLIST = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA']

# Define layout
app.layout = html.Div([
    # Header
    html.Div([
        html.H1("📊 Credit Risk Dashboard", 
                style={'text-align': 'center', 'color': '#2c3e50', 'margin-top': '20px',
                       'font-family': 'Arial, sans-serif', 'font-size': '36px'}),
        html.P("Real-time credit ratings using KBRA methodology",
               style={'text-align': 'center', 'color': '#7f8c8d', 'font-size': '16px',
                      'margin-bottom': '30px'})
    ]),
    
    # Controls Section
    html.Div([
        # Company Selector
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
        
        # Watchlist Buttons
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
        
        # Watchlist Display
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
            dcc.Tab(label='📈 KBRA Ratios', value='kbra-ratios',
                   style={'font-weight': 'bold'}, selected_style={'font-weight': 'bold', 'border-top': '3px solid #3498db'}),
            dcc.Tab(label='🎯 Component Breakdown', value='component-breakdown',
                   style={'font-weight': 'bold'}, selected_style={'font-weight': 'bold', 'border-top': '3px solid #3498db'}),
            dcc.Tab(label='📊 vs Actual Ratings', value='comparison',
                   style={'font-weight': 'bold'}, selected_style={'font-weight': 'bold', 'border-top': '3px solid #3498db'}),
            dcc.Tab(label='⭐ My Watchlist Analysis', value='watchlist-analysis',
                   style={'font-weight': 'bold'}, selected_style={'font-weight': 'bold', 'border-top': '3px solid #3498db'}),
            dcc.Tab(label='📋 Raw Data', value='raw-data',
                   style={'font-weight': 'bold'}, selected_style={'font-weight': 'bold', 'border-top': '3px solid #3498db'}),
        ]),
        html.Div(id='tab-content', style={'padding': '20px', 'background-color': 'white',
                                          'border-radius': '0 0 10px 10px', 'box-shadow': '0 2px 4px rgba(0,0,0,0.1)'}),
    ], style={'width': '95%', 'margin': 'auto', 'margin-top': '20px'}),
    
    # Hidden div for storing data
    dcc.Store(id='data-store'),
    dcc.Store(id='detailed-store'),
    dcc.Store(id='user-watchlist', storage_type='local', data=DEFAULT_WATCHLIST),
    dcc.Download(id='download-dataframe-csv'),
    
    # Auto-refresh every 60 minutes
    dcc.Interval(
        id='interval-component',
        interval=60*60*1000,
        n_intervals=0
    ),
])

def create_watchlist_chip(ticker):
    """Create a clickable watchlist chip"""
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
    """Create a styled card for a company's rating with hover details."""
    
    # Color based on rating
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
    
    tooltip = f"""
    {company_name}
    Data Period: {data_year}
    Industry Risk: {components.get('industry_risk', 'N/A')}
    Competitive Risk: {components.get('competitive_risk', 'N/A')}
    Liquidity Risk: {components.get('liquidity_risk', 'N/A')}
    Size Score: {components.get('size_score', 'N/A')}
    Profitability: {components.get('profitability_score', 'N/A')}
    Cash Flow: {components.get('cash_flow_score', 'N/A')}
    Leverage: {components.get('leverage_score', 'N/A')}
    Coverage: {components.get('coverage_score', 'N/A')}
    """
    
    return html.Div([
        html.Div([
            html.H4(company_name, style={'margin': '5px', 'color': '#2c3e50', 'font-size': '14px'}),
            html.H2(rating, style={'color': color, 'margin': '5px', 'font-size': '32px', 
                                   'font-weight': 'bold'}),
            html.Div([
                html.P(f"Business: {business_score:.2f}", style={'margin': '2px', 'font-size': '12px'}),
                html.P(f"Financial: {financial_score:.2f}", style={'margin': '2px', 'font-size': '12px'}),
                html.P(f"Data: {data_year}", style={'margin': '2px', 'font-size': '10px', 
                                                    'color': '#7f8c8d'}),
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
        }, title=tooltip),
    ], style={'margin': '8px'})

# Callback to update watchlist display
@app.callback(
    Output('watchlist-display', 'children'),
    [Input('user-watchlist', 'data')]
)
def update_watchlist_display(watchlist):
    """Display watchlist chips"""
    if not watchlist:
        return html.P("Your watchlist is empty. Use the dropdown above to add companies.", 
                      style={'color': '#7f8c8d'})
    
    return [create_watchlist_chip(ticker) for ticker in watchlist]

# Callback to add to watchlist
@app.callback(
    Output('user-watchlist', 'data', allow_duplicate=True),
    [Input('add-to-watchlist', 'n_clicks'),
     Input('remove-from-watchlist', 'n_clicks')],
    [State('company-selector', 'value'),
     State('user-watchlist', 'data')],
    prevent_initial_call=True
)
def modify_watchlist(add_clicks, remove_clicks, selected_companies, current_watchlist):
    """Add or remove companies from watchlist"""
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

# Callback to handle watchlist chip clicks
@app.callback(
    Output('company-selector', 'value'),
    [Input({'type': 'watchlist-chip', 'index': dash.ALL}, 'n_clicks')],
    [State('company-selector', 'value')],
    prevent_initial_call=True
)
def select_from_watchlist(n_clicks_list, current_selection):
    """When a watchlist chip is clicked, add it to selection"""
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

# Callback to update data with retry logic for Render free tier
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
    """Fetch data and store in dcc.Store with retry logic for slow startups."""
    
    if not selected_tickers:
        return {}, {}, "No companies selected. Use dropdown to add companies."
    
    # Add initial delay to allow Render to wake up (only for first request)
    if not hasattr(fetch_and_store_data, '_initialized'):
        fetch_and_store_data._initialized = True
        # Add 5 second delay for first request to handle spin-up
        logger.info("First request detected - adding delay for Render spin-up")
        time.sleep(5)
    
    # Clear cache if requested
    ctx = dash.callback_context
    if ctx.triggered:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if button_id == 'clear-cache-button' and cache_clicks > 0:
            cache.clear()
            logger.info("Cache cleared by user")
    
    results = []
    detailed_results = []
    failed = []
    
    # Function to fetch with retry for each ticker
    def fetch_with_retry(ticker, max_retries=2):
        for attempt in range(max_retries):
            try:
                data = DataFetcher.fetch_company_data(ticker)
                if data:
                    return data
                else:
                    logger.warning(f"{ticker}: Attempt {attempt + 1} failed, retrying...")
                    if attempt < max_retries - 1:
                        time.sleep(3)  # Wait 3 seconds before retry
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
            
            # Calculate revenue in billions for size metric
            revenue_bn = data.get('revenue', 0) / 1e9 if data.get('revenue') else 0
            data_year = str(data.get('data_year', 'N/A'))
            
            results.append({
                'ticker': ticker,
                'rating': rating,
                'business_score': business_score,
                'financial_score': financial_score,
                'data_year': data_year,
                'revenue_bn': revenue_bn,
                'ebit_margin': ratios.get('ebit_margin', 0),
                'fcf_to_debt': ratios.get('fcf_to_debt', 0),
                'debt_to_ebitda': ratios.get('debt_to_ebitda', 0),
                'ebit_interest': ratios.get('ebit_interest', 0),
                'roa': ratios.get('roa', 0),
                'debt_to_capital': ratios.get('debt_to_capital', 0)
            })
            
            detailed_results.append({
                'ticker': ticker,
                'rating': rating,
                'business_score': business_score,
                'financial_score': financial_score,
                'data_year': data_year,
                'industry_risk': business_assessment.industry_risk.value,
                'competitive_risk': business_assessment.competitive_risk.value,
                'liquidity_risk': business_assessment.liquidity_risk.value,
                'size_score': financial_assessment.size_score,
                'profitability_score': financial_assessment.profitability_score,
                'cash_flow_score': financial_assessment.cash_flow_score,
                'leverage_score': financial_assessment.leverage_score,
                'coverage_score': financial_assessment.coverage_score,
                'revenue_bn': revenue_bn,
                'ebit_margin': round(ratios.get('ebit_margin', 0) * 100, 1) if pd.notna(ratios.get('ebit_margin')) else 'N/A',
                'fcf_to_debt': round(ratios.get('fcf_to_debt', 0), 3) if pd.notna(ratios.get('fcf_to_debt')) else 'N/A',
                'debt_to_ebitda': round(ratios.get('debt_to_ebitda', 0), 2) if pd.notna(ratios.get('debt_to_ebitda')) else 'N/A',
                'ebit_interest': round(ratios.get('ebit_interest', 0), 1) if pd.notna(ratios.get('ebit_interest')) else 'N/A',
                'roa': round(ratios.get('roa', 0) * 100, 1) if pd.notna(ratios.get('roa')) else 'N/A',
                'debt_to_capital': round(ratios.get('debt_to_capital', 0) * 100, 1) if pd.notna(ratios.get('debt_to_capital')) else 'N/A'
            })
            
        except Exception as e:
            logger.error(f"Error processing {ticker}: {e}")
            failed.append(ticker)
    
    status = f"✅ Loaded: {len(results)} companies"
    if failed:
        status += f" | ❌ Failed: {', '.join(failed)}"
    
    # Add note about loading time
    if len(results) < len(selected_tickers):
        status += " | ⏱️ First load may take 30-60 seconds (Render wake-up)"
    
    return results, detailed_results, status

# Callback to update display
@app.callback(
    [Output('rating-cards', 'children'),
     Output('tab-content', 'children'),
     Output('last-updated', 'children')],
    [Input('data-store', 'data'),
     Input('detailed-store', 'data'),
     Input('tabs', 'value')]
)
def update_display(stored_data, detailed_data, active_tab):
    """Update the dashboard display with stored data."""
    
    if not stored_data:
        return [], html.Div("No data available. Please select companies to analyze.", 
                           style={'text-align': 'center', 'padding': '50px'}), ""
    
    # Create rating cards (already includes data_year)
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
    
    # Tab content
    if active_tab == 'risk-scores':
        fig = go.Figure(data=[
            go.Bar(name='Business Score', x=[c['ticker'] for c in stored_data], 
                   y=[c['business_score'] for c in stored_data], marker_color='#3498db'),
            go.Bar(name='Financial Score', x=[c['ticker'] for c in stored_data], 
                   y=[c['financial_score'] for c in stored_data], marker_color='#e74c3c')
        ])
        # Add data period to subtitle
        data_periods = ', '.join(set([c['data_year'] for c in stored_data]))
        fig.update_layout(title=f'Risk Scores by Company (Data Period: {data_periods})', 
                         xaxis_title='Company', yaxis_title='Score', barmode='group')
        content = dcc.Graph(figure=fig, style={'height': '500px'})
        
    elif active_tab == 'kbra-ratios':
        # Show all 5 KBRA financial ratios with data period in subtitle
        fig = make_subplots(rows=2, cols=3, subplot_titles=[
            'Revenue (Size)', 'EBIT Margin %', 'FCF/Debt',
            'Debt/EBITDA', 'EBIT/Interest', 'ROA %'
        ])
        
        tickers = [c['ticker'] for c in stored_data]
        data_periods = ', '.join(set([c['data_year'] for c in stored_data]))
        
        # Revenue
        fig.add_trace(go.Bar(x=tickers, y=[c['revenue_bn'] for c in stored_data], 
                            name='Revenue ($B)', marker_color='#3498db'), row=1, col=1)
        
        # EBIT Margin
        fig.add_trace(go.Bar(x=tickers, y=[c['ebit_margin']*100 for c in stored_data], 
                            name='EBIT Margin %', marker_color='#2ecc71'), row=1, col=2)
        
        # FCF/Debt
        fig.add_trace(go.Bar(x=tickers, y=[c['fcf_to_debt'] for c in stored_data], 
                            name='FCF/Debt', marker_color='#f39c12'), row=1, col=3)
        
        # Debt/EBITDA
        fig.add_trace(go.Bar(x=tickers, y=[c['debt_to_ebitda'] for c in stored_data], 
                            name='Debt/EBITDA', marker_color='#e74c3c'), row=2, col=1)
        
        # EBIT/Interest
        fig.add_trace(go.Bar(x=tickers, y=[c['ebit_interest'] for c in stored_data], 
                            name='EBIT/Interest', marker_color='#9b59b6'), row=2, col=2)
        
        # ROA
        fig.add_trace(go.Bar(x=tickers, y=[c['roa']*100 for c in stored_data], 
                            name='ROA %', marker_color='#1abc9c'), row=2, col=3)
        
        fig.update_layout(title=f'KBRA Financial Ratios (Data Period: {data_periods})', 
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
            comparison_data = []
            matches = 0
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
                    is_match = your_rating[:2] in actual_rating
                    if is_match:
                        matches += 1
                    comparison_data.append({
                        'Ticker': ticker, 'Company': company_name,
                        'Your Rating': your_rating, 'S&P Rating': actual_rating,
                        'Data Period': data_year, 'Match': '✓' if is_match else '✗'
                    })
            accuracy = round((matches / total) * 100, 1) if total > 0 else 0
            content = html.Div([
                html.Div([
                    html.H4("Model Accuracy vs S&P Ratings", style={'text-align': 'center'}),
                    html.Div([
                        html.H2(f"{accuracy}%", style={'text-align': 'center', 'color': '#2ecc71', 'font-size': '48px'}),
                        html.P(f"{matches} out of {total} companies match S&P ratings",
                              style={'text-align': 'center'})
                    ], style={'background-color': '#f8f9fa', 'padding': '20px', 'border-radius': '10px'})
                ]),
                dash_table.DataTable(data=comparison_data, columns=[
                    {'name': 'Ticker', 'id': 'Ticker'},
                    {'name': 'Company', 'id': 'Company'},
                    {'name': 'Your Rating', 'id': 'Your Rating'},
                    {'name': 'S&P Rating', 'id': 'S&P Rating'},
                    {'name': 'Data Period', 'id': 'Data Period'},
                    {'name': 'Match', 'id': 'Match'}
                ], style_cell={'textAlign': 'center'}, style_header={'backgroundColor': '#2c3e50', 'color': 'white'})
            ])
        except Exception as e:
            content = html.Div("Comparison data not available")
            
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
            # Reorder columns to put Company Name next to Ticker
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
    else:
        content = html.Div()
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    last_updated = f"Last updated: {timestamp}"
    
    return cards, content, last_updated

# Callback to clear cache
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

# Callback to export data
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

# Run the app
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8050))
    print("="*60)
    print("🚀 Starting Credit Risk Dashboard...")
    print("📊 Open http://127.0.0.1:8050 in your browser")
    print("⏱️  First load may take 30-60 seconds (Render spin-up)")
    print("="*60)
    app.run(host='0.0.0.0', port=port, debug=False)
