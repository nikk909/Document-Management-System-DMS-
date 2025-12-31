# -*- coding: utf-8 -*-
import os

print("Testing WeasyPrint...")

try:
    from weasyprint import HTML
    print("WeasyPrint import successful!")
    
    # Try simple PDF generation
    html_content = '<html><body><h1>Test</h1></body></html>'
    output_file = 'test_output.pdf'
    
    HTML(string=html_content).write_pdf(output_file)
    print("PDF generation successful!")
    
    if os.path.exists(output_file):
        print(f"File size: {os.path.getsize(output_file)} bytes")
        os.remove(output_file)
        print("Cleanup done.")
    
except ImportError as e:
    print(f"Import error: {e}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

