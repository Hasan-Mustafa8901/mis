# backend/services/ingestion/excel_parser.py
import pandas as pd
import json
from pathlib import Path


def load_column_config():
    base_path = Path(__file__).resolve().parent.parent.parent
    config_path = base_path / "config" / "column_config.json"
    with open(config_path) as f:
        return json.load(f)


def load_excel(file_path: str):
    df = pd.read_excel(file_path)
    df.columns = df.columns.str.lower().str.strip()
    return df


def normalize_columns(df: pd.DataFrame):
    config = load_column_config()
    mapping = config.get("column_mapping", {})
    df.rename(columns=mapping, inplace=True)
    return df


def classify_columns(df):
    config = load_column_config()

    price_cols = config["price_components"]
    discount_cols = config["discount_components"]
    meta_cols = config["meta_columns"]
    ignore_cols = config.get("ignore_columns", [])

    # Detect unknown columns (very useful for debugging)
    known_cols = set(price_cols + discount_cols + meta_cols + ignore_cols)

    unknown_cols = [col for col in df.columns if col not in known_cols]

    if unknown_cols:
        # add logger here
        print("⚠️ Unknown columns detected:", unknown_cols)

    return price_cols, discount_cols
