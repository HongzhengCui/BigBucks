from flask import Flask, render_template, jsonify, Blueprint, render_template, session, current_app, g
import numpy as np
import json
from .ef_data_prep import PortfolioOptimizer
from .auth import login_required
from .db import get_db

bp = Blueprint('profile', __name__, url_prefix='/profile')

@bp.route('/')
@login_required
def profile():
    user_id = session.get('user_id')
    
    db = get_db()
    user_info = db.execute(
        'SELECT * FROM user_info WHERE id = ?',
        (user_id,)
    ).fetchone()

    user_assets = db.execute(
        'SELECT * FROM user_assets WHERE user_id = ?',
        (user_id,)
    ).fetchall()
    
    return render_template(
        'profile.html', 
        user_info=user_info, 
        user_assets=user_assets,
        page_data={"title": "Profile"}
    )


@bp.route('/get-plot-data')
def get_plot_data():
    db_path = current_app.config['DATABASE']
    user_id = g.user['id']
    optimizer = PortfolioOptimizer(db_path=db_path, user_id=user_id)
    symbols = optimizer.get_user_symbols(user_id)
    
    # Assuming the weights are correctly stored and simulation results are calculated
    portfolio_volatilities, portfolio_returns, sharpe_ratios, weights = optimizer.random_portfolios(num_portfolios=30000)
    simulation_results_df = optimizer.process_simulation_results(portfolio_volatilities, portfolio_returns, sharpe_ratios, weights)

    if simulation_results_df.empty:
        return jsonify({"error": "No simulation results available."}), 500

    volatilities = simulation_results_df['Volatility'].tolist()
    returns = simulation_results_df['Return'].tolist()
    max_sharpe_idx = simulation_results_df['Sharpe Ratio'].idxmax()
    min_vol_idx = simulation_results_df['Volatility'].idxmin()

    max_sharpe_weights = json.loads(simulation_results_df.at[max_sharpe_idx, 'Weights'])
    min_vol_weights = json.loads(simulation_results_df.at[min_vol_idx, 'Weights'])

    user_portfolio_weights_df, weights_array = optimizer.calculate_portfolio_weights(user_id)
    user_portfolio_weights = user_portfolio_weights_df['weight'].values
    user_perf = optimizer.portfolio_annualised_performance(user_portfolio_weights)

    data = {
        "symbols": symbols,
        "ef_curve": {
            "returns": returns,
            "volatilities": volatilities
        },
        "user_portfolio": {
            "performance": user_perf,
            "weights": user_portfolio_weights.tolist()
        },
        "max_sharpe_portfolio": {
            "performance": optimizer.portfolio_annualised_performance(np.array(max_sharpe_weights)),
            "weights": max_sharpe_weights
        },
        "min_vol_portfolio": {
            "performance": optimizer.portfolio_annualised_performance(np.array(min_vol_weights)),
            "weights": min_vol_weights
        }
    }

    return jsonify(data)