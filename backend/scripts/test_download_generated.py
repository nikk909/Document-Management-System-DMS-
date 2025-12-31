# -*- coding: utf-8 -*-
import requests

BASE_URL = 'http://localhost:8000'

# Login
response = requests.post(f'{BASE_URL}/api/auth/login', json={'username': 'admin', 'password': 'admin'})
token = response.json().get('token')
headers = {'Authorization': f'Bearer {token}'}
print('Login: OK')

# Get generated documents
r = requests.get(f'{BASE_URL}/api/documents/generated', headers=headers)
if r.status_code == 200:
    docs = r.json().get('documents', [])
    print(f'Found {len(docs)} documents')
    if docs:
        doc = docs[0]
        print(f'Trying to download: {doc["filename"]} (ID: {doc["id"]})')
        
        # Try download
        r2 = requests.get(f'{BASE_URL}/api/documents/generated/{doc["id"]}/download', headers=headers)
        print(f'Download status: {r2.status_code}')
        if r2.status_code != 200:
            print(f'Error: {r2.text[:500]}')
        else:
            print(f'Download successful! Size: {len(r2.content)} bytes')
else:
    print(f'Error: {r.text[:300]}')

