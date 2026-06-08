# React Frontend for Automobile Sales Audit MIS

This frontend replaces the old Python GUI without changing the FastAPI backend.

## Run

```bash
cd react-frontend
npm install
cp .env.example .env
npm run dev
```

Keep the backend running separately on `http://127.0.0.1:8000` or update `VITE_API_BASE_URL`.

## Build

```bash
npm run build
```

The build output is generated in `dist/`.
