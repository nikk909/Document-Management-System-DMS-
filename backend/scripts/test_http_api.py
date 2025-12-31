# -*- coding: utf-8 -*-
"""
直接HTTP测试API
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def get_token():
    """获取token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        data={"username": "admin", "password": "admin"}
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    return None

def test_categories():
    """测试分类API"""
    token = get_token()
    if not token:
        print("Failed to get token")
        return
    
    print(f"Token obtained: {token[:20]}...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test GET categories
    print("\n1. GET /api/files/categories")
    response = requests.get(f"{BASE_URL}/api/files/categories", headers=headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Categories: {data.get('categories', [])}")
    else:
        print(f"   Error: {response.text}")

def test_generate():
    """测试文档生成"""
    token = get_token()
    if not token:
        print("Failed to get token")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test templates
    print("\n2. GET /api/templates")
    response = requests.get(f"{BASE_URL}/api/templates", headers=headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Templates count: {data.get('total', 0)}")
        templates = data.get('templates', [])
        for t in templates[:3]:
            print(f"     - {t.get('name', 'N/A')} (ID: {t.get('id')})")
    else:
        print(f"   Error: {response.text}")
    
    # Test files
    print("\n3. GET /api/files")
    response = requests.get(f"{BASE_URL}/api/files", headers=headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Files count: {data.get('total', 0)}")
    else:
        print(f"   Error: {response.text}")

if __name__ == '__main__':
    test_categories()
    test_generate()

