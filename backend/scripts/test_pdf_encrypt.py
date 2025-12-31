# -*- coding: utf-8 -*-
import requests

BASE_URL = 'http://localhost:8000'

# Login
response = requests.post(f'{BASE_URL}/api/auth/login', json={'username': 'admin', 'password': 'admin'})
token = response.json().get('token')
headers = {'Authorization': f'Bearer {token}'}
print('Login: OK')

# Generate PDF with encryption
form_data = {
    'template_id': 34,  # test1 html template (for PDF generation)
    'data_file_id': 33,  # test3.json
    'output_format': 'pdf',
    'enable_masking': 'false',
    'enable_encryption': 'true',
    'pdf_password': 'test123',
    'enable_watermark': 'false',
    'enable_table': 'true',
    'enable_chart': 'true'
}

print('\nGenerating encrypted PDF...')
print(f'  Template: HTML (ID: 34)')
print(f'  Output: PDF')
print(f'  Encryption: enabled')
print(f'  Password: test123')

r = requests.post(f'{BASE_URL}/api/documents/generate', headers=headers, data=form_data)
print(f'\nStatus: {r.status_code}')
if r.status_code == 200:
    result = r.json()
    print(f'Success: {result.get("success")}')
    print(f'Document ID: {result.get("document_id")}')
    print(f'Filename: {result.get("filename")}')
else:
    try:
        error = r.json()
        print(f'Error detail: {error.get("detail", "Unknown")}')
        if error.get('error_log'):
            print(f'Error log: {error.get("error_log")[:500]}')
        if error.get('metadata'):
            print(f'Metadata: {error.get("metadata")}')
    except:
        print(f'Error: {r.text[:500]}')

