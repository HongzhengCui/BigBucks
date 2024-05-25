import sqlite3
import pandas as pd
import plotly.graph_objects as go
import json
from plotly.utils import PlotlyJSONEncoder
import numpy as np
from scipy.stats import linregress

def safe_isnan(value):
    """
    Safety check if value is NaN. Only floating point numbers are checked.
    """
    return isinstance(value, float) and np.isnan(value)

def convert_numpy(obj):
    """
    Safety check if value is NaN. Only floating point numbers are checked.
    """
    if isinstance(obj, np.ndarray):
        return [None if safe_isnan(x) else x for x in obj]
    elif isinstance(obj, dict):
        return {k: convert_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy(v) for v in obj]
    elif isinstance(obj, float):
        return None if safe_isnan(obj) else obj
    else:
        return obj

def plot_returns(db_path, symbol):
    with sqlite3.connect(db_path) as conn:
        query = f"SELECT date, close, simple_return, log_return, cumulative_return FROM stock_history WHERE symbol = '{symbol}' ORDER BY date"
        df = pd.read_sql_query(query, conn)

    df['date'] = pd.to_datetime(df['date'])
    df['simple_return_yesterday'] = df['simple_return'].shift(1)

    # Create simple and logarithmic return charts
    fig_returns = go.Figure()
    fig_returns.add_trace(go.Scatter(x=df['date'], y=df['simple_return'], mode='lines', name='Simple Return', line=dict(color='blue')))
    fig_returns.add_trace(go.Scatter(x=df['date'], y=df['log_return'], mode='lines', name='Log Return', line=dict(color='orange')))
    fig_returns.update_layout(title=f'{symbol} Simple and Log Returns', xaxis_title='Date', yaxis_title='Return', legend_title='Type of Return')

    # Create a scatter chart
    fig_scatter = go.Figure()
    fig_scatter.add_trace(go.Scatter(x=df['date'], y=df['simple_return']*100, mode='markers', name='Simple Return Scatter', marker=dict(color='black')))
    fig_scatter.update_layout(title=f'{symbol} Simple Return Scatter', xaxis_title='Date', yaxis=dict(title='Return', tickmode='array', tickvals=[i for i in range(-10, 11, 2)], ticktext=[f"{i}%" for i in range(-10, 11, 2)], range=[-10, 10]))

    # Create a cumulative return chart
    fig_cumulative = go.Figure()
    fig_cumulative.add_trace(go.Scatter(x=df['date'], y=df['cumulative_return'], mode='lines', name='Cumulative Return', line=dict(color='green')))
    fig_cumulative.update_layout(title=f'{symbol} Cumulative Return', xaxis_title='Date', yaxis_title='Cumulative Return', legend_title='Cumulative Return')

    # Create a price chart
    fig_price = go.Figure()
    fig_price.add_trace(go.Scatter(x=df['date'], y=df['close'], mode='lines', name='Price', line=dict(color='red')))
    fig_price.update_layout(title=f'{symbol} Price', xaxis_title='Date', yaxis_title='Price', legend_title='Price')

    df = df.dropna()
    fig_simple_vs_yesterday = go.Figure()
    fig_simple_vs_yesterday.add_trace(go.Scatter(x=df['simple_return_yesterday'], y=df['simple_return'], mode='markers', name='Simple Return', marker=dict(color='blue')))
    fig_simple_vs_yesterday.update_layout(title=f'{symbol} Simple Return vs Yesterday', xaxis_title='Yesterday Simple Return', yaxis_title='Today Simple Return')

    # Draw a histogram
    fig_histogram = go.Figure(data=[go.Histogram(
    x=df['simple_return'],
    xbins=dict(  # bins used for x axis
        start=-0.1,  # start range of bins
        end=0.1,     # end range of bins
        size=0.01    # size of bins
    )
)])
    fig_histogram.update_layout(bargap=0.1)
    fig_histogram.update_layout(
    title='Histogram of Simple Return',
    xaxis_title='Simple Return (%)',
    yaxis_title='Frequency'
)
    conn.close()

    return {
        'returns_data': convert_numpy(fig_returns.to_dict()),
        'scatter_data': convert_numpy(fig_scatter.to_dict()),
        'cumulative_data': convert_numpy(fig_cumulative.to_dict()),
        'price_data': convert_numpy(fig_price.to_dict()),
        'simple_vs_yesterday_data': convert_numpy(fig_simple_vs_yesterday.to_dict()),
        'histogram_data': convert_numpy(fig_histogram.to_dict())
    }
    
