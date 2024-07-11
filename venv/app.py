import sqlite3
from flask import Flask, jsonify, request, render_template
import logging
import jwt
from datetime import datetime, timedelta
from functools import wraps
import requests
from flask_cors import CORS
from database import setup_database

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

app.config['TOKEN_EXPIRATION_DAYS'] = 30
app.config['SECRET_KEY'] = '09d607fc4bbd698d4334427605aa78b9899c7798a1d1998c8381cb1ca7712067'  # Ensure this is kept secret and safe

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Helper function to get database connection
def get_db_connection():
    conn = sqlite3.connect('trading_bot.db', timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn, conn.cursor()

# Helper function to create a new JWT token
def create_token(user_id):
    expiration = datetime.utcnow() + timedelta(days=app.config['TOKEN_EXPIRATION_DAYS'])
    payload = {
        'user_id': user_id,
        'exp': expiration
    }
    token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
    return token

# Function to test token validity
def test_token_validity(token):
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return True, payload['user_id']
    except jwt.ExpiredSignatureError:
        return False, None
    except jwt.InvalidTokenError:
        return False, None

# Decorator to require token authentication
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"msg": "Token is missing"}), 401
        is_valid, user_id = test_token_validity(token)

        return f(user_id, *args, **kwargs)
    return decorated

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login-page', methods=['GET'])
def login_page():
    return render_template('login.html')


@app.route('/register', methods=['POST'])
def register():
    try:
        if request.content_type == 'application/json':
            # Handle JSON data
            data = request.json
            username = data['username']
            password = data['password']
            email = data.get('email')
            phone_number = data.get('phone_number')
        else:
            # Handle form data
            username = request.form['username']
            password = request.form['password']
            email = request.form.get('email')
            phone_number = request.form.get('phone_number')

        conn, c = get_db_connection()
        c.execute(
            "INSERT INTO users (username, password, email, phone_number, paper_balance) VALUES (?, ?, ?, ?, ?)", 
            (username, password, email, phone_number, 0)
        )
        conn.commit()
        conn.close()
        
        logging.debug(f"User {username} registered successfully")
        return jsonify({"msg": "User created successfully"}), 201
    except Exception as e:
        logging.exception('Error during registration')
        return str(e), 500

@app.route('/login', methods=['POST'])
def login():
    try:
        if request.content_type == 'application/json':
            # Handle JSON data
            data = request.json
            username = data['username']
            password = data['password']
        else:
            # Handle form data
            username = request.form['username']
            password = request.form['password']

        conn, c = get_db_connection()
        user = c.execute(
            "SELECT id FROM users WHERE username = ? AND password = ?", 
            (username, password)
        ).fetchone()
        conn.close()
        
        if user:
            token = create_token(user['id'])
            logging.debug(f"User {username} logged in successfully")
            return jsonify(token=token), 200
        else:
            logging.warning(f"Failed login attempt for username: {username}")
            return jsonify({"msg": "Bad username or password"}), 401
    except Exception as e:
        logging.exception('Error during login')
        return str(e), 500


@app.route('/market-data', methods=['GET'])
@token_required
def get_market_data(user_id):
    try:
        response = requests.get('https://api.coingecko.com/api/v3/simple/price', 
                                params={'ids': 'bitcoin', 'vs_currencies': 'usd'})
        if response.status_code != 200:
            logging.error('Failed to fetch market data from CoinGecko')
            return jsonify({"error": "Failed to fetch market data"}), 500

        market_data = response.json()
        logging.debug(f"Fetched market data: {market_data}")

        ticker = {
            "symbol": "BTC/USDT",
            "price": market_data['bitcoin']['usd']
        }

        return jsonify(ticker)
    except Exception as e:
        logging.exception('Error fetching market data')
        return str(e), 500

@app.route('/deposit', methods=['POST'])
@token_required
def deposit(user_id):
    try:
        data = request.json
        user_address = data['userAddress']
        deposited_amount = data['amount']
        balance_usd = data['usdBalance']
        status = data.get('status', 'Pending')
        transaction_hash = data.get('transactionHash')

        logging.debug(f'Deposit request: user_id={user_id}, address={user_address}, amount={deposited_amount}, balance={balance_usd}, status={status}, tx_hash={transaction_hash}')

        conn, c = get_db_connection()
        c.execute("INSERT INTO deposits (user_id, address, amount, balance_usd, status, transaction_hash) VALUES (?, ?, ?, ?, ?, ?)",
                  (user_id, user_address, deposited_amount, balance_usd, status, transaction_hash))
        c.execute("UPDATE users SET paper_balance = paper_balance + ? WHERE id = ?", (balance_usd, user_id))
        conn.commit()
        conn.close()

        logging.debug(f'Deposit successful for user_id={user_id}, amount={balance_usd}')
        return jsonify({'address': user_address, 'deposited_amount': balance_usd, 'status': status, 'transaction_hash': transaction_hash})
    except Exception as e:
        logging.exception('Error during deposit')
        return str(e), 500

