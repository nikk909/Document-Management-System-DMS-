# -*- coding: utf-8 -*-
import requests
import time

BASE_URL = 'http://localhost:8000'

# Login
response = requests.post(f'{BASE_URL}/api/auth/login', json={'username': 'admin', 'password': 'admin'})
token = response.json().get('token')
headers = {'Authorization': f'Bearer {token}'}
print('Login: OK')

# Check generated docs before
r = requests.get(f'{BASE_URL}/api/documents/generated', headers=headers)
before_count = r.json().get('total', 0) if r.status_code == 200 else 0
print(f'\nBefore generation: {before_count} documents')

# Generate document
form_data = {
    'template_id': 33,  # test1 word template
    'data_file_id': 33,  # test3.json
    'output_format': 'word',
    'enable_masking': 'false',
    'enable_encryption': 'false',
    'enable_watermark': 'false',
    'enable_table': 'true',
    'enable_chart': 'true'
}

print('\nGenerating document...')
r = requests.post(f'{BASE_URL}/api/documents/generate', headers=headers, data=form_data)
print(f'Status: {r.status_code}')
if r.status_code == 200:
    result = r.json()
    print(f'Success: {result.get("success")}')
    print(f'Document ID: {result.get("document_id")}')
    print(f'Filename: {result.get("filename")}')
    print(f'MinIO Path: {result.get("minio_path")}')
else:
    print(f'Error: {r.text[:500]}')

# Wait a bit
time.sleep(1)

# Check generated docs after
r = requests.get(f'{BASE_URL}/api/documents/generated', headers=headers)
after_count = r.json().get('total', 0) if r.status_code == 200 else 0
print(f'\nAfter generation: {after_count} documents')
if r.status_code == 200:
    docs = r.json().get('documents', [])[:3]
    for doc in docs:
        print(f'  - {doc.get("filename")} (ID: {doc.get("id")})')

