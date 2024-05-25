from flask import Flask, jsonify, request, render_template, current_app
import json
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from alpha_vantage.timeseries import TimeSeries
import os
from .plot import plot_returns
from plotly.utils import PlotlyJSONEncoder 
from .retrieve_data import Alpha_Vantage_Data


app = Flask(__name__)
def clean_old_data(db_path, table_name='stock_history'):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        five_years_ago = datetime.now() - timedelta(days=5*365)
        cursor.execute(f'''
        DELETE FROM {table_name}
        WHERE date < ?
        ''', (five_years_ago.strftime('%Y-%m-%d'),))
        conn.commit()

def fetch_and_process_data(symbol, db_path, is_index=False):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        ts = TimeSeries(key=os.getenv('ALPHAVANTAGE_API_KEY'), output_format='pandas')
        data, meta_data = ts.get_daily_adjusted(symbol=symbol, outputsize='full')
        data = data[data.index >= (datetime.now() - timedelta(days=5*365+1))]
        
        data['symbol'] = symbol
        data['date'] = data.index.strftime('%Y-%m-%d')
        data['simple_return'] = data['4. close'].pct_change()
        data['log_return'] = np.log(data['4. close'] / data['4. close'].shift(1))
        
        table_name = 'index_data' if is_index else 'stock_history'
        
        for index, row in data.iterrows():
            cursor.execute(f'''
            SELECT COUNT(*) FROM {table_name} WHERE symbol=? AND date=?
            ''', (row['symbol'], row['date']))
            exists = cursor.fetchone()[0] > 0
            
            if exists:
                cursor.execute(f'''
                UPDATE {table_name} SET
                open=?, high=?, low=?, close=?, volume=?, adjusted_close=?, simple_return=?, log_return=?
                WHERE symbol=? AND date=?
                ''', (row['1. open'], row['2. high'], row['3. low'], row['4. close'], row['6. volume'],
                      row['5. adjusted close'], row['simple_return'], row['log_return'], row['symbol'], row['date']))
            else:
                cursor.execute(f'''
                INSERT INTO {table_name} 
                (symbol, date, open, high, low, close, volume, adjusted_close, simple_return, log_return)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (row['symbol'], row['date'], row['1. open'], row['2. high'], row['3. low'], 
                      row['4. close'], row['6. volume'], row['5. adjusted close'], 
                      row['simple_return'], row['log_return']))
                
        conn.commit()


def update_spy_index_data(db_path):
    ts = TimeSeries(key=os.getenv('ALPHAVANTAGE_API_KEY'), output_format='pandas')
    symbol = 'SPY'

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            data, meta_data = ts.get_daily_adjusted(symbol=symbol, outputsize='full')
            data = data[['1. open', '2. high', '3. low', '4. close', '6. volume', '5. adjusted close']]
            data.reset_index(inplace=True)
            data.rename(columns={
                'index': 'date',
                '1. open': 'open',
                '2. high': 'high',
                '3. low': 'low',
                '4. close': 'close',
                '6. volume': 'volume',
                '5. adjusted close': 'adjusted_close'
            }, inplace=True)

            data['date'] = pd.to_datetime(data['date'])
            five_years_ago = datetime.now() - timedelta(days=5 * 365)
            data = data[data['date'] >= five_years_ago]

            data['simple_return'] = data['close'].pct_change()
            data['log_return'] = np.log(data['close'] / data['close'].shift(1))

            data.fillna(0, inplace=True)

            data['date'] = data['date'].dt.strftime('%Y-%m-%d')

            data_tuples = data.to_records(index=False).tolist()
            insert_query = '''
                INSERT OR REPLACE INTO index_data
                (symbol, date, open, high, low, close, volume, adjusted_close, simple_return, log_return)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            cursor.executemany(insert_query, [(symbol, *row) for row in data_tuples])

            conn.commit()
            print(f"{len(data_tuples)} rows processed for symbol {symbol}.")

    except Exception as e:
        print(f"An error occurred: {e}")

def calculate_and_update_cumulative_return(db_path, symbol):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute(f"SELECT date, close FROM stock_history WHERE symbol=? ORDER BY date ASC", (symbol,))
        rows = cursor.fetchall()

        if rows:
            initial_value = rows[0][1]
            cumulative_return = 0

            for i, row in enumerate(rows):
                if i == 0:
                    cumulative_return = 0
                else:
                    cumulative_return = (row[1] - initial_value) / initial_value

                cursor.execute(f"UPDATE stock_history SET cumulative_return=? WHERE symbol=? AND date=?", (cumulative_return, symbol, row[0]))

        conn.commit()




    