@app.route('/spot-grid', methods=['POST'])
@token_required
def spot_grid(user_id):
    try:
        data = request.json
        app.logger.debug(f"Received request data: {data}")

        required_fields = ['symbol', 'lower_price', 'upper_price', 'grid_intervals', 'investment_amount']
        for field in required_fields:
            if field not in data:
                app.logger.error(f'Missing required parameter: {field}')
                return jsonify({"error": f"Missing required parameter: {field}"}), 400

        symbol = data['symbol']
        lower_price = data['lower_price']
        upper_price = data['upper_price']
        grid_intervals = data['grid_intervals']
        investment_amount = data['investment_amount']

        trading_strategy = "Spot Grid"
        roi = data.get('roi', 0)
        pnl = data.get('pnl', 0)
        runtime = data.get('runtime', "0 days 0 hours 0 minutes")

        app.logger.debug(f'Spot grid request: user_id={user_id}, symbol={symbol}, lower_price={lower_price}, upper_price={upper_price}, grid_intervals={grid_intervals}, investment_amount={investment_amount}')

        conn, c = get_db_connection()
        paper_balance = c.execute("SELECT paper_balance FROM users WHERE id = ?", (user_id,)).fetchone()[0]
        if paper_balance is None or paper_balance < investment_amount:
            app.logger.debug(f'Insufficient funds: paper_balance={paper_balance}, investment_amount={investment_amount}')
            return jsonify({"error": "Insufficient funds"}), 400

        c.execute("UPDATE users SET paper_balance = paper_balance - ? WHERE id = ?", (investment_amount, user_id))
        conn.commit()

        coingecko_symbol = 'bitcoin'
        response = requests.get('https://api.coingecko.com/api/v3/simple/price', 
                                params={'ids': coingecko_symbol, 'vs_currencies': 'usd'})
        response_data = response.json()
        if coingecko_symbol not in response_data or 'usd' not in response_data[coingecko_symbol]:
            logging.error(f"Unable to retrieve market price for symbol: {symbol}")
            return jsonify({"error": "Unable to retrieve market price"}), 500

        market_price = response_data[coingecko_symbol]['usd']

        grid_prices = [lower_price + x * (upper_price - lower_price) / (grid_intervals - 1) for x in range(grid_intervals)]
        if market_price not in grid_prices:
            grid_prices.append(market_price)
            grid_prices.sort()

        trades = []
        for price in grid_prices:
            buy_amount = investment_amount / grid_intervals / price
            buy_trade = {
                'user_id': user_id,
                'symbol': symbol,
                'type': 'limit',
                'side': 'buy',
                'amount': buy_amount,
                'price': price,
                'timestamp': int(time.time())
            }
            trades.append(buy_trade)

            sell_price = price * 1.01
            sell_amount = buy_amount
            sell_trade = {
                'user_id': user_id,
                'symbol': symbol,
                'type': 'limit',
                'side': 'sell',
                'amount': sell_amount,
                'price': sell_price,
                'timestamp': int(time.time())
            }
            trades.append(sell_trade)

        c.execute(
            "INSERT INTO spot_grids (user_id, trading_pair, trading_strategy, roi, pnl, runtime, min_investment, status, user_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, symbol, trading_strategy, roi, pnl, runtime, investment_amount, "Active", 1)
        )
        spot_grid_id = c.lastrowid

        for trade in trades:
            c.execute(
                "INSERT INTO trades (user_id, symbol, type, side, amount, price, timestamp, spot_grid_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (trade['user_id'], trade['symbol'], trade['type'], trade['side'], trade['amount'], trade['price'], trade['timestamp'], spot_grid_id)
            )

        conn.commit()
        conn.close()

        logging.debug(f'Spot grid trading started successfully for user_id={user_id}, trades={trades}')
        return jsonify({"msg": "Grid trading started successfully", "trades": trades}), 200
    except Exception as e:
        app.logger.error(f"Error during spot grid: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/marketplace', methods=['GET'])
@token_required
def get_marketplace(user_id):
    try:
        sort_by = request.args.get('sort_by', 'roi')

        conn, c = get_db_connection()
        if (sort_by == 'roi'):
            c.execute("SELECT id, trading_pair, roi, pnl, runtime, min_investment, user_count FROM spot_grids WHERE status = 'Active' ORDER BY roi DESC")
        elif (sort_by == 'pnl'):
            c.execute("SELECT id, trading_pair, roi, pnl, runtime, min_investment, user_count FROM spot_grids WHERE status = 'Active' ORDER BY pnl DESC")
        elif (sort_by == 'copied'):
            c.execute("SELECT id, trading_pair, roi, pnl, runtime, min_investment, user_count FROM spot_grids WHERE status = 'Active' ORDER BY user_count DESC")
        else:
            conn.close()
            logging.error(f"Invalid sorting parameter: {sort_by}")
            return jsonify({"error": "Invalid sorting parameter"}), 400

        spot_grids = c.fetchall()
        conn.close()

        bot_list = []
        for grid in spot_grids:
            bot_list.append({
                "id": grid[0],
                "trading_pair": grid[1],
                "roi": grid[2],
                "pnl": grid[3],
                "runtime": grid[4],
                "min_investment": grid[5],
                "user_count": grid[6]
            })

        logging.debug(f"Fetched marketplace data: {bot_list}")
        return jsonify(bot_list)
    except Exception as e:
        logging.exception('Error fetching marketplace data')
        return str(e), 500

@app.route('/paper-trades', methods=['GET'])
@token_required
def get_paper_trades(user_id):
    try:
        conn, c = get_db_connection()
        trades = c.execute("SELECT * FROM trades WHERE user_id = ?", (user_id,)).fetchall()
        conn.close()

        trade_list = []
        for trade in trades:
            trade_list.append({
                "id": trade[0],
                "user_id": trade[1],
                "symbol": trade[2],
                "type": trade[3],
                "side": trade[4],
                "amount": trade[5],
                "price": trade[6],
                "timestamp": trade[7],
                "spot_grid_id": trade[8]
            })

        logging.debug(f"Fetched paper trades for user_id={user_id}: {trade_list}")
        return jsonify(trade_list)
    except Exception as e:
        logging.exception('Error fetching paper trades')
        return str(e), 500

@app.route('/spot-grids', methods=['GET'])
@token_required
def get_spot_grids(user_id):
    try:
        conn, c = get_db_connection()
        spot_grids = c.execute("SELECT * FROM spot_grids WHERE user_id = ?", (user_id,)).fetchall()
        conn.close()

        grid_list = []
        for grid in spot_grids:
            grid_list.append({
                "id": grid[0],
                "user_id": grid[1],
                "trading_pair": grid[2],
                "trading_strategy": grid[3],
                "roi": grid[4],
                "pnl": grid[5],
                "runtime": grid[6],
                "min_investment": grid[7],
                "status": grid[8],
                "user_count": grid[9]
            })

        logging.debug(f"Fetched spot grids for user_id={user_id}: {grid_list}")
        return jsonify(grid_list)
    except Exception as e:
        logging.exception('Error fetching spot grids')
        return str(e), 500

@app.route('/trade_history', methods=['GET'])
@token_required
def trade_history(user_id):
    conn, c = get_db_connection()
    trades = c.execute("SELECT timestamp, symbol, type, side, amount, price FROM trades WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()

    trade_history = []
    for trade in trades:
        trade_history.append({
            "timestamp": trade["timestamp"],
            "symbol": trade["symbol"],
            "type": trade["type"],
            "side": trade["side"],
            "amount": trade["amount"],
            "price": trade["price"]
        })

    return jsonify(trade_history)

@app.route('/deposit_history', methods=['GET'])
@token_required
def get_deposit_history(user_id):
    try:
        logging.debug(f'Fetching deposit history for user_id: {user_id}')

        conn, c = get_db_connection()
        c.execute("SELECT amount, status, timestamp FROM deposits WHERE user_id = ?", (user_id,))
        deposits = c.fetchall()
        conn.close()

        deposit_history = []
        for deposit in deposits:
            deposit_history.append({
                'amount': deposit['amount'],
                'status': deposit['status'],
                'timestamp': deposit['timestamp']
            })

        return jsonify(deposit_history)
    except Exception as e:
        logging.exception('Error fetching deposit history')
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    setup_database()
    app.run(port=5000)
