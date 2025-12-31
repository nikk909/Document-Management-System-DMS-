# -*- coding: utf-8 -*-
import requests

BASE_URL = 'http://localhost:8000'

# Login
response = requests.post(f'{BASE_URL}/api/auth/login', json={'username': 'admin', 'password': 'admin'})
token = response.json().get('token')
headers = {'Authorization': f'Bearer {token}'}
print('Login: OK')

# Test Word with watermark
print('\n=== Test 1: Word with text watermark ===')
form_data = {
    'template_id': 33,  # test1 word template
    'data_file_id': 33,  # test3.json
    'output_format': 'word',
    'enable_watermark': 'true',
    'watermark_text': 'Confidential',
}
r = requests.post(f'{BASE_URL}/api/documents/generate', headers=headers, data=form_data)
print(f'Status: {r.status_code}')
if r.status_code == 200:
    print(f'Success: {r.json().get("filename")}')
else:
    print(f'Error: {r.text[:300]}')

# Test HTML with watermark
print('\n=== Test 2: HTML with text watermark ===')
form_data['output_format'] = 'html'
form_data['template_id'] = 34  # HTML template
r = requests.post(f'{BASE_URL}/api/documents/generate', headers=headers, data=form_data)
print(f'Status: {r.status_code}')
if r.status_code == 200:
    print(f'Success: {r.json().get("filename")}')
else:
    print(f'Error: {r.text[:300]}')

# Test PDF with watermark
print('\n=== Test 3: PDF with text watermark ===')
form_data['output_format'] = 'pdf'
r = requests.post(f'{BASE_URL}/api/documents/generate', headers=headers, data=form_data)
print(f'Status: {r.status_code}')
if r.status_code == 200:
    print(f'Success: {r.json().get("filename")}')
else:
    print(f'Error: {r.text[:300]}')

