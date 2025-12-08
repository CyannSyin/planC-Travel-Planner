"""
Utility script to clean OSM POI CSV by removing rows with Unknown values.

数据清洗脚本：
- 从 city_pois.csv 中删除 name 为 "Unknown"（大小写不敏感）的行
- 默认读取 data/city_pois.csv，输出到 data/city_pois_clean.csv

Usage / 用法:
    python scripts/clean_city_pois.py
    python scripts/clean_city_pois.py --input data/my_pois.csv --output data/my_pois_clean.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def clean_city_pois(input_path: Path, output_path: Path) -> None:
    """Load a POI CSV, drop rows whose name is 'Unknown', and save to output.

    读取 POI CSV，删除 name 等于 'Unknown'（忽略大小写）的行，并保存到新文件。
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    df = pd.read_csv(input_path)

    if "name" not in df.columns:
        raise ValueError(
            f"Input file {input_path} does not contain a 'name' column; "
            "cannot filter Unknown names."
        )

    original_count = len(df)

    # Drop rows where name is 'Unknown' (case-insensitive) or empty / NaN
    mask_unknown = df["name"].astype(str).str.strip().str.lower().isin(
        ["unknown", "", "nan"]
    )
    df_clean = df[~mask_unknown].copy()
    cleaned_count = len(df_clean)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_clean.to_csv(output_path, index=False)

    print(f"Input file:  {input_path}")
    print(f"Output file: {output_path}")
    print(f"Total rows:      {original_count}")
    print(f"Removed Unknown: {original_count - cleaned_count}")
    print(f"Remaining rows:  {cleaned_count}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Clean POI CSV by removing rows whose name is 'Unknown' "
            "(case-insensitive). / "
            "从 POI CSV 中删除 name 为 'Unknown' 的行。"
        )
    )
    parser.add_argument(
        "--input",
        type=str,
        default="data/city_pois.csv",
        help="Input POI CSV file path (default: data/city_pois.csv)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/city_pois_clean.csv",
        help="Output cleaned CSV file path (default: data/city_pois_clean.csv)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    in_path = Path(args.input)
    out_path = Path(args.output)
    clean_city_pois(in_path, out_path)


