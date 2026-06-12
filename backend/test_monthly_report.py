# test_monthly_endpoint.py

import requests


BASE_URL = "http://localhost:8000"

response = requests.get(
    f"{BASE_URL}/reports/monthly",
    params={
        "start_date": "2026-05-01",
        "end_date": "2026-05-31",
        "dealership_id": 1,
    },
    timeout=60,
)

print("Status:", response.status_code)

response.raise_for_status()

filename = "monthly_report_test.xlsx"

content_disposition = response.headers.get("Content-Disposition")

if content_disposition and "filename=" in content_disposition:
    filename = content_disposition.split("filename=")[-1].replace('"', "").strip()

with open(filename, "wb") as f:
    f.write(response.content)

print(f"Saved: {filename}")
