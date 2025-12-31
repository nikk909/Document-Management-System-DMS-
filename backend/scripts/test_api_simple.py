# -*- coding: utf-8 -*-
import requests
import json

# Login with JSON
response = requests.post('http://localhost:8000/api/auth/login', json={'username': 'admin', 'password': 'admin'})
print(f'Login Status: {response.status_code}')
if response.status_code == 200:
    # Note: API returns 'token' not 'access_token'
    token = response.json().get('token')
    print(f'Token obtained successfully')
    
    # Test categories
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get('http://localhost:8000/api/categories', headers=headers)
    print(f'\nCategories API Status: {response.status_code}')
    if response.status_code == 200:
        data = response.json()
        cats = data.get('categories', [])
        print(f'Categories count: {len(cats)}')
        for cat in cats:
            print(f'  - {cat}')
    else:
        print(f'Error: {response.text[:500]}')
else:
    print(f'Login Error: {response.text[:500]}')

