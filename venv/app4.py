import requests

response = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=binancecoin&vs_currencies=usd')
response_data = response.json()
print(response_data)


from flask import Flask, request, jsonify
import requests
import logging
import time

app = Flask(__name__)

def get_db_connection():
    # Dummy function, replace with actual database connection logic
    pass

@app.route('/spot-grid', methods=['POST'])
@token_required
def spot_grid(user_id):
    try:
        data = request.json
        app.logger.debug(f"Received request data: {data}")

        required_fields = ['symbol', 'lower_price', 'upper_price', 'grid_intervals', 'investment_amount', 'wallet_address']
        for field in required_fields:
            if field not in data:
                app.logger.error(f'Missing required parameter: {field}')
                return jsonify({"error": f"Missing required parameter: {field}"}), 400

        symbol = data['symbol']
        lower_price = data['lower_price']
        upper_price = data['upper_price']
        grid_intervals = data['grid_intervals']
        investment_amount = data['investment_amount']
        wallet_address = data['wallet_address']

        trading_strategy = "Spot Grid"
        roi = data.get('roi', 0)
        pnl = data.get('pnl', 0)
        runtime = data.get('runtime', "0 days 0 hours 0 minutes")

        app.logger.debug(f'Spot grid request: user_id={user_id}, wallet_address={wallet_address}, symbol={symbol}, lower_price={lower_price}, upper_price={upper_price}, grid_intervals={grid_intervals}, investment_amount={investment_amount}')

        conn, c = get_db_connection()

        paper_balance_usd = get_paper_balance_usd(c, wallet_address)
        if paper_balance_usd < investment_amount:
            app.logger.debug(f'Insufficient funds: paper_balance_usd={paper_balance_usd}, investment_amount={investment_amount}')
            return jsonify({"error": "Insufficient funds"}), 400

        # Deduct investment_amount from paper_balance
        c.execute("UPDATE users SET paper_balance = paper_balance - ? WHERE id = ?", (investment_amount, user_id))
        conn.commit()

        # Fetch the appropriate conversion rate for the selected trading pair
        symbol_map = {
            'BTC/USD': 'bitcoin',
            'ETH/USD': 'ethereum',
            'BNB/USD': 'binancecoin'
        }

        coingecko_symbol = symbol_map.get(symbol)
        if not coingecko_symbol:
            logging.error(f"Unsupported trading pair: {symbol}")
            return jsonify({"error": "Unsupported trading pair"}), 400

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

def get_paper_balance_usd(cursor, wallet_address):
    paper_balance_bnb = cursor.execute("SELECT SUM(amount) FROM deposits WHERE wallet_address = ?", (wallet_address,)).fetchone()[0]
    
    if paper_balance_bnb is None:
        return 0

    coingecko_symbol = 'binancecoin'
    response = requests.get('https://api.coingecko.com/api/v3/simple/price', 
                            params={'ids': coingecko_symbol, 'vs_currencies': 'usd'})
    response_data = response.json()
    if coingecko_symbol not in response_data or 'usd' not in response_data[coingecko_symbol]:
        logging.error(f"Unable to retrieve BNB to USD conversion rate")
        raise Exception("Unable to retrieve conversion rate")

    bnb_to_usd_rate = response_data[coingecko_symbol]['usd']
    paper_balance_usd = paper_balance_bnb * bnb_to_usd_rate
    
    return paper_balance_usd

