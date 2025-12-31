# -*- coding: utf-8 -*-
import requests

BASE_URL = 'http://localhost:8000'

def test_generate():
    # Login
    response = requests.post(f'{BASE_URL}/api/auth/login', json={'username': 'admin', 'password': 'admin'})
    token = response.json().get('token')
    headers = {'Authorization': f'Bearer {token}'}
    print('Login: OK')
    
    # Get files (need data file ID)
    response = requests.get(f'{BASE_URL}/api/files', headers=headers)
    files = response.json().get('files', [])
    data_file_id = None
    for f in files:
        if 'json' in f.get('filename', '').lower():
            data_file_id = f.get('id')
            print(f'Data file: {f.get("filename")} (ID: {data_file_id})')
            break
    
    # Get templates (need template ID)
    response = requests.get(f'{BASE_URL}/api/templates', headers=headers)
    templates = response.json().get('templates', [])
    template_id = None
    for t in templates:
        if t.get('format_type') == 'word':
            template_id = t.get('id')
            print(f'Template: {t.get("name")} (ID: {template_id}, Format: {t.get("format_type")})')
            break
    
    if not data_file_id or not template_id:
        print('Missing data file or template')
        return
    
    # Generate document
    print(f'\nGenerating document...')
    print(f'  data_file_id: {data_file_id}')
    print(f'  template_id: {template_id}')
    print(f'  output_format: word')
    
    form_data = {
        'template_id': template_id,
        'data_file_id': data_file_id,
        'output_format': 'word',
        'enable_masking': 'false',
        'enable_encryption': 'false',
        'enable_watermark': 'false',
        'enable_table': 'true',
        'enable_chart': 'true'
    }
    
    response = requests.post(f'{BASE_URL}/api/documents/generate', headers=headers, data=form_data)
    print(f'\nGenerate Status: {response.status_code}')
    
    if response.status_code == 200:
        result = response.json()
        print(f'Success: {result.get("success")}')
        print(f'Document ID: {result.get("document_id")}')
        print(f'Filename: {result.get("filename")}')
    else:
        try:
            error_data = response.json()
            print(f'Error: {error_data.get("detail", "Unknown")}')
            if error_data.get('error_log'):
                print(f'Error log (first 500 chars): {error_data.get("error_log")[:500]}')
        except:
            print(f'Error: {response.text[:500]}')

if __name__ == '__main__':
    test_generate()

