# -*- coding: utf-8 -*-
import sys
import re

# Read HTML exporter file
with open('backend/src/exporters/html_exporter.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find export function definition
match = re.search(r'def export\([^)]+\)', content, re.DOTALL)
if match:
    print('HTML File export signature:')
    print(match.group(0))
else:
    print('Not found in file')

# Read PDF exporter file
with open('backend/src/exporters/pdf_exporter.py', 'r', encoding='utf-8') as f:
    content = f.read()

match = re.search(r'def export\([^)]+\)', content, re.DOTALL)
if match:
    print('\nPDF File export signature:')
    print(match.group(0))

