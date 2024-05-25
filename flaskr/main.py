from flask import Blueprint, render_template, request, redirect, url_for, flash, g, session, current_app, jsonify, json
from .auth import login_required
from .db import get_db
from .retrieve_data import Alpha_Vantage_Data
from datetime import datetime
from .plot import plot_returns, plot_comparison_with_index, plot_regression_between_stock_and_index, plot_cumulative_return_comparison, calculate_volatility,calculate_and_plot_rsi, plot_moving_averages
from plotly.utils import PlotlyJSONEncoder
from .store_history import calculate_and_update_cumulative_return, clean_old_data, fetch_and_process_data, update_spy_index_data
import plotly.io as pio
import json

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return render_template('index.html', page_data={"title": "Home"}, role=g.role)

@bp.route('/term_of_use')
def term_of_use():
    return render_template('ToU.html', page_data={"title": "Term of Use"})

# Create functions to complete transactions
@bp.route('/transaction', methods=['GET', 'POST'])
@login_required
def transaction():
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

    transactions = db.execute(
        'SELECT * FROM transactions_history WHERE user_id = ? ORDER BY timestamp DESC',
        (user_id,)
    ).fetchall()

    return render_template(
        'transaction.html', 
        user_info=user_info, 
        user_assets=user_assets,
        transactions=transactions,
        page_data={"title": "Trading Platform"}
    )

# Function to buy stock
@bp.route('/transaction/buy', methods=['POST'])
@login_required
def buy_stock():
    user_id = session.get('user_id')
    symbol = request.form.get('symbol')
    quantity = int(request.form.get('quantity'))

    if quantity <= 0:
        flash('Invalid quantity.', 'error')
        return redirect(url_for('main.transaction'))

    av_data = Alpha_Vantage_Data(symbol)
    current_price, _ = av_data.get_daily_stock_price_show()

    if current_price is None:
        flash('Unable to retrieve current price.', 'error')
        return redirect(url_for('main.transaction'))

    db = get_db()
    try:
        db.execute('BEGIN TRANSACTION')

        user = db.execute('SELECT * FROM user_info WHERE id = ?', (user_id,)).fetchone()

        total_cost = float(current_price) * quantity
        if user['balance'] < total_cost:
            flash('Insufficient balance to complete the transaction.', 'error')
            return redirect(url_for('main.transaction'))

        new_balance = user['balance'] - total_cost
        db.execute('UPDATE user_info SET balance = ? WHERE id = ?', (new_balance, user_id))

        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        db.execute('INSERT INTO transactions_history (user_id, symbol, type, quantity, price, timestamp) VALUES (?, ?, ?, ?, ?, ?)',
                   (user_id, symbol, 'BUY', quantity, current_price, current_time))

        asset = db.execute('SELECT * FROM user_assets WHERE user_id = ? AND symbol = ?', (user_id, symbol)).fetchone()
        if asset:
            new_quantity = asset['quantity'] + quantity
            db.execute('UPDATE user_assets SET quantity = ? WHERE id = ?', (new_quantity, asset['id']))
        else:
            db.execute('INSERT INTO user_assets (user_id, symbol, quantity) VALUES (?, ?, ?)', (user_id, symbol, quantity))

        time_series_daily = av_data.get_daily_stock_price()
        for date, adjusted_close in time_series_daily.items():
            formatted_date = datetime.strptime(date, '%Y-%m-%d').strftime('%Y-%m-%d')
            adjusted_close = format(float(adjusted_close), '.2f')
            db.execute('INSERT OR IGNORE INTO stock_history (symbol, date, adjusted_close) VALUES (?, ?, ?)', (symbol, formatted_date, adjusted_close))

        db.commit()
        flash('Stock purchased successfully!', 'success')
    except Exception as e:
        db.rollback()
        flash(f'Error processing transaction: {e}', 'error')
    return redirect(url_for('main.transaction'))


# Function to sell stock
@bp.route('/transaction/sell', methods=['POST'])
@login_required
def sell_stock():
    user_id = session.get('user_id')
    symbol = request.form.get('symbol')
    quantity = int(request.form.get('quantity'))

    if quantity <= 0:
        flash('Invalid quantity to sell.', 'error')
        return redirect(url_for('main.transaction'))
    
    av_data = Alpha_Vantage_Data(symbol)
    current_price, _ = av_data.get_daily_stock_price_show()
    if current_price is None:
        flash('Unable to retrieve current price.', 'error')
        return redirect(url_for('main.transaction'))

    current_price = format(float(current_price), '.2f')
    time_series_daily = av_data.get_daily_stock_price()

    db = get_db()
    try:
        db.execute('BEGIN TRANSACTION')

        asset = db.execute('SELECT * FROM user_assets WHERE user_id = ? AND symbol = ?', (user_id, symbol)).fetchone()
        if not asset or asset['quantity'] < quantity:
            flash('Not enough stock to sell.', 'error')
            return redirect(url_for('main.transaction'))

        new_quantity = asset['quantity'] - quantity
        if new_quantity > 0:
            db.execute('UPDATE user_assets SET quantity = ? WHERE id = ?', (new_quantity, asset['id']))
        else:
            db.execute('DELETE FROM user_assets WHERE id = ?', (asset['id'],))

        user = db.execute('SELECT * FROM user_info WHERE id = ?', (user_id,)).fetchone()
        updated_balance = user['balance'] + quantity * float(current_price)
        db.execute('UPDATE user_info SET balance = ? WHERE id = ?', (updated_balance, user_id))

        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        db.execute('INSERT INTO transactions_history (user_id, symbol, type, quantity, price, timestamp) VALUES (?, ?, ?, ?, ?, ?)',
                   (user_id, symbol, 'SELL', quantity, current_price, current_time))

        for date, adjusted_close in time_series_daily.items():
            formatted_date = datetime.strptime(date, '%Y-%m-%d').strftime('%Y-%m-%d')
            adjusted_close = format(float(adjusted_close), '.2f')
            db.execute('INSERT OR IGNORE INTO stock_history (symbol, date, adjusted_close) VALUES (?, ?, ?)', (symbol, formatted_date, adjusted_close))
        db.commit()
        flash('Stock sold successfully!', 'success')
    except Exception as e:
        db.rollback()
        flash(f'Error processing transaction: {e}', 'error')
    return redirect(url_for('main.transaction'))




