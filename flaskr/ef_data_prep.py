import pandas as pd
import numpy as np
import scipy.optimize as sco
import sqlite3
import json

class PortfolioOptimizer:
    def __init__(self, db_path, user_id, risk_free_rate=0.0531):
        """Initialize the PortfolioOptimizer with a path to the SQLite database."""
        self.db_path = db_path
        self.user_id = user_id
        self.risk_free_rate = risk_free_rate
        self.load_data(user_id)
    
    def load_data(self, user_id):
        """Loads stock price data from the database for the specific user and prepares it for analysis."""
        with sqlite3.connect(self.db_path) as conn:
            # First, retrieve only the symbols the user has in their assets
            user_symbols = pd.read_sql_query(
                "SELECT DISTINCT symbol FROM user_assets WHERE user_id = ?",
                conn,
                params=(user_id,)
            )
            symbols = user_symbols['symbol'].tolist()

            # Now, load only the stock history for those symbols
            query = "SELECT date, symbol, adjusted_close FROM stock_history WHERE symbol IN ({})"
            query = query.format(','.join('?' for _ in symbols))  # Create placeholders
            df = pd.read_sql_query(query, conn, params=symbols, parse_dates=['date'], index_col='date')

        # Pivot the DataFrame to have dates as index and symbols as columns with their adjusted close prices
        self.data = df.pivot(columns='symbol', values='adjusted_close')
        self.returns = self.data.pct_change().dropna()
        self.mean_returns = self.returns.mean()
        self.cov_matrix = self.returns.cov()
    
    def portfolio_annualised_performance(self, weights):
        """Calculates the annualised performance of the portfolio based on the provided weights."""
        returns = np.sum(self.mean_returns * weights) * 252
        std = np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix, weights))) * np.sqrt(252)
        return std, returns
    
    def random_portfolios(self, num_portfolios=5000):
        """Generates random portfolios and calculates their performance metrics."""
        num_assets = len(self.mean_returns)  # Number of assets based on mean_returns
        portfolio_volatilities = []
        portfolio_returns = []
        sharpe_ratios = []
        weights_record = []

        for _ in range(num_portfolios):
            weights = np.random.random(num_assets)
            weights /= np.sum(weights)  # Normalize weights to sum to 1
            
            portfolio_std_dev, portfolio_return = self.portfolio_annualised_performance(weights)
            portfolio_volatilities.append(portfolio_std_dev)
            portfolio_returns.append(portfolio_return)
            sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_std_dev
            sharpe_ratios.append(sharpe_ratio)
            weights_record.append(weights)

        return portfolio_volatilities, portfolio_returns, sharpe_ratios, weights_record

    
    def optimize_portfolio(self, target_return=None, minimize_volatility=False):
        """Optimize portfolio using either the maximum Sharpe ratio or minimum volatility approach."""
        num_assets = len(self.mean_returns)
        args = (self.mean_returns, self.cov_matrix, self.risk_free_rate)
        constraints = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1}]
        bounds = tuple((0, 1) for _ in range(num_assets))

        if minimize_volatility:
            if target_return is not None:
                constraints.append({'type': 'eq', 'fun': lambda x: self.portfolio_annualised_performance(x)[1] - target_return})
            objective_function = self.portfolio_volatility
        else:
            objective_function = lambda x: -self.portfolio_annualised_performance(x)[1] / self.portfolio_volatility(x)

        result = sco.minimize(objective_function, num_assets*[1./num_assets], args=args, method='SLSQP', bounds=bounds, constraints=constraints)
        return result
    
    def portfolio_volatility(self, weights):
        """Calculates the portfolio volatility for given weights."""
        return self.portfolio_annualised_performance(weights)[0]

    def process_simulation_results(self, portfolio_volatilities, portfolio_returns, sharpe_ratios, weights_list):
        """Process the simulation results to a DataFrame."""
        data = {
            "Volatility": portfolio_volatilities,
            "Return": portfolio_returns,
            "Sharpe Ratio": sharpe_ratios,
            "Weights": [json.dumps(weights.tolist()) for weights in weights_list]
        }
        return pd.DataFrame(data)

    def calculate_portfolio_weights(self, user_id):
        """Calculate portfolio weights based on the current holdings and latest stock prices for a specific user."""
        with sqlite3.connect(self.db_path) as conn:
            latest_prices = pd.read_sql_query(
    """
    SELECT sh.symbol, sh.adjusted_close
    FROM stock_history sh
    INNER JOIN (
        SELECT symbol, MAX(date) as max_date
        FROM stock_history
        GROUP BY symbol
    ) latest ON sh.symbol = latest.symbol AND sh.date = latest.max_date
    """,
    conn
)

            user_assets = pd.read_sql_query(
                "SELECT symbol, quantity FROM user_assets WHERE user_id = ?",
                conn,
                params=(user_id,)
            )
        merged_data = pd.merge(user_assets, latest_prices, on='symbol')
        merged_data['total_value'] = merged_data['quantity'] * merged_data['adjusted_close']
        total_portfolio_value = merged_data['total_value'].sum()
        merged_data['weight'] = merged_data['total_value'] / total_portfolio_value
        return merged_data[['symbol', 'weight']], merged_data['weight'].values

    def calculate_user_portfolio_performance(self):
        """Calculate the user portfolio's return and volatility based on current weights."""
        _, weights = self.calculate_portfolio_weights()
        weights = np.array(weights, dtype=float)
        std_dev, annual_return = self.portfolio_annualised_performance(weights)
        return annual_return, std_dev
    
    def get_user_symbols(self, user_id):
        """Retrieve and return a list of stock symbols from the user_assets table for a specific user."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DISTINCT symbol FROM user_assets WHERE user_id = ?",
                (user_id,)
            )
            symbols_data = cursor.fetchall()
        symbols_list = [item[0] for item in symbols_data]
        return symbols_list


