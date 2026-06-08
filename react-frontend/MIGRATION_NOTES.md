# Frontend Conversion Notes

## What has been converted

The Python GUI has been converted into a modular React + HTML + JavaScript + Tailwind CSS frontend under `react-frontend/`.

The backend has not been modified.

## Modular structure

- `src/services/` — API layer for FastAPI endpoints
- `src/context/` — authentication and master-data providers
- `src/components/` — reusable UI components
- `src/pages/` — business screens
- `src/layouts/` — sidebar/header layout
- `src/config/` — navigation and table-column configuration
- `src/lib/` — formatting and storage helpers

## Main screens included

- Login
- Dashboard
- Booking MIS
- Delivery MIS
- Transaction add/edit form
- Daily Reporting
- Complaints Control Panel
- EBD Upload
- Price List Upload
- Settings & Masters

## Backend compatibility

The frontend calls the existing FastAPI endpoints such as:

- `/auth/login`
- `/transactions-pages`
- `/transactions/{id}`
- `/transactions/meta`
- `/report/`
- `/reports/daily`
- `/complaints/`
- `/mis/upload-ebd`
- `/price-list/upload`
- `/dealerships`, `/outlets`, `/variants`, `/sales-executives`

## Performance improvements made at frontend level

- Uses paginated `/transactions-pages` instead of loading all records by default.
- Splits frontend into small reusable files.
- Centralizes API client and authentication token handling.
- Avoids repeated HTTP client creation pattern used in the old Python GUI.
- Loads full transaction detail only when editing/viewing a transaction.

## Notes

Some highly specific legacy Python GUI behaviours may still require final field-level mapping after testing against live production data because the old frontend was very large and contained many dynamic field conventions.
