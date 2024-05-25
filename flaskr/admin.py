from flask import Blueprint, render_template, g, redirect, url_for, flash, request
from .db import get_db
from datetime import datetime
import json

# Define the 'admin' blueprint with URL prefix '/admin'
bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.before_request
def require_admin_role():
    # Confirm that the user is logged in and has the role of admin
    if g.user is None or g.role != 'admin':
        flash('You must be an admin to view this page.', 'error')
        return redirect(url_for('main.index'))  # Assuming 'main.index' is the route for the homepage

@bp.route('/assets', methods=['GET', 'POST'])
def view_assets():
    # Establish a database connection
    db = get_db()
    # Query to aggregate the total quantity of each symbol held across all users
    assets = db.execute(
        'SELECT symbol, SUM(quantity) as total_quantity FROM user_assets GROUP BY symbol'
    ).fetchall()
    
    # Prepare asset data for display
    asset_data = [{'label': asset['symbol'], 'value': asset['total_quantity']} for asset in assets]

    # Query to get user-specific stock positions
    asset_user_data = db.execute(
        '''
        SELECT u.id as user_id, u.username, a.symbol, SUM(a.quantity) as total_quantity
        FROM user_assets a
        JOIN user_info u ON a.user_id = u.id
        GROUP BY u.id, a.symbol
        ORDER BY u.username, a.symbol
        '''
    ).fetchall()
    
    # Format the user asset data for display
    formatted_asset_user_data = [
        {'username': asset['username'], 'symbol': asset['symbol'], 'quantity': asset['total_quantity']}
        for asset in asset_user_data
    ]

    transactions = []
    search_date = None

    # Handle POST request to filter transactions by date
    if request.method == 'POST':
        search_date = request.form.get('transaction_date')
        transactions = db.execute(
            '''
            SELECT t.id, u.username, t.symbol, t.type, t.quantity, t.price, t.timestamp
            FROM transactions_history t
            JOIN user_info u ON t.user_id = u.id
            WHERE DATE(t.timestamp) = ?
            ORDER BY t.timestamp DESC
            ''', (search_date,)
        ).fetchall()
    else:
        # Get recent transactions for initial page load or when no date filter is applied
        transactions = db.execute(
            '''
            SELECT t.id, u.username, t.symbol, t.type, t.quantity, t.price, t.timestamp
            FROM transactions_history t
            JOIN user_info u ON t.user_id = u.id
            ORDER BY t.timestamp DESC
            '''
        ).fetchall()

    # Render the assets admin page with necessary data
    return render_template(
        'admin/assets.html',
        asset_data=asset_data,
        asset_user_data=formatted_asset_user_data,
        transactions=transactions,
        search_date=search_date,  # Include search date in the rendering context
        page_data={"title": 'Admin Assets Overview'}
    )

