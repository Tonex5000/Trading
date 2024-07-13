import requests

response = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=binancecoin&vs_currencies=usd')
response_data = response.json()
print(response_data)
