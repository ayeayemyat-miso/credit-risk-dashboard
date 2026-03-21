# app/dashboard.py
"""
Real-Time Credit Risk Dashboard
Monitors credit ratings for companies in real-time with detailed breakdowns
Deployment-ready for Render.com
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dash
from dash import dcc, html, Input, Output, State, dash_table, no_update
import plotly.graph_objs as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime
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

# Initialize the Dash app
app = dash.Dash(__name__)
server = app.server  # <--- IMPORTANT: Required for Render deployment
app.title = "KBRA Credit Risk Dashboard"

# Define layout
app.layout = html.Div([
    # Header
    html.Div([
        html.H1("📊 KBRA Credit Risk Dashboard", 
                style={'text-align': 'center', 'color': '#2c3e50', 'margin-top': '20px',
                       'font-family': 'Arial, sans-serif', 'font-size': '36px'}),
        html.P("Real-time credit ratings using KBRA methodology",
               style={'text-align': 'center', 'color': '#7f8c8d', 'font-size': '16px',
                      'margin-bottom': '30px'})
    ]),
    
    # Controls
    html.Div([
        html.Div([
            html.H3("Select Companies to Monitor", 
                    style={'text-align': 'center', 'color': '#34495e', 'margin-bottom': '15px'}),
            dcc.Dropdown(
                id='company-dropdown',
                options=[{'label': ticker, 'value': ticker} for ticker in config.DEFAULT_TICKERS],
                value=['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA'],
                multi=True,
                style={'width': '80%', 'margin': 'auto', 'font-family': 'Arial, sans-serif',
                       'background-color': 'white'}
            ),
        ], style={'padding': '20px'}),
        
        html.Div([
            html.Button('🔄 Refresh Data', id='refresh-button', n_clicks=0,
                       style={'background-color': '#3498db', 'color': 'white', 
                              'padding': '12px 24px', 'border': 'none', 'border-radius': '5px',
                              'cursor': 'pointer', 'font-size': '16px', 'margin': '5px',
                              'font-weight': 'bold'}),
            
            html.Button('🗑️ Clear Cache', id='clear-cache-button', n_clicks=0,
                       style={'background-color': '#e74c3c', 'color': 'white', 
                              'padding': '12px 24px', 'border': 'none', 'border-radius': '5px',
                              'cursor': 'pointer', 'font-size': '16px', 'margin': '5px',
                              'font-weight': 'bold'}),
            
            html.Button('📥 Export Data', id='export-button', n_clicks=0,
                       style={'background-color': '#2ecc71', 'color': 'white', 
                              'padding': '12px 24px', 'border': 'none', 'border-radius': '5px',
                              'cursor': 'pointer', 'font-size': '16px', 'margin': '5px',
                              'font-weight': 'bold'}),
        ], style={'text-align': 'center', 'margin': '20px'}),
        
        html.Div(id='last-updated', style={'text-align': 'center', 'color': '#7f8c8d', 
                                           'font-family': 'Arial, sans-serif', 'margin': '10px',
                                           'font-size': '14px'}),
        
        html.Div(id='data-status', style={'text-align': 'center', 'color': '#27ae60', 
                                          'font-family': 'Arial, sans-serif', 'margin': '10px',
                                          'font-size': '14px', 'font-weight': 'bold'}),
    ], style={'background-color': '#f8f9fa', 'border-radius': '10px', 'margin': '20px',
              'padding': '20px', 'box-shadow': '0 2px 4px rgba(0,0,0,0.1)'}),
    
    # Rating cards
    html.Div(id='rating-cards', style={'display': 'flex', 'flex-wrap': 'wrap', 
                                       'justify-content': 'center', 'margin': '20px'}),
    
    # Tabs for different views
    html.Div([
        dcc.Tabs(id='tabs', value='risk-scores', children=[
            dcc.Tab(label='📊 Risk Scores', value='risk-scores', 
                   style={'font-weight': 'bold'}, selected_style={'font-weight': 'bold', 'border-top': '3px solid #3498db'}),
            dcc.Tab(label='📈 Financial Metrics', value='financial-metrics',
                   style={'font-weight': 'bold'}, selected_style={'font-weight': 'bold', 'border-top': '3px solid #3498db'}),
            dcc.Tab(label='🎯 Component Breakdown', value='component-breakdown',
                   style={'font-weight': 'bold'}, selected_style={'font-weight': 'bold', 'border-top': '3px solid #3498db'}),
            dcc.Tab(label='📋 Raw Data', value='raw-data',
                   style={'font-weight': 'bold'}, selected_style={'font-weight': 'bold', 'border-top': '3px solid #3498db'}),
        ]),
        html.Div(id='tab-content', style={'padding': '20px', 'background-color': 'white',
                                          'border-radius': '0 0 10px 10px', 'box-shadow': '0 2px 4px rgba(0,0,0,0.1)'}),
    ], style={'width': '95%', 'margin': 'auto', 'margin-top': '20px'}),
    
    # Hidden div for storing detailed data
    html.Div(id='detailed-data-store', style={'display': 'none'}),
    
    # Main data store
    dcc.Store(id='data-store'),
    dcc.Store(id='detailed-store'),
    dcc.Download(id='download-dataframe-csv'),
    
    # Auto-refresh every 60 minutes
    dcc.Interval(
        id='interval-component',
        interval=60*60*1000,
        n_intervals=0
    ),
])

def create_rating_card(ticker, rating, business_score, financial_score, data_year, components):
    """Create a styled card for a company's rating with hover details."""
    
    # Color based on rating
    if rating in ['AAA', 'AA']:
        color = '#2ecc71'  # Green
        bg_color = '#d4edda'
        border_color = '#c3e6cb'
    elif rating in ['A', 'BBB']:
        color = '#f39c12'  # Orange
        bg_color = '#fff3cd'
        border_color = '#ffeeba'
    else:
        color = '#e74c3c'  # Red
        bg_color = '#f8d7da'
        border_color = '#f5c6cb'
    
    # Create tooltip text
    tooltip = f"""
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
            html.H4(ticker, style={'margin': '5px', 'color': '#2c3e50', 'font-size': '20px'}),
            html.H2(rating, style={'color': color, 'margin': '5px', 'font-size': '36px', 
                                   'font-weight': 'bold'}),
            html.Div([
                html.P(f"Business: {business_score:.2f}", style={'margin': '2px', 'font-size': '14px'}),
                html.P(f"Financial: {financial_score:.2f}", style={'margin': '2px', 'font-size': '14px'}),
                html.P(f"Data: {data_year}", style={'margin': '2px', 'font-size': '12px', 
                                                    'color': '#7f8c8d'}),
            ], style={'margin-top': '10px'}),
        ], style={
            'border': f'2px solid {border_color}',
            'border-radius': '10px',
            'padding': '15px',
            'width': '220px',
            'text-align': 'center',
            'background-color': bg_color,
            'box-shadow': '0 4px 6px rgba(0,0,0,0.1)',
            'cursor': 'help'
        }, title=tooltip),
    ], style={'margin': '10px'})

# Callback to update data
@app.callback(
    [Output('data-store', 'data'),
     Output('detailed-store', 'data'),
     Output('data-status', 'children')],
    [Input('refresh-button', 'n_clicks'),
     Input('interval-component', 'n_intervals'),
     Input('clear-cache-button', 'n_clicks')],
    [Input('company-dropdown', 'value')]
)
def fetch_and_store_data(refresh_clicks, interval_clicks, cache_clicks, selected_tickers):
    """Fetch data and store in dcc.Store."""
    
    if not selected_tickers:
        return {}, {}, "Please select at least one company"
    
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
    
    for ticker in selected_tickers:
        try:
            # Fetch data
            data = DataFetcher.fetch_company_data(ticker)
            if not data:
                failed.append(ticker)
                continue
            
            # Calculate ratios
            ratios = RatioCalculator.calculate_all(data)
            
            # Assess risks
            business_assessment = BusinessRiskAssessor.assess_all(data)
            financial_assessment = FinancialRiskAssessor.assess_all(data, ratios)
            
            # Calculate rating
            business_score = business_assessment.calculate_weighted_score()
            business_category = RatingCalculator._business_score_to_category(business_score)
            financial_score = financial_assessment.calculate_weighted_score()
            rating = RatingCalculator._determine_rating_from_table(business_category, financial_score)
            
            # Store basic results
            results.append({
                'ticker': ticker,
                'rating': rating,
                'business_score': business_score,
                'financial_score': financial_score,
                'data_year': str(data.get('data_year', 'N/A')),
                'revenue': data.get('revenue'),
                'ebitda': data.get('ebitda'),
                'total_debt': data.get('total_debt'),
                'cash': data.get('cash')
            })
            
            # Store detailed results for tooltips and breakdown
            detailed_results.append({
                'ticker': ticker,
                'rating': rating,
                'business_score': business_score,
                'financial_score': financial_score,
                'industry_risk': business_assessment.industry_risk.value,
                'competitive_risk': business_assessment.competitive_risk.value,
                'liquidity_risk': business_assessment.liquidity_risk.value,
                'size_score': financial_assessment.size_score,
                'profitability_score': financial_assessment.profitability_score,
                'cash_flow_score': financial_assessment.cash_flow_score,
                'leverage_score': financial_assessment.leverage_score,
                'coverage_score': financial_assessment.coverage_score,
                'debt_to_ebitda': round(ratios.get('debt_to_ebitda', 0), 2) if pd.notna(ratios.get('debt_to_ebitda')) else 'N/A',
                'ebit_margin': round(ratios.get('ebit_margin', 0) * 100, 1) if pd.notna(ratios.get('ebit_margin')) else 'N/A',
                'fcf_to_debt': round(ratios.get('fcf_to_debt', 0), 3) if pd.notna(ratios.get('fcf_to_debt')) else 'N/A',
                'roa': round(ratios.get('roa', 0) * 100, 1) if pd.notna(ratios.get('roa')) else 'N/A'
            })
            
        except Exception as e:
            logger.error(f"Error processing {ticker}: {e}")
            failed.append(ticker)
    
    status = f"✅ Loaded: {len(results)} companies"
    if failed:
        status += f" | ❌ Failed: {', '.join(failed)}"
    
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
        return [], html.Div("No data available. Please refresh.", style={'text-align': 'center', 'padding': '50px'}), ""
    
    # Create rating cards with detailed tooltips
    cards = []
    for company in stored_data:
        # Find matching detailed data
        detail = next((d for d in detailed_data if d['ticker'] == company['ticker']), {})
        cards.append(create_rating_card(
            company['ticker'],
            company['rating'],
            company['business_score'],
            company['financial_score'],
            company['data_year'],
            detail
        ))
    
    # Create tab content
    if active_tab == 'risk-scores':
        # Bar chart of risk scores
        fig = go.Figure(data=[
            go.Bar(name='Business Score', 
                   x=[c['ticker'] for c in stored_data], 
                   y=[c['business_score'] for c in stored_data],
                   marker_color='#3498db',
                   text=[f"{c['business_score']:.2f}" for c in stored_data],
                   textposition='outside',
                   hovertemplate='<b>%{x}</b><br>Business Score: %{y:.2f}<extra></extra>'),
            go.Bar(name='Financial Score', 
                   x=[c['ticker'] for c in stored_data], 
                   y=[c['financial_score'] for c in stored_data],
                   marker_color='#e74c3c',
                   text=[f"{c['financial_score']:.2f}" for c in stored_data],
                   textposition='outside',
                   hovertemplate='<b>%{x}</b><br>Financial Score: %{y:.2f}<extra></extra>')
        ])
        
        fig.update_layout(
            title='Risk Scores by Company (Lower is Better)',
            xaxis_title='Company',
            yaxis_title='Score',
            barmode='group',
            template='plotly_white',
            hovermode='x unified',
            yaxis=dict(range=[0, 20]),
            showlegend=True,
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
        )
        
        content = dcc.Graph(figure=fig, style={'height': '500px'})
        
    elif active_tab == 'financial-metrics':
        # Create metrics comparison
        fig = go.Figure()
        
        metrics = [
            ('EBIT Margin %', 'ebit_margin', '#2ecc71'),
            ('Debt/EBITDA', 'debt_to_ebitda', '#e74c3c'),
            ('FCF/Debt', 'fcf_to_debt', '#3498db'),
            ('ROA %', 'roa', '#f39c12')
        ]
        
        for metric_name, metric_key, color in metrics:
            values = []
            valid_tickers = []
            for d in detailed_data:
                val = d.get(metric_key, 'N/A')
                if val != 'N/A':
                    values.append(float(val))
                    valid_tickers.append(d['ticker'])
            
            if values:
                fig.add_trace(go.Bar(
                    name=metric_name,
                    x=valid_tickers,
                    y=values,
                    marker_color=color,
                    text=[f"{v:.1f}" for v in values],
                    textposition='outside'
                ))
        
        fig.update_layout(
            title='Financial Metrics Comparison',
            xaxis_title='Company',
            yaxis_title='Value',
            barmode='group',
            template='plotly_white',
            height=500,
            showlegend=True,
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
        )
        
        content = dcc.Graph(figure=fig, style={'height': '500px'})
        
    elif active_tab == 'component-breakdown':
        # Radar charts for each company
        if not detailed_data:
            content = html.Div("No detailed data available")
        else:
            # Create subplot for radar charts
            n_companies = len(detailed_data)
            cols = min(3, n_companies)
            rows = (n_companies + cols - 1) // cols
            
            fig = make_subplots(
                rows=rows, cols=cols,
                specs=[[{'type': 'polar'}]*cols for _ in range(rows)],
                subplot_titles=[d['ticker'] for d in detailed_data]
            )
            
            for idx, d in enumerate(detailed_data):
                row = idx // cols + 1
                col = idx % cols + 1
                
                categories = ['Size', 'Profitability', 'Cash Flow', 'Leverage', 'Coverage']
                values = [
                    d.get('size_score', 0),
                    d.get('profitability_score', 0),
                    d.get('cash_flow_score', 0),
                    d.get('leverage_score', 0),
                    d.get('coverage_score', 0)
                ]
                
                # Close the loop
                categories.append(categories[0])
                values.append(values[0])
                
                fig.add_trace(go.Scatterpolar(
                    r=values,
                    theta=categories,
                    fill='toself',
                    name=d['ticker'],
                    line_color=['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6'][idx % 5]
                ), row=row, col=col)
            
            fig.update_layout(
                title='Financial Risk Component Breakdown',
                height=400 * rows,
                showlegend=False
            )
            
            content = dcc.Graph(figure=fig)
        
    elif active_tab == 'raw-data':
        # Create data table
        df = pd.DataFrame(detailed_data)
        if not df.empty:
            # Select and rename columns for display
            display_df = df[[
                'ticker', 'rating', 'business_score', 'financial_score',
                'industry_risk', 'competitive_risk', 'liquidity_risk',
                'debt_to_ebitda', 'ebit_margin', 'fcf_to_debt', 'roa'
            ]].copy()
            
            display_df.columns = [
                'Ticker', 'Rating', 'Business', 'Financial',
                'Industry Risk', 'Competitive', 'Liquidity',
                'Debt/EBITDA', 'EBIT Margin %', 'FCF/Debt', 'ROA %'
            ]
            
            content = html.Div([
                html.H4("Detailed Company Data", style={'margin-bottom': '20px'}),
                dash_table.DataTable(
                    data=display_df.to_dict('records'),
                    columns=[{'name': col, 'id': col} for col in display_df.columns],
                    style_table={'overflowX': 'auto'},
                    style_cell={
                        'textAlign': 'center',
                        'padding': '10px',
                        'font-family': 'Arial, sans-serif'
                    },
                    style_header={
                        'backgroundColor': '#3498db',
                        'color': 'white',
                        'fontWeight': 'bold'
                    },
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': '#f8f9fa'
                        }
                    ]
                )
            ])
        else:
            content = html.Div("No data available")
    
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
    """Clear cache and trigger refresh."""
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
    """Export data to CSV."""
    if n_clicks and data:
        df = pd.DataFrame(data)
        return dcc.send_data_frame(df.to_csv, f"credit_ratings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", index=False)

# Run the app - UPDATED FOR RENDER DEPLOYMENT
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8050))  # Get PORT from Render, default to 8050 locally
    print("="*60)
    print("🚀 Starting KBRA Credit Risk Dashboard...")
    print(f"📊 Open http://127.0.0.1:{port} in your browser")
    print("⏱️  First load may be slow (fetching data from FMP)...")
    print("="*60)
    app.run(host='0.0.0.0', port=port, debug=False)  # debug=False for production