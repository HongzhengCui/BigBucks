from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, make_response
from .db import get_db
from .auth import login_required
from .retrieve_data import Alpha_Vantage_Data

bp = Blueprint('stock', __name__, url_prefix='/stock')

@bp.route('/', methods=['GET', 'POST'])
@bp.route('/<symbol>', methods=['GET'])
def show_stock_info(symbol=None):
    page_data = {
        "title": (symbol if symbol else ""),
        "inputValue": symbol if symbol else ""
    }

    overview_data = None
    current_price_data = None
    news_data = []

    if symbol:
        av_data = Alpha_Vantage_Data(symbol)
        overview_data = av_data.get_overview()
        if not overview_data:
            flash(f'Stock symbol not found or error in API call: {symbol}', 'error')
            
        current_price_data, date = av_data.get_daily_stock_price_show()
        print(current_price_data)
        if not current_price_data:
            flash(f'Stock symbol not found or error in API call: {symbol}', 'error')

        news_data = av_data.get_news_sentiment()
        if not news_data:
            flash(f'Stock symbol not found or error in API call: {symbol}', 'error')
    return render_template(
        "stock.html",
        page_data=page_data,
        overview_data=overview_data,
        current_price_data=current_price_data,
        current_time = date,
        news_data=news_data,
        symbol=symbol
    )

@bp.route('/pricing/<symbol>')
def retrieve_stock_prices(symbol):
    av_data = Alpha_Vantage_Data(symbol)
    time_series_data = av_data.get_daily_stock_price()

    if time_series_data:
        dates = list(time_series_data.keys())
        adj_close_prices = list(time_series_data.values())
        result = {
            "symbol": symbol,
            "dates": dates,
            "adjClosePrices": adj_close_prices
        }
        return jsonify(result)
    else:
        return make_response(jsonify({'error': 'Data not found'}), 404)