# Comparison for simple return
def plot_comparison_with_index(db_path, symbol):
    with sqlite3.connect(db_path) as conn:
        stock_query = f"SELECT date, simple_return FROM stock_history WHERE symbol = '{symbol}' ORDER BY date"
        index_query = "SELECT date, simple_return FROM index_data WHERE symbol = 'SPY' ORDER BY date"
        
        df_stock = pd.read_sql_query(stock_query, conn)
        df_index = pd.read_sql_query(index_query, conn)

    df_stock['date'] = pd.to_datetime(df_stock['date'])
    df_index['date'] = pd.to_datetime(df_index['date'])

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(x=df_stock['date'], y=df_stock['simple_return'], mode='lines', name=f'{symbol} Simple Return', line=dict(color='blue'))
    )
    
    fig.add_trace(
        go.Scatter(x=df_index['date'], y=df_index['simple_return'], mode='lines', name='SPY Simple Return', line=dict(color='red'))
    )

    max_return = max(df_stock['simple_return'].max(), df_index['simple_return'].max())
    min_return = min(df_stock['simple_return'].min(), df_index['simple_return'].min())
    
    fig.update_layout(
        title=f'Daily Return Comparison: {symbol} vs SPY',
        xaxis_title='Date',
        yaxis_title='Simple Return (%)',
        legend_title='Legend',
        yaxis=dict(
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor='grey',
            range=[min_return - 0.01, max_return + 0.01]
        )
    )

    return convert_numpy(fig.to_dict())

#correlation for simple return
def plot_regression_between_stock_and_index(db_path, symbol):
    with sqlite3.connect(db_path) as conn:
        stock_query = f"SELECT date, simple_return FROM stock_history WHERE symbol = '{symbol}' ORDER BY date"
        index_query = "SELECT date, simple_return FROM index_data WHERE symbol = 'SPY' ORDER BY date"
        
        df_stock = pd.read_sql_query(stock_query, conn)
        df_index = pd.read_sql_query(index_query, conn)

    df_stock['date'] = pd.to_datetime(df_stock['date'])
    df_index['date'] = pd.to_datetime(df_index['date'])

    df_merged = pd.merge(df_stock, df_index, on='date', suffixes=('_stock', '_index'))
    df_merged.dropna(inplace=True)

    if df_merged.empty:
        print("No overlapping or valid data between stock and index.")
        return {}

    slope, intercept, r_value, p_value, std_err = linregress(df_merged['simple_return_index'], df_merged['simple_return_stock'])

    df_merged['regression_line'] = intercept + slope * df_merged['simple_return_index']

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=df_merged['simple_return_index'], y=df_merged['simple_return_stock'], mode='markers', name='Returns Scatter', marker=dict(color='blue'))
    )
    fig.add_trace(
        go.Scatter(x=df_merged['simple_return_index'], y=df_merged['regression_line'], mode='lines', name='Regression Line', line=dict(color='red'))
    )
    fig.update_layout(
        title=f'Regression Analysis: {symbol} Returns vs SPY Returns',
        xaxis_title='SPY Returns (%)',
        yaxis_title=f'{symbol} Returns (%)',
        legend_title='Legend'
    )

    return convert_numpy(fig.to_dict())

#cumulative return comparison
def plot_cumulative_return_comparison(db_path, symbol):
    with sqlite3.connect(db_path) as conn:
        stock_query = f"SELECT date, cumulative_return FROM stock_history WHERE symbol = '{symbol}' ORDER BY date"
        index_query = "SELECT date, cumulative_return FROM index_data WHERE symbol = 'SPY' ORDER BY date"
        
        df_stock = pd.read_sql_query(stock_query, conn)
        df_index = pd.read_sql_query(index_query, conn)

    df_stock['date'] = pd.to_datetime(df_stock['date'])
    df_index['date'] = pd.to_datetime(df_index['date'])

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(x=df_stock['date'], y=df_stock['cumulative_return'], mode='lines', name=f'{symbol} Cumulative Return', line=dict(color='blue'))
    )
    
    fig.add_trace(
        go.Scatter(x=df_index['date'], y=df_index['cumulative_return'], mode='lines', name='SPY Cumulative Return', line=dict(color='red'))
    )

    fig.update_layout(
        title=f'Cumulative Return Comparison: {symbol} vs SPY',
        xaxis_title='Date',
        yaxis_title='Cumulative Return (%)',
        legend_title='Legend'
    )

    return convert_numpy(fig.to_dict())

