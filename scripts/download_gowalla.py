"""
Download Gowalla check-in dataset from Stanford SNAP.

从 Stanford SNAP 数据集下载 Gowalla 签到数据。
"""

from __future__ import annotations

import gzip
import shutil
from pathlib import Path
from typing import Optional

import requests
from tqdm import tqdm


# Gowalla dataset URLs
GOWALLA_URL = "https://snap.stanford.edu/data/loc-gowalla_totalCheckins.txt.gz"
GOWALLA_CHECKINS_FILE = "loc-gowalla_totalCheckins.txt.gz"


def download_file(url: str, output_path: Path, chunk_size: int = 8192) -> None:
    """Download a file with progress bar.
    
    Args:
        url: URL to download from
        output_path: Path to save the file
        chunk_size: Chunk size for streaming download
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Downloading from {url}...")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    total_size = int(response.headers.get('content-length', 0))
    
    with open(output_path, 'wb') as f, tqdm(
        desc=output_path.name,
        total=total_size,
        unit='B',
        unit_scale=True,
        unit_divisor=1024,
    ) as pbar:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
                pbar.update(len(chunk))
    
    print(f"Downloaded to {output_path}")


def extract_gzip(gzip_path: Path, output_path: Path) -> None:
    """Extract a gzipped file.
    
    Args:
        gzip_path: Path to the .gz file
        output_path: Path to save the extracted file
    """
    print(f"Extracting {gzip_path.name}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with gzip.open(gzip_path, 'rb') as f_in:
        with open(output_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    print(f"Extracted to {output_path}")


def download_gowalla_data(
    data_dir: Optional[Path] = None,
    keep_gzip: bool = False
) -> Path:
    """Download and extract Gowalla check-in dataset.
    
    Args:
        data_dir: Directory to save the data (default: project data/ directory)
        keep_gzip: Whether to keep the compressed .gz file after extraction
    
    Returns:
        Path to the extracted Gowalla_totalCheckins.txt file
    """
    if data_dir is None:
        # Assume script is run from project root
        project_root = Path(__file__).parent.parent
        data_dir = project_root / "data"
    
    data_dir = Path(data_dir)
    gzip_path = data_dir / GOWALLA_CHECKINS_FILE
    output_path = data_dir / "Gowalla_totalCheckins.txt"
    
    # Check if already downloaded
    if output_path.exists():
        print(f"Gowalla data already exists at {output_path}")
        response = input("Re-download? (y/N): ").strip().lower()
        if response != 'y':
            return output_path
    
    # Download the compressed file
    if not gzip_path.exists():
        download_file(GOWALLA_URL, gzip_path)
    else:
        print(f"Compressed file already exists at {gzip_path}")
        response = input("Re-download? (y/N): ").strip().lower()
        if response == 'y':
            download_file(GOWALLA_URL, gzip_path)
    
    # Extract the file
    if not output_path.exists():
        extract_gzip(gzip_path, output_path)
    else:
        print(f"Extracted file already exists at {output_path}")
        response = input("Re-extract? (y/N): ").strip().lower()
        if response == 'y':
            extract_gzip(gzip_path, output_path)
    
    # Remove gzip file if not keeping it
    if not keep_gzip and gzip_path.exists():
        gzip_path.unlink()
        print(f"Removed compressed file: {gzip_path}")
    
    print(f"\n✓ Gowalla data ready at: {output_path}")
    print(f"  File size: {output_path.stat().st_size / (1024**2):.2f} MB")
    
    return output_path


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Download Gowalla check-in dataset from Stanford SNAP"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Directory to save data (default: project data/ directory)"
    )
    parser.add_argument(
        "--keep-gzip",
        action="store_true",
        help="Keep the compressed .gz file after extraction"
    )
    
    args = parser.parse_args()
    
    data_dir = Path(args.data_dir) if args.data_dir else None
    download_gowalla_data(data_dir=data_dir, keep_gzip=args.keep_gzip)

