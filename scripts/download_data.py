"""
Main script to download all required datasets for the PlanC Travel Planner.

下载所有必需的数据集的主脚本。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path to import download scripts
sys.path.insert(0, str(Path(__file__).parent))

from download_gowalla import download_gowalla_data
from download_osm_pois import download_osm_pois


def download_all_data(
    data_dir: Optional[Path] = None,
    city_name: Optional[str] = None,
    bbox: Optional[tuple] = None,
    osm_method: str = "osmnx",
    skip_gowalla: bool = False,
    skip_osm: bool = False
) -> None:
    """Download all required datasets.
    
    Args:
        data_dir: Directory to save data (default: project data/ directory)
        city_name: City name for OSM POI download (e.g., "Manhattan, New York, USA")
        bbox: Bounding box for OSM POI download (north, south, east, west)
        osm_method: OSM download method ("osmnx" or "overpass")
        skip_gowalla: Skip Gowalla download
        skip_osm: Skip OSM POI download
    """
    if data_dir is None:
        project_root = Path(__file__).parent.parent
        data_dir = project_root / "data"
    
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("PlanC Travel Planner - Data Download")
    print("=" * 60)
    print()
    
    # Download Gowalla data
    if not skip_gowalla:
        print("📥 Step 1/2: Downloading Gowalla check-in data...")
        print("-" * 60)
        try:
            gowalla_path = download_gowalla_data(data_dir=data_dir)
            print(f"✓ Gowalla data: {gowalla_path}")
        except Exception as e:
            print(f"✗ Failed to download Gowalla data: {e}")
            print("  You can skip this step with --skip-gowalla")
        print()
    else:
        print("⏭️  Skipping Gowalla download (--skip-gowalla)")
        print()
    
    # Download OSM POI data
    if not skip_osm:
        print("📥 Step 2/2: Downloading OSM POI data...")
        print("-" * 60)
        
        if city_name is None and bbox is None:
            print("⚠️  Warning: No city name or bbox provided for OSM POI download.")
            print("   Please provide one of the following:")
            print("   - --city 'City Name, Country'")
            print("   - --bbox north south east west")
            print()
            print("   Example:")
            print("   --city 'Manhattan, New York, USA'")
            print("   --bbox 40.8 40.7 -73.9 -74.0  # NYC bounding box")
            print()
            skip_osm = True
        
        if not skip_osm:
            try:
                osm_df = download_osm_pois(
                    city_name=city_name,
                    bbox=bbox,
                    method=osm_method,
                    output_path=data_dir / "city_pois.csv"
                )
                print(f"✓ OSM POI data: {data_dir / 'city_pois.csv'}")
                print(f"  Found {len(osm_df)} POIs")
            except Exception as e:
                print(f"✗ Failed to download OSM POI data: {e}")
                print("  You can skip this step with --skip-osm")
        print()
    else:
        print("⏭️  Skipping OSM POI download (--skip-osm)")
        print()
    
    print("=" * 60)
    print("✓ Data download complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Verify data files in:", data_dir)
    print("2. Run experiments: python -m planner.experiments")
    print()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Download all required datasets for PlanC Travel Planner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download both datasets for Manhattan
  python scripts/download_data.py --city "Manhattan, New York, USA"
  
  # Download only Gowalla data
  python scripts/download_data.py --skip-osm
  
  # Download only OSM data using bounding box
  python scripts/download_data.py --skip-gowalla --bbox 40.8 40.7 -73.9 -74.0
  
  # Use Overpass API instead of OSMnx
  python scripts/download_data.py --city "Paris, France" --osm-method overpass
        """
    )
    
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Directory to save data (default: project data/ directory)"
    )
    parser.add_argument(
        "--city",
        type=str,
        default=None,
        help="City name for OSM POI download (e.g., 'Manhattan, New York, USA')"
    )
    parser.add_argument(
        "--bbox",
        type=float,
        nargs=4,
        metavar=("NORTH", "SOUTH", "EAST", "WEST"),
        default=None,
        help="Bounding box for OSM POI download: north south east west"
    )
    parser.add_argument(
        "--osm-method",
        type=str,
        choices=["osmnx", "overpass"],
        default="osmnx",
        help="OSM download method: osmnx (recommended) or overpass"
    )
    parser.add_argument(
        "--skip-gowalla",
        action="store_true",
        help="Skip Gowalla data download"
    )
    parser.add_argument(
        "--skip-osm",
        action="store_true",
        help="Skip OSM POI data download"
    )
    
    args = parser.parse_args()
    
    download_all_data(
        data_dir=Path(args.data_dir) if args.data_dir else None,
        city_name=args.city,
        bbox=tuple(args.bbox) if args.bbox else None,
        osm_method=args.osm_method,
        skip_gowalla=args.skip_gowalla,
        skip_osm=args.skip_osm
    )

