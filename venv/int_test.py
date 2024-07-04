import unittest
import json
from app import app, get_db_connection, setup_database

class TradingBotIntegrationTest(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

        # Setup database for testing
        setup_database()
        conn, c = get_db_connection()
        c.execute("DELETE FROM users")
        c.execute("DELETE FROM deposits")
        c.execute("DELETE FROM spot_grids")
        c.execute("DELETE FROM trades")
        conn.commit()
        conn.close()

    def test_user_registration_and_login(self):
        # Register a new user
        response = self.app.post('/register', json={
            'username': 'testuser',
            'password': 'testpassword',
            'email': 'testuser@example.com',
            'phone_number': '1234567890'
        })
        self.assertEqual(response.status_code, 201)
        self.assertIn('User created successfully', response.get_data(as_text=True))

        # Login with the new user
        response = self.app.post('/login', json={
            'username': 'testuser',
            'password': 'testpassword'
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        self.assertIn('access_token', data)

        self.access_token = data['access_token']

    def test_get_market_data(self):
        # Login with the new user to get the access token
        self.test_user_registration_and_login()

        # Fetch market data
        response = self.app.get('/market-data', headers={
            'Authorization': f'Bearer {self.access_token}'
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        self.assertIn('symbol', data)

    def test_deposit(self):
    # Login with the new user to get the access token
      self.test_user_registration_and_login()

      # Mock a deposit
      response = self.app.post('/deposit', json={
          'amount': 1000,
          'address': '0x2dF3c385E40EE91D6061102f51d053B6b603Bd19'
      }, headers={
          'Authorization': f'Bearer {self.access_token}'
      })
      self.assertEqual(response.status_code, 200)
      data = json.loads(response.get_data(as_text=True))
      self.assertIn('address', data)
      self.assertIn('deposited_amount', data)


    def test_spot_grid(self):
      self.test_user_registration_and_login()

      # Set a sufficient paper balance for the user
      conn, c = get_db_connection()
      c.execute("UPDATE users SET paper_balance = ? WHERE username = ?", (5000, 'testuser'))
      conn.commit()

      user_id = c.execute("SELECT id FROM users WHERE username = ?", ('testuser',)).fetchone()[0]
      conn.close()

      response = self.app.post('/spot-grid', json={
          'symbol': 'BTC/USDT',
          'lower_price': 30000,
          'upper_price': 40000,
          'grid_intervals': 10,
          'investment_amount': 1000
      }, headers={
          'Authorization': f'Bearer {self.access_token}'
      })

      print(f"Response Status Code: {response.status_code}")
      print(f"Response Content: {response.get_data(as_text=True)}")

      self.assertEqual(response.status_code, 200)
      data = json.loads(response.get_data(as_text=True))
      self.assertIn('msg', data)
      self.assertIn('trades', data)



    def test_get_paper_trades(self):
          # Login with the new user to get the access token
          self.test_user_registration_and_login()

          # Fetch paper trades
          response = self.app.get('/paper-trades', headers={
              'Authorization': f'Bearer {self.access_token}'
          })
          self.assertEqual(response.status_code, 200)
          data = json.loads(response.get_data(as_text=True))
          self.assertIsInstance(data, list)

    def test_get_spot_grids(self):
        # Login with the new user to get the access token
        self.test_user_registration_and_login()

        # Fetch spot grids
        response = self.app.get('/spot-grids', headers={
            'Authorization': f'Bearer {self.access_token}'
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        self.assertIsInstance(data, list)

if __name__ == '__main__':
    unittest.main()
