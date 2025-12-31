# -*- coding: utf-8 -*-
"""测试水印功能详细情况"""
import requests
import os

BASE_URL = 'http://localhost:8000'

# Login
response = requests.post(f'{BASE_URL}/api/auth/login', json={'username': 'admin', 'password': 'admin'})
token = response.json().get('token')
headers = {'Authorization': f'Bearer {token}'}
print('Login: OK')

# Get a data file
r = requests.get(f'{BASE_URL}/api/files?page=1&page_size=10', headers=headers)
files = r.json().get('files', [])
data_file = None
for f in files:
    if f['filename'].endswith('.json') or f['filename'].endswith('.csv'):
        data_file = f
        break

if not data_file:
    print('No data file found')
    exit(1)

print(f'Using data file: {data_file["filename"]} (ID: {data_file["id"]})')

# Get a template
r = requests.get(f'{BASE_URL}/api/templates?page=1&page_size=10', headers=headers)
templates = r.json().get('templates', [])
if not templates:
    print('No template found')
    exit(1)

template = templates[0]
print(f'Using template: {template["name"]} (ID: {template["id"]})')

# Generate with watermark
print('\n--- Generating Word document with watermark ---')
form_data = {
    'template_id': str(template['id']),
    'data_file_id': str(data_file['id']),
    'output_format': 'word',
    'enable_watermark': 'true',
    'watermark_text': 'TEST WATERMARK',
    'enable_table': 'true',
    'enable_chart': 'true'
}

# Make request
r = requests.post(f'{BASE_URL}/api/documents/generate', data=form_data, headers=headers)
print(f'Response status: {r.status_code}')
if r.status_code == 200:
    result = r.json()
    print(f'Success! Document ID: {result.get("document_id")}')
    print(f'Filename: {result.get("filename")}')
else:
    print(f'Error: {r.text[:500]}')

