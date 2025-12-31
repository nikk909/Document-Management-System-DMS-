# Functionality Guide

## 1. Template Management

### Multi-Format Support
Upload templates in `.docx`, `.html`, or `.pdf` (internally treated as HTML).

### Version Control
- **Automatic Increment**: Every upload of an existing template name increments the version.
- **Rollback**: One-click rollback to any previous version.
- **Cross-Format Linking**: Templates with the same name are linked across different formats (e.g., a "Invoice" Word template and an "Invoice" HTML template).

**Implementation Status**: ⚠️ Backend fully supports version history (MinIO versioning + MySQL metadata), but frontend UI for version listing and rollback is not yet completed.

## 2. Document Generation

### Data Sources
- **JSON**: Support for nested structures and arrays.
- **CSV**: Automatic table detection and chart generation.

### Dynamic Elements
- **Tables**: Automatic rendering of data lists into formatted tables.
- **Charts**: Automatic generation of Line and Bar charts from numerical CSV data.
- **Images**: Insert images using base64, MinIO ID, or URL.

### Security Options
- **Data Masking**: ✅ **Fully Implemented** - Automatically redacts ID cards, phones, emails, bank cards, and names. The backend `DataMasker` module supports automatic detection and masking of sensitive fields without requiring manual field selection in the frontend.
- **Watermarking**: ✅ **Fully Implemented**
  - Text: Customizable text at 45-degree angle.
    - Word: VML background watermark (semi-transparent, doesn't interfere with text)
    - PDF: ReportLab-generated watermark layer
    - HTML: CSS background watermark
  - Image: Choice of background images from the Image Gallery.
- **Encryption**: ✅ **Fully Implemented**
  - PDF: Password protection using PyPDF2.
  - Word: Restrict editing to read-only mode via XML document protection.

## 3. Access Control (Blacklisting)

### Configuration
Administrators can blacklist specific users or departments from accessing individual generated documents.

### Enforcement
- **Download Check**: Prevent unauthorized downloads with a "You are not authorized" message.
- **Delete Check**: Prevent unauthorized deletions.
- **UI Visibility**: Blocked users don't see restricted actions.

## 4. Examples

### Jinja2 Example (Word/HTML)
```jinja2
Hello {{ name }},
Your sales for {{ month }} are:
{{ table:sales_data }}
```

### Automatic Masking Example
Input: `110101199001011234`
Output: `XXX01199001011XXXX`