@bp.route('/profile/conduct_transaction', methods=['POST'])
@login_required
def conduct_transaction():
    action = request.form.get('action')

    if action == 'buy':
        return buy_stock()
    elif action == 'sell':
        return sell_stock()
    else:
        flash('Invalid action.', 'error')
        return redirect(url_for('main.transaction'))



# Create contact us form
@bp.route('/contact_us')
def contact_us():
    return render_template('contact_us.html', page_data={"title": "Contact Us"})

@bp.route('/submit_contact_form', methods=['POST'])
def submit_contact_form():
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')

    db = get_db()
    db.execute(
        'INSERT INTO contact_us (name, email, message) VALUES (?, ?, ?)',
        (name, email, message)
    )
    db.commit()

    flash('Thank you for contacting us! We will get back to you soon.', 'success')
    return redirect(url_for('main.contact_us'))


@bp.route('/plot/<symbol>')
def plot_view(symbol):
    db_path = current_app.config['DATABASE']
    response = None
    try:
        # Clean Old data
        clean_old_data(db_path, 'stock_history')
        clean_old_data(db_path, 'index_data')
        # Fetch new data and then process
        fetch_and_process_data(symbol, db_path)
        update_spy_index_data(db_path)
        # Update the cumulative returns
        calculate_and_update_cumulative_return(db_path, 'stock_history')
        calculate_and_update_cumulative_return(db_path, 'index_data')

        # Generate new plots
        plot_data = plot_returns(db_path, symbol)
        comparison_plot_data = plot_comparison_with_index(db_path, symbol)
        regression_plot_data = plot_regression_between_stock_and_index(db_path, symbol)
        cumulative_comparison_data = plot_cumulative_return_comparison(db_path, symbol)
        volatility_data = calculate_volatility(db_path, symbol)
        rsi_data = calculate_and_plot_rsi(db_path,symbol)
        moving_average_data = plot_moving_averages(db_path, symbol)

        scatter_data_json = json.dumps(plot_data['scatter_data'], cls=PlotlyJSONEncoder)
        returns_data_json = json.dumps(plot_data['returns_data'], cls=PlotlyJSONEncoder)
        cumulative_data_json = json.dumps(plot_data['cumulative_data'], cls=PlotlyJSONEncoder)
        price_data_json = json.dumps(plot_data['price_data'], cls=PlotlyJSONEncoder)
        simple_vs_yesterday_data_json = json.dumps(plot_data['simple_vs_yesterday_data'], cls=PlotlyJSONEncoder)
        histogram_data_json = json.dumps(plot_data['histogram_data'], cls=PlotlyJSONEncoder)
        comparison_data_json = json.dumps(comparison_plot_data, cls=PlotlyJSONEncoder)  # 新图表数据
        regression_data_json = json.dumps(regression_plot_data, cls=PlotlyJSONEncoder)  # 新回归线散点图数据
        cumulative_comparison_data_json = json.dumps(cumulative_comparison_data, cls=PlotlyJSONEncoder)  # 新累计回报率对比图数据
        volatility_data_json = json.dumps(volatility_data, cls=PlotlyJSONEncoder)
        rsi_data_json = json.dumps(rsi_data, cls=PlotlyJSONEncoder)
        moving_average_data_json = json.dumps(moving_average_data, cls=PlotlyJSONEncoder)
        
        response = render_template('plot.html', 
                                   returns_data_json=returns_data_json, 
                                   scatter_data_json=scatter_data_json, 
                                   cumulative_data_json=cumulative_data_json, 
                                   price_data_json=price_data_json, 
                                   simple_vs_yesterday_data_json=simple_vs_yesterday_data_json, 
                                   histogram_data_json=histogram_data_json, 
                                   comparison_data_json=comparison_data_json,
                                   regression_data_json=regression_data_json,
                                   cumulative_comparison_data_json = cumulative_comparison_data_json,
                                   volatility_data_json = volatility_data_json,
                                   rsi_data_json = rsi_data_json,
                                   moving_average_data_json = moving_average_data_json,
                                   symbol=symbol)
    except Exception as e:
        response = render_template('error.html', message=str(e))
    return response
