import os
import requests
import pandas

class Alpha_Vantage_Data:
    def __init__(self, symbol):
        self.symbol = symbol.upper()
        self.api_key = os.getenv('ALPHAVANTAGE_API_KEY')
        self.base_url = 'https://www.alphavantage.co/query'
        
    def get_overview(self):
        params = {
            "function": "OVERVIEW",
            "symbol": self.symbol,
            "apikey": self.api_key
        }
        response = requests.get(self.base_url, params=params)
        return response.json() if response.ok else None

    def get_news_sentiment(self):
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": self.symbol,
            "apikey": self.api_key
        }
        response = requests.get(self.base_url, params=params)
        return response.json()['feed'][:5] if response.ok else None

    def get_daily_stock_price(self):
        params = {
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": self.symbol,
            "apikey": self.api_key,
            "outputsize": "full"
        }
        response = requests.get(self.base_url, params=params)
        if response.ok:
            data = response.json()
            closing_prices = {}
            sorted_dates = sorted(data['Time Series (Daily)'].keys(), reverse=True)
            for date in sorted_dates[:252*5]:
                closing_prices[date] = data['Time Series (Daily)'][date]['5. adjusted close']
            return closing_prices
        else:
            return None
        
    def get_intraday_stock_price(self):
        params = {
            "function": "TIME_SERIES_INTRADAY",
            "symbol": self.symbol,
            "interval": "1min",
            "apikey": self.api_key
        }
        response = requests.get(self.base_url, params=params)
        if response.ok:
            data = response.json()
            latest_timestamp = max(data['Time Series (1min)'].keys())
            latest_price = data['Time Series (1min)'][latest_timestamp]['4. close']
            return latest_price, latest_timestamp
        else:
            return None, None
        
        
    def get_daily_stock_price_show(self):
        params = {
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": self.symbol,
            "apikey": self.api_key
        }
        response = requests.get(self.base_url, params=params)
        if response.ok:
            data = response.json()
            latest_timestamp = max(data["Time Series (Daily)"].keys())
            latest_price = data["Time Series (Daily)"][latest_timestamp]['5. adjusted close']
            return latest_price, latest_timestamp
        else:
            return None, None

