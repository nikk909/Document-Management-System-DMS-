# -*- coding: utf-8 -*-
import requests
import json

BASE_URL = 'http://localhost:8000'

def test_all():
    # Login
    response = requests.post(f'{BASE_URL}/api/auth/login', json={'username': 'admin', 'password': 'admin'})
    if response.status_code != 200:
        print(f'Login failed: {response.text}')
        return
    
    token = response.json().get('token')
    headers = {'Authorization': f'Bearer {token}'}
    print('Login: OK')
    
    # 1. Test categories
    response = requests.get(f'{BASE_URL}/api/categories', headers=headers)
    print(f'\n1. Categories: Status={response.status_code}')
    if response.status_code == 200:
        cats = response.json().get('categories', [])
        print(f'   Count: {len(cats)}')
        for cat in cats:
            print(f'   - {cat}')
    else:
        print(f'   Error: {response.text[:200]}')
    
    # 2. Test files
    response = requests.get(f'{BASE_URL}/api/files', headers=headers)
    print(f'\n2. Files: Status={response.status_code}')
    if response.status_code == 200:
        data = response.json()
        print(f'   Total: {data.get("total", 0)}')
        for f in data.get('files', [])[:3]:
            print(f'   - {f.get("filename")} (ID: {f.get("id")})')
    else:
        print(f'   Error: {response.text[:200]}')
    
    # 3. Test templates
    response = requests.get(f'{BASE_URL}/api/templates', headers=headers)
    print(f'\n3. Templates: Status={response.status_code}')
    if response.status_code == 200:
        data = response.json()
        print(f'   Total: {data.get("total", 0)}')
        for t in data.get('templates', [])[:3]:
            print(f'   - {t.get("name")} (ID: {t.get("id")}, Format: {t.get("format_type")})')
    else:
        print(f'   Error: {response.text[:200]}')
    
    # 4. Test images
    response = requests.get(f'{BASE_URL}/api/images', headers=headers)
    print(f'\n4. Images: Status={response.status_code}')
    if response.status_code == 200:
        data = response.json()
        print(f'   Total: {data.get("total", 0)}')
    else:
        print(f'   Error: {response.text[:200]}')
    
    # 5. Test file download
    response = requests.get(f'{BASE_URL}/api/files', headers=headers)
    if response.status_code == 200:
        files = response.json().get('files', [])
        if files:
            file_id = files[0].get('id')
            print(f'\n5. Download file ID {file_id}:')
            response = requests.get(f'{BASE_URL}/api/files/{file_id}/download', headers=headers)
            print(f'   Status: {response.status_code}')
            if response.status_code == 200:
                print(f'   Size: {len(response.content)} bytes')
            else:
                print(f'   Error: {response.text[:200]}')
    
    print('\n=== All tests completed ===')

if __name__ == '__main__':
    test_all()

