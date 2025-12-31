# -*- coding: utf-8 -*-
import requests
import jwt

SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"

# Login with JSON
response = requests.post('http://localhost:8000/api/auth/login', json={'username': 'admin', 'password': 'admin'})
print(f'Login Status: {response.status_code}')

if response.status_code == 200:
    token = response.json().get('access_token')
    print(f'Token: {token}')
    
    # Decode token manually
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(f'\nDecoded payload: {payload}')
    except Exception as e:
        print(f'Decode error: {e}')
    
    # Test with different header formats
    print('\nTesting different header formats:')
    
    # Format 1: Bearer token
    headers1 = {'Authorization': f'Bearer {token}'}
    r1 = requests.get('http://localhost:8000/api/files/categories', headers=headers1)
    print(f'  Bearer {token[:20]}... -> Status: {r1.status_code}')
    
    # Format 2: Just token
    headers2 = {'Authorization': token}
    r2 = requests.get('http://localhost:8000/api/files/categories', headers=headers2)
    print(f'  Token only -> Status: {r2.status_code}')
    
    # Try GET user info (simpler API)
    print('\nTesting /api/auth/me:')
    r3 = requests.get('http://localhost:8000/api/auth/me', headers=headers1)
    print(f'  Status: {r3.status_code}')
    print(f'  Response: {r3.text[:200]}')

