import requests
import json

BASE_URL = "http://localhost:8000"

# Simple registration test
url = f"{BASE_URL}/api/auth/register"
payload = {
    "username": "testuser",
    "email": "test@test.com", 
    "password": "TestPass123",
    "role": "doctor"
}

print("Sending registration request...")
print(f"URL: {url}")
print(f"Payload: {json.dumps(payload, indent=2)}")

try:
    response = requests.post(url, json=payload, timeout=5)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print(f"Raw Text: {response.text}")
    print(f"Full Response Object: {response}")
    
    if response.status_code == 200:
        print(f"\nJSON: {response.json()}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {str(e)}")
