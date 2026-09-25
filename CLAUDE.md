# CLAUDE.md - CHUN KING System Architecture & Developer Guide

This document provides essential context, architecture details, commands, and operational rules for AI assistants (such as Claude Code) working on this repository.

---

## 1. Project Overview

**CHUN KING** is an integrated business operations and financial management system built for SharePoint Online. It bridges a modern single-page web application (SPA) with SharePoint Online lists, libraries, and automated backup pipelines.

### Key Components:
1. **Core SPA (`smart_forms_app.html`)**: Single-file web app (vanilla HTML/CSS/JS, zero build steps, ~517 KB) containing:
   - Expense Allocation (Multi-project split, cheque sequence auto-generation for prefixes `CK`, `WS`, `CHQ`, `DBS`, `TEST`, receipt rename/upload, and paid/unpaid status).
   - Income Records (Auto-numbering `INC-00xxxx`, bank association, receipt filing).
   - Transaction Editor (Full server-side CAML search without 5,000 threshold truncation, batch multi-project allocation view & edit, batch voiding with cost rollback).
   - Project Management & Remarks (Contract value, VO changes, cumulative costs/income tracking).
   - Financial Dashboard (`#dashboard` tab - live project financial analytics & charts).
2. **Local Development Proxy (`server.py`)**: A Python HTTP server (`http://localhost:8080`) that serves local files and reverse-proxies SharePoint REST API requests using credentials in `cookies.json`.
3. **Automated SharePoint Deployment (`deploy_app_to_sharepoint.py`)**: Python script that publishes `smart_forms_app.html` directly to SharePoint Online `SiteAssets`.
4. **Browser Communication Bridge (`chrome-extension/` & `sharepoint-bridge.user.js`)**: Manifest V3 extension and Tampermonkey script that bridge parent window routing (hash changes) and proxy cross-origin fetch requests across the SharePoint `iframe`.
5. **Weekly Backup Pipeline (`backup/` & `.github/workflows/weekly_backup.yml`)**: Automated export of SharePoint lists (Projects, Transactions, Income) to Excel/CSV and incremental synchronization of all receipt PDFs/images to Google Drive via Google Service Account.

---

## 2. Environment & Quick Start Commands

### Prerequisites
- **OS**: Windows (PowerShell shell environment).
- **Python**: 3.8+ with `requests`, `openpyxl`, `google-api-python-client`, `google-auth`.

### Common Commands
* **Start Local Dev Server**:
  ```powershell
  python server.py
  # Or double click: start_app.bat
  # Serves at: http://localhost:8080/smart_forms_app.html
  ```
* **Deploy Frontend to SharePoint**:
  ```powershell
  python deploy_app_to_sharepoint.py
  ```
* **Run Local Backup to Google Drive**:
  ```powershell
  cd backup
  python backup_sharepoint_to_gdrive.py
  ```

---

## 3. SharePoint Deployment & Hosting Architecture

### Target URLs on SharePoint
The site URL is `https://k35n.sharepoint.com/sites/CHUNKING`.

`deploy_app_to_sharepoint.py` performs a **dual-deployment**:
1. **`/sites/CHUNKING/SiteAssets/forms/app.html`**:
   - This is the **primary production entry point**.
   - All Quick Links on `Home.aspx` and the iframe embed page (`CHUN-KING-業務智慧表單中心(1).aspx`) link to this URL with route hashes (e.g., `#expense`, `#income`, `#dashboard`).
   - *Note*: `/Forms` is a SharePoint reserved system directory and is hidden from the web UI file browser.
2. **`/sites/CHUNKING/SiteAssets/app/app.html` & `smart_forms_app.html`**:
   - Visible folder created so users can browse, view, and inspect source files directly in the SharePoint **「網站資產」 (Site Assets)** web interface.