#volatility comparison
def calculate_volatility(db_path, symbol):
    with sqlite3.connect(db_path) as conn:
        stock_query = f"SELECT date, close FROM stock_history WHERE symbol = '{symbol}' ORDER BY date"
        df_stock = pd.read_sql_query(stock_query, conn)
        
        index_query = "SELECT date, close FROM index_data WHERE symbol = 'SPY' ORDER BY date"
        df_index = pd.read_sql_query(index_query, conn)
        
    df_stock['date'] = pd.to_datetime(df_stock['date'])
    df_index['date'] = pd.to_datetime(df_index['date'])
    
    df_stock['returns'] = df_stock['close'].pct_change()
    df_index['returns'] = df_index['close'].pct_change()
    
    df_stock['volatility'] = df_stock['returns'].rolling(window=30).std() * np.sqrt(252)
    df_index['volatility'] = df_index['returns'].rolling(window=30).std() * np.sqrt(252)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_stock['date'], y=df_stock['volatility'], mode='lines', name=f'{symbol} Volatility'))
    fig.add_trace(go.Scatter(x=df_index['date'], y=df_index['volatility'], mode='lines', name='SPY Volatility'))

    fig.update_layout(
        title=f'30-Day Historical Volatility Comparison: {symbol} vs SPY',
        xaxis_title='Date',
        yaxis_title='Annualized Volatility',
        legend_title='Symbol'
    )

    return fig

def calculate_and_plot_rsi(db_path, symbol, window=14):
    with sqlite3.connect(db_path) as conn:
        query = f"SELECT date, close FROM stock_history WHERE symbol = '{symbol}' ORDER BY date"
        df = pd.read_sql_query(query, conn)
    
    df['date'] = pd.to_datetime(df['date'])
    df['change'] = df['close'].diff()

    df['gain'] = np.where(df['change'] > 0, df['change'], 0)
    df['loss'] = np.where(df['change'] < 0, -df['change'], 0)

    df['avg_gain'] = df['gain'].rolling(window=window, min_periods=1).mean()
    df['avg_loss'] = df['loss'].rolling(window=window, min_periods=1).mean()

    df['rs'] = df['avg_gain'] / df['avg_loss']
    df['rsi'] = 100 - (100 / (1 + df['rs']))

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['date'], y=df['rsi'], mode='lines', name='RSI'))
    fig.update_layout(
        title=f'RSI for {symbol}',
        xaxis_title='Date',
        yaxis_title='RSI',
        yaxis=dict(range=[0, 100]),
        legend_title='Symbol'
    )
    
    fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought")
    fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold")

    return fig

def plot_moving_averages(db_path, symbol):
    conn = sqlite3.connect(db_path)
    
    data = pd.read_sql(f"SELECT date, close FROM stock_history WHERE symbol='{symbol}' ORDER BY date", conn)
    data['date'] = pd.to_datetime(data['date'])
    
    data['MA10'] = data['close'].rolling(window=10).mean()
    data['MA50'] = data['close'].rolling(window=50).mean()
    data['MA200'] = data['close'].rolling(window=200).mean()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data['date'], y=data['close'], mode='lines', name='Close Price', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=data['date'], y=data['MA10'], mode='lines', name='10-day MA', line=dict(color='red')))
    fig.add_trace(go.Scatter(x=data['date'], y=data['MA50'], mode='lines', name='50-day MA', line=dict(color='green')))
    fig.add_trace(go.Scatter(x=data['date'], y=data['MA200'], mode='lines', name='200-day MA', line=dict(color='orange')))

    fig.update_layout(title=f'Moving Averages for {symbol}',
                      xaxis_title='Date',
                      yaxis_title='Price',
                      legend_title='Legend')
    
    conn.close()
    return fig
