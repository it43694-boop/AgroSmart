import requests

response = requests.post(
    "http://127.0.0.1:8001/token",
    data={
        "admin_code": "Ibrahim200119!",
        "username": "admin@test.com"
    }
)

if response.status_code == 200:
    data = response.json()
    print(data.get('access_token', ''))
else:
    print(f"Error: {response.status_code}")
    print(response.text)