> [!IMPORTANT]
> `app.html` and `smart_forms_app.html` are exact identical byte-for-byte copies of [`smart_forms_app.html`](file:///c:/Users/kmk112/Downloads/mitigation/smart_forms_app.html). Always make your code changes in `smart_forms_app.html` and use `python deploy_app_to_sharepoint.py` to push to SharePoint.

---

## 4. SharePoint Data Model & OData Gotchas

Always consult [`SHAREPOINT_GUID_MAPPING.md`](file:///c:/Users/kmk112/Downloads/mitigation/SHAREPOINT_GUID_MAPPING.md) for precise field internal names.

### Key Lists & GUIDs
| List Name | Key Internal Purpose | GUID |
| :--- | :--- | :--- |
| **Projects** | Project master, contract value, costs | `1958fe5e-336d-43a0-beb2-4da48df59f7b` |
| **Transactions** | Expense payments & cheque allocations | `a09172c2-2be4-4b12-8dfd-418a6fbe0c6d` |
| **交易記錄-收入** | Customer income payments & bank receipts | `527698fd-139d-4482-b819-b3f6da4e8794` |
| **DocLib** | Document library for cheque/income receipts | Root `/sites/CHUNKING/DocLib` |

### Critical Rules for SharePoint API Calls:
1. **OData Unicode Hex Encoding**:
   SharePoint encodes non-ASCII (Traditional Chinese) column names into `_xHHHH_`. When using verbose JSON, fields starting with an underscore are prefixed with `OData_`.
   - Example: `項目編號` $\rightarrow$ `OData__x9805__x76ee__x7de8__x865f_`.
2. **Lookup Columns Require `_Id`**:
   When writing/updating a lookup field (e.g. associating an expense to a Project), use the ID column:
   - `OData__x6240__x5c6c__x9805__x76ee_Id: <project_id>`
3. **Handling HTTP 429 Rate Limiting (Throttling)**:
   SharePoint Online aggressively throttles REST API requests. Any script communicating with SharePoint must include retry loops with exponential backoff and jitter upon receiving status code `429` or `503`.
4. **FormDigestValue Requirement**:
   All POST, PUT, DELETE, and upload operations require obtaining a valid `FormDigestValue` from `/_api/contextinfo` and sending it in the `X-RequestDigest` HTTP header.
5. **CAML Query 5,000 Threshold**:
   Large lists exceed the 5,000-item view limit. Avoid unindexed `<OrderBy>` tags in CAML queries. Filter by indexed fields (like `ID` or indexed date) to prevent query throttling.

---

## 5. Directory Structure & Key Files

```text
mitigation/
├── smart_forms_app.html            # Main SPA frontend (Expense, Income, Projects, Editor, Dashboard)
├── server.py                       # Local proxy dev server (forwards API calls using cookies.json)
├── start_app.bat                   # Windows batch launcher for server.py
├── deploy_app_to_sharepoint.py     # Production deploy script to SharePoint SiteAssets
├── sharepoint-bridge.user.js       # Tampermonkey bridge script
├── cookies.json                    # Active SharePoint Online user session cookies
├── SHAREPOINT_GUID_MAPPING.md      # Field mapping dictionary (Chinese <-> Hex internal names)
├── README.md                       # Comprehensive system documentation
├── CLAUDE.md                       # AI developer guide (this file)
│
├── chrome-extension/               # Chrome Extension (Manifest V3) for iframe auto-bridge
│   ├── manifest.json
│   ├── content.js
│   └── 使用說明.txt
│
├── backup/                         # SharePoint to Google Drive weekly backup engine
│   ├── backup_sharepoint_to_gdrive.py # Main backup runner
│   ├── sharepoint_client.py        # Resilient SharePoint API client
│   ├── gdrive_client.py            # Google Drive API client (resumable uploads, manifests)
│   ├── service_account.json        # Google Cloud service account key (local testing)
│   └── requirements.txt            # Python dependencies for backup
│
├── .github/workflows/
│   └── weekly_backup.yml           # GitHub Actions weekly Sunday 03:00 HKT backup cron
│
└── _archive/                       # Historical scripts, past migrations & audit logs (DO NOT EDIT)
```

---

## 6. Development & Modification Rules

1. **Maintain SPA Simplicity**:
   Do NOT introduce complex front-end frameworks (React/Vue/Webpack/Tailwind) unless explicitly instructed. Keep [`smart_forms_app.html`](file:///c:/Users/kmk112/Downloads/mitigation/smart_forms_app.html) self-contained with standard CSS/JS so it can run immediately in any browser or SharePoint iframe without bundling.
2. **Do Not Touch `_archive/`**:
   Files in `_archive/` are historical logs, data migration checkpoints, and superseded scripts. They must not be modified or imported into production flows.
3. **Session Credentials in `cookies.json`**:
   `cookies.json` stores live session cookies. If API calls return `401 Unauthorized` or redirect to login pages, prompt the user to refresh `cookies.json` from their browser's developer tools.
4. **Preserve Compatibility**:
   When updating `deploy_app_to_sharepoint.py`, always ensure both `/SiteAssets/forms/app.html` (for existing Quick Links and web parts) and `/SiteAssets/app/` (for UI visibility) are maintained.
