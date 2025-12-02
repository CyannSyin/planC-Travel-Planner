"""
Download POIs from OpenStreetMap using OSMnx or Overpass API.

从 OpenStreetMap 下载景点（POI）数据。
支持两种方法：
1. OSMnx（推荐）- 使用城市名称或边界框
2. Overpass API - 使用自定义查询
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import overpy

try:
    import osmnx as ox
    HAS_OSMNX = True
except ImportError:
    HAS_OSMNX = False
    print("Warning: osmnx not installed. Install with: pip install osmnx")


# Default POI tags to extract from OSM
DEFAULT_POI_TAGS = {
    'tourism': [
        'attraction', 'museum', 'gallery', 'theme_park', 'zoo', 'aquarium',
        'viewpoint', 'monument', 'memorial', 'artwork'
    ],
    'amenity': [
        'restaurant', 'cafe', 'bar', 'pub', 'fast_food', 'food_court',
        'theatre', 'cinema', 'nightclub', 'library'
    ],
    'historic': [
        'castle', 'ruins', 'archaeological_site', 'tomb', 'fort'
    ],
    'leisure': [
        'park', 'garden', 'beach_resort', 'stadium', 'sports_centre'
    ],
    'shop': [
        'mall', 'marketplace'
    ]
}


def estimate_duration_min(category: str, name: str = "") -> float:
    """Estimate visit duration based on POI category.
    
    Args:
        category: POI category tag
        name: POI name (optional)
    
    Returns:
        Estimated duration in minutes
    """
    category_lower = category.lower()
    
    # Museums and galleries
    if 'museum' in category_lower or 'gallery' in category_lower:
        return 120.0  # 2 hours
    
    # Restaurants and cafes
    if 'restaurant' in category_lower or 'cafe' in category_lower:
        return 60.0  # 1 hour
    
    # Attractions and theme parks
    if 'theme_park' in category_lower or 'attraction' in category_lower:
        return 180.0  # 3 hours
    
    # Parks and gardens
    if 'park' in category_lower or 'garden' in category_lower:
        return 90.0  # 1.5 hours
    
    # Viewpoints and monuments
    if 'viewpoint' in category_lower or 'monument' in category_lower:
        return 30.0  # 30 minutes
    
    # Default
    return 60.0


def estimate_rating() -> float:
    """Generate a synthetic rating (in real scenario, use real review data).
    
    Returns:
        Random rating between 3.5 and 5.0
    """
    import random
    return round(random.uniform(3.5, 5.0), 1)


def download_osm_pois_osmnx(
    city_name: Optional[str] = None,
    bbox: Optional[Tuple[float, float, float, float]] = None,
    tags: Optional[Dict] = None,
    output_path: Optional[Path] = None
) -> pd.DataFrame:
    """Download POIs using OSMnx (recommended method).
    
    Args:
        city_name: City name (e.g., "Manhattan, New York, USA")
        bbox: Bounding box (north, south, east, west)
        tags: OSM tags to filter (default: DEFAULT_POI_TAGS)
        output_path: Path to save CSV (optional)
    
    Returns:
        DataFrame with POI data
    """
    if not HAS_OSMNX:
        raise ImportError(
            "osmnx is required. Install with: pip install osmnx"
        )
    
    if tags is None:
        tags = DEFAULT_POI_TAGS
    
    print(f"Downloading OSM POIs using OSMnx...")
    
    if city_name:
        print(f"  City: {city_name}")
        gdf = ox.geometries_from_place(city_name, tags=tags)
    elif bbox:
        north, south, east, west = bbox
        print(f"  Bounding box: ({north}, {south}, {east}, {west})")
        gdf = ox.geometries_from_bbox(north, south, east, west, tags=tags)
    else:
        raise ValueError("Either city_name or bbox must be provided")
    
    print(f"  Found {len(gdf)} POIs")
    
    # Convert to DataFrame with required columns
    pois = []
    for idx, row in gdf.iterrows():
        # Extract coordinates
        if hasattr(row.geometry, 'centroid'):
            lon, lat = row.geometry.centroid.x, row.geometry.centroid.y
        elif hasattr(row.geometry, 'x'):
            lon, lat = row.geometry.x, row.geometry.y
        else:
            continue
        
        # Extract category
        category_parts = []
        for key, value in row.items():
            if key in DEFAULT_POI_TAGS and pd.notna(value):
                category_parts.append(f"{key}={value}")
        
        if not category_parts:
            continue
        
        category = ", ".join(category_parts[:2])  # Take first 2 categories
        
        # Extract name
        name = row.get('name', 'Unknown')
        if pd.isna(name):
            name = 'Unknown'
        
        # Extract opening hours
        opening_hours = row.get('opening_hours', '')
        if pd.isna(opening_hours):
            opening_hours = ''
        
        # Estimate duration and rating
        duration_min = estimate_duration_min(category, name)
        rating = estimate_rating()
        popularity = 0.0  # Can be derived from check-ins later
        
        pois.append({
            'poi_id': str(idx),
            'lat': lat,
            'lon': lon,
            'category': category,
            'rating': rating,
            'duration_min': duration_min,
            'popularity': popularity,
            'name': name,
            'opening_hours': opening_hours
        })
    
    df = pd.DataFrame(pois)
    
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        print(f"✓ Saved {len(df)} POIs to {output_path}")
    
    return df


def download_osm_pois_overpass(
    bbox: Tuple[float, float, float, float],
    tags: Optional[List[str]] = None,
    output_path: Optional[Path] = None,
    timeout: int = 60
) -> pd.DataFrame:
    """Download POIs using Overpass API.
    
    Args:
        bbox: Bounding box (north, south, east, west)
        tags: List of OSM key=value tags to query
        output_path: Path to save CSV (optional)
        timeout: Request timeout in seconds
    
    Returns:
        DataFrame with POI data
    """
    if tags is None:
        # Default tags
        tags = [
            'tourism=*',
            'amenity=restaurant',
            'amenity=cafe',
            'amenity=bar',
            'historic=*',
            'leisure=park'
        ]
    
    north, south, east, west = bbox
    
    print(f"Downloading OSM POIs using Overpass API...")
    print(f"  Bounding box: ({north}, {south}, {east}, {west})")
    
    # Build Overpass query
    tag_conditions = " or ".join([f'"{tag}"' for tag in tags])
    query = f"""
    [out:json][timeout:{timeout}];
    (
      node[{tag_conditions}]({south},{west},{north},{east});
      way[{tag_conditions}]({south},{west},{north},{east});
      relation[{tag_conditions}]({south},{west},{north},{east});
    );
    out center;
    """
    
    api = overpy.Overpass()
    print("  Sending query to Overpass API...")
    
    try:
        result = api.query(query)
        print(f"  Found {len(result.nodes) + len(result.ways)} POIs")
    except Exception as e:
        print(f"  Error querying Overpass API: {e}")
        raise
    
    # Convert to DataFrame
    pois = []
    
    # Process nodes
    for node in result.nodes:
        tags_dict = node.tags
        
        # Extract category
        category_parts = []
        for key in ['tourism', 'amenity', 'historic', 'leisure']:
            if key in tags_dict:
                category_parts.append(f"{key}={tags_dict[key]}")
        
        if not category_parts:
            continue
        
        category = ", ".join(category_parts[:2])
        name = tags_dict.get('name', 'Unknown')
        opening_hours = tags_dict.get('opening_hours', '')
        
        pois.append({
            'poi_id': f"node_{node.id}",
            'lat': float(node.lat),
            'lon': float(node.lon),
            'category': category,
            'rating': estimate_rating(),
            'duration_min': estimate_duration_min(category, name),
            'popularity': 0.0,
            'name': name,
            'opening_hours': opening_hours
        })
    
    # Process ways (use center point)
    for way in result.ways:
        if not way.center_lat or not way.center_lon:
            continue
        
        tags_dict = way.tags
        
        category_parts = []
        for key in ['tourism', 'amenity', 'historic', 'leisure']:
            if key in tags_dict:
                category_parts.append(f"{key}={tags_dict[key]}")
        
        if not category_parts:
            continue
        
        category = ", ".join(category_parts[:2])
        name = tags_dict.get('name', 'Unknown')
        opening_hours = tags_dict.get('opening_hours', '')
        
        pois.append({
            'poi_id': f"way_{way.id}",
            'lat': float(way.center_lat),
            'lon': float(way.center_lon),
            'category': category,
            'rating': estimate_rating(),
            'duration_min': estimate_duration_min(category, name),
            'popularity': 0.0,
            'name': name,
            'opening_hours': opening_hours
        })
    
    df = pd.DataFrame(pois)
    
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        print(f"✓ Saved {len(df)} POIs to {output_path}")
    
    return df


def download_osm_pois(
    city_name: Optional[str] = None,
    bbox: Optional[Tuple[float, float, float, float]] = None,
    method: str = "osmnx",
    output_path: Optional[Path] = None,
    **kwargs
) -> pd.DataFrame:
    """Main function to download OSM POIs.
    
    Args:
        city_name: City name for OSMnx method
        bbox: Bounding box (north, south, east, west)
        method: "osmnx" or "overpass"
        output_path: Path to save CSV
        **kwargs: Additional arguments passed to download functions
    
    Returns:
        DataFrame with POI data
    """
    if output_path is None:
        project_root = Path(__file__).parent.parent
        output_path = project_root / "data" / "city_pois.csv"
    
    output_path = Path(output_path)
    
    # Check if already exists
    if output_path.exists():
        print(f"OSM POI data already exists at {output_path}")
        response = input("Re-download? (y/N): ").strip().lower()
        if response != 'y':
            return pd.read_csv(output_path)
    
    if method == "osmnx":
        return download_osm_pois_osmnx(
            city_name=city_name,
            bbox=bbox,
            output_path=output_path,
            **kwargs
        )
    elif method == "overpass":
        if bbox is None:
            raise ValueError("bbox is required for Overpass method")
        return download_osm_pois_overpass(
            bbox=bbox,
            output_path=output_path,
            **kwargs
        )
    else:
        raise ValueError(f"Unknown method: {method}. Use 'osmnx' or 'overpass'")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Download POIs from OpenStreetMap"
    )
    parser.add_argument(
        "--city",
        type=str,
        default=None,
        help="City name (e.g., 'Manhattan, New York, USA') - for OSMnx method"
    )
    parser.add_argument(
        "--bbox",
        type=float,
        nargs=4,
        metavar=("NORTH", "SOUTH", "EAST", "WEST"),
        default=None,
        help="Bounding box: north south east west (latitude/longitude)"
    )
    parser.add_argument(
        "--method",
        type=str,
        choices=["osmnx", "overpass"],
        default="osmnx",
        help="Download method: osmnx (recommended) or overpass"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output CSV path (default: data/city_pois.csv)"
    )
    
    args = parser.parse_args()
    
    if args.city is None and args.bbox is None:
        parser.error("Either --city or --bbox must be provided")
    
    download_osm_pois(
        city_name=args.city,
        bbox=tuple(args.bbox) if args.bbox else None,
        method=args.method,
        output_path=Path(args.output) if args.output else None
    )

