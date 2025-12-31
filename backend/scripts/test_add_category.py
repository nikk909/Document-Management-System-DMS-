# -*- coding: utf-8 -*-
import requests

BASE_URL = 'http://localhost:8000'

# Login
response = requests.post(f'{BASE_URL}/api/auth/login', json={'username': 'admin', 'password': 'admin'})
token = response.json().get('token')
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
print(f'Login: OK')

# Get current categories
r = requests.get(f'{BASE_URL}/api/categories', headers=headers)
print(f'\n1. Current categories: {r.json().get("categories", [])}')

# Add new category
r = requests.post(f'{BASE_URL}/api/categories', headers=headers, json={'category': 'test_new_category'})
print(f'\n2. Add category status: {r.status_code}')
print(f'   Response: {r.text}')

# Get categories again
r = requests.get(f'{BASE_URL}/api/categories', headers=headers)
print(f'\n3. Categories after add: {r.json().get("categories", [])}')

