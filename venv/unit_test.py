import unittest
from flask import json
from flask_jwt_extended import create_access_token
from app import app, get_db_connection, setup_database

class FlaskAppTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Ensure the database is set up before running tests
        setup_database()

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        with app.app_context():
            self.conn, self.c = get_db_connection()
            self.c.execute("DELETE FROM users")
            self.c.execute("DELETE FROM deposits")
            self.c.execute("DELETE FROM trades")
            self.c.execute("DELETE FROM spot_grids")
            self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def test_register_user(self):
        response = self.app.post('/register', data=json.dumps({
            'username': 'testuser',
            'password': 'testpass',
            'email': 'test@example.com',
            'phone_number': '1234567890'
        }), content_type='application/json')

        self.assertEqual(response.status_code, 201)
        self.assertIn('User created successfully', response.get_data(as_text=True))

    def test_login_user(self):
        self.c.execute("INSERT INTO users (username, password, email, phone_number, paper_balance) VALUES (?, ?, ?, ?, ?)",
                       ('testuser', 'testpass', 'test@example.com', '1234567890', 0))
        self.conn.commit()

        response = self.app.post('/login', data=json.dumps({
            'username': 'testuser',
            'password': 'testpass'
        }), content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertIn('access_token', json.loads(response.get_data(as_text=True)))

    def test_get_market_data(self):
        # First, login to get a valid JWT token
        self.c.execute("INSERT INTO users (username, password, email, phone_number, paper_balance) VALUES (?, ?, ?, ?, ?)",
                       ('testuser', 'testpass', 'test@example.com', '1234567890', 0))
        self.conn.commit()

        response = self.app.post('/login', data=json.dumps({
            'username': 'testuser',
            'password': 'testpass'
        }), content_type='application/json')

        access_token = json.loads(response.get_data(as_text=True))['access_token']

        # Use the token to get market data
        response = self.app.get('/market-data', headers={
            'Authorization': f'Bearer {access_token}'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('symbol', json.loads(response.get_data(as_text=True)))

if __name__ == '__main__':
    unittest.main()
