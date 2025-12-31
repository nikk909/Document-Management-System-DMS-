# System Architecture

## Overview

The Document Management System (DMS) follows a classic client-server architecture with a clear separation between the presentation layer, the application logic layer, and the data storage layer.

## Frontend Architecture

- **Core**: Vanilla JavaScript (ES6+), HTML5, and CSS3.
- **UI Design**: Modern, responsive design using Flexbox and Grid. Custom CSS variables for consistent theming.
- **State Management**: Client-side state managed through global variables and DOM attributes.
- **API Interaction**: RESTful API calls using the `fetch` API.
- **Features**:
  - Dynamic tab navigation.
  - Real-time progress bars for document generation.
  - Integrated file and template previewers.
  - Dynamic form building for permission management.

## Backend Architecture

- **Framework**: FastAPI (Asynchronous Python).
- **ORM**: SQLAlchemy 2.0 for relational data mapping.
- **Authentication**: JWT (JSON Web Tokens) with HTTP Bearer scheme. Role-based access control (Admin/User).
- **Core Modules**:
  - `StorageManager`: Abstracted interface for MinIO and MySQL synchronization.
  - `DocumentExporter`: Unified entry point for generating documents across all supported formats.
  - `DataMasker`: Rule-based and pattern-based PII redaction engine.
  - `AccessLogger`: Synchronous and asynchronous logging of system activities.
  - `TemplateManager`: Version-aware template retrieval and storage.

## Data Layer

- **Metadata (MySQL)**:
  - `users`: User credentials and roles.
  - `documents`: Raw data files and uploaded assets.
  - `templates`: Jinja2 templates with version history.
  - `generated_documents`: Audit trail and metadata for generated output.
  - `access_logs`: Detailed activity logs.
- **Storage (MinIO)**:
  - Files are organized into buckets based on categories (e.g., `images`, `templates`, `uncategorized`).
  - Path format: `{category}/{year}/{month}/{day}/{filename}`.
  - Built-in versioning support for templates.

## Workflow: Document Generation

1. **Upload/Select Data**: User provides a JSON or CSV file.
2. **Select Template**: User chooses a compatible Word or HTML template.
3. **Configuration**: User sets security options (watermark, masking, encryption).
4. **Processing**:
   - Backend parses data via `DataProcessor`.
   - `DataMasker` redacts sensitive fields if enabled.
   - `DocumentExporter` renders the template using Jinja2.
   - Specific exporters (Word/PDF/HTML) apply final formatting and security.
5. **Storage**: Final document is saved to MinIO, and metadata is recorded in MySQL.
6. **Delivery**: User downloads the result via a secure, permission-checked link.

