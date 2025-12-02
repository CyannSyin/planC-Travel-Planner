# Data Download Scripts / 数据下载脚本

This directory contains scripts to automatically download the required datasets for the PlanC Travel Planner system.

此目录包含用于自动下载 PlanC Travel Planner 系统所需数据集的脚本。

---

## Quick Start / 快速开始

### Download All Data / 下载所有数据

```bash
# Download both Gowalla and OSM POI data for a city
python scripts/download_data.py --city "Manhattan, New York, USA"
```

### Download Separately / 分别下载

```bash
# 1. Download Gowalla check-in data
python scripts/download_gowalla.py

# 2. Download OSM POI data
python scripts/download_osm_pois.py --city "Manhattan, New York, USA"
```

---

## Scripts Overview / 脚本概览

### `download_data.py` - Main Download Script / 主下载脚本

Downloads all required datasets in one command.

一键下载所有必需的数据集。

**Usage / 使用：**

```bash
# Download all data for a city
python scripts/download_data.py --city "Paris, France"

# Download all data using bounding box
python scripts/download_data.py --bbox 48.9 48.8 2.4 2.2

# Download only Gowalla
python scripts/download_data.py --skip-osm

# Download only OSM POIs
python scripts/download_data.py --skip-gowalla --city "Tokyo, Japan"
```

**Options / 选项：**

- `--city CITY_NAME` - City name for OSM POI download (e.g., "Manhattan, New York, USA")
- `--bbox NORTH SOUTH EAST WEST` - Bounding box for OSM POI download (latitude/longitude)
- `--osm-method {osmnx,overpass}` - OSM download method (default: osmnx)
- `--skip-gowalla` - Skip Gowalla data download
- `--skip-osm` - Skip OSM POI data download
- `--data-dir PATH` - Custom data directory (default: `data/`)

---

### `download_gowalla.py` - Gowalla Dataset Downloader

Downloads the Gowalla check-in dataset from Stanford SNAP.

从 Stanford SNAP 下载 Gowalla 签到数据集。

**Usage / 使用：**

```bash
# Default: download to data/ directory
python scripts/download_gowalla.py

# Custom data directory
python scripts/download_gowalla.py --data-dir /path/to/data

# Keep compressed file after extraction
python scripts/download_gowalla.py --keep-gzip
```

**Features / 特性：**

- Automatic download from Stanford SNAP
- Progress bar during download
- Automatic extraction of `.gz` file
- Skips re-download if file already exists

---

### `download_osm_pois.py` - OSM POI Downloader

Downloads Points of Interest from OpenStreetMap.

从 OpenStreetMap 下载景点（POI）数据。

**Usage / 使用：**

**Method 1: Using City Name (OSMnx) / 方法 1：使用城市名称**

```bash
python scripts/download_osm_pois.py --city "Manhattan, New York, USA" --method osmnx
```

**Note:** Requires `osmnx` package. Install with:
**注意：** 需要 `osmnx` 包。安装方法：

```bash
pip install osmnx
```

**Method 2: Using Bounding Box (Overpass API) / 方法 2：使用边界框**

```bash
python scripts/download_osm_pois.py --bbox 40.8 40.7 -73.9 -74.0 --method overpass
```

**Options / 选项：**

- `--city CITY_NAME` - City name (for OSMnx method)
- `--bbox NORTH SOUTH EAST WEST` - Bounding box coordinates
- `--method {osmnx,overpass}` - Download method (default: osmnx)
- `--output PATH` - Output CSV path (default: `data/city_pois.csv`)

**Supported POI Categories / 支持的 POI 类别：**

- Tourism: attractions, museums, galleries, theme parks, zoos, viewpoints, monuments
- Amenity: restaurants, cafes, bars, pubs, theatres, cinemas
- Historic: castles, ruins, archaeological sites
- Leisure: parks, gardens, beaches, stadiums
- Shopping: malls, marketplaces

---

## Examples / 示例

### Example 1: Download Data for New York City / 示例 1：下载纽约市数据

```bash
# Download all data
python scripts/download_data.py --city "Manhattan, New York, USA"

# This will:
# 1. Download Gowalla_totalCheckins.txt to data/
# 2. Download OSM POIs for Manhattan to data/city_pois.csv
```

### Example 2: Download Data for Multiple Cities / 示例 2：下载多个城市数据

```bash
# Download POIs for Paris
python scripts/download_osm_pois.py --city "Paris, France" --output data/paris_pois.csv

# Download POIs for Tokyo
python scripts/download_osm_pois.py --city "Tokyo, Japan" --output data/tokyo_pois.csv
```

### Example 3: Use Custom Bounding Box / 示例 3：使用自定义边界框

```bash
# Download POIs within a specific bounding box
# Format: --bbox NORTH SOUTH EAST WEST
python scripts/download_osm_pois.py \
  --bbox 40.8 40.7 -73.9 -74.0 \
  --method overpass \
  --output data/nyc_custom_pois.csv
```

### Example 4: Download Only Gowalla Data / 示例 4：只下载 Gowalla 数据

```bash
python scripts/download_gowalla.py
```

---

## Troubleshooting / 故障排除

### Issue: OSMnx Import Error

**Error:** `ImportError: osmnx not installed`

**Solution:** Install osmnx:

```bash
pip install osmnx
```

Or use the Overpass API method instead:

```bash
python scripts/download_osm_pois.py --bbox ... --method overpass
```

### Issue: Download Timeout

**Error:** `TimeoutError` or `ConnectionError`

**Solution:**
- Check your internet connection
- Try again later (servers may be busy)
- For Overpass API, increase timeout in the script if needed

### Issue: No POIs Found

**Solution:**
- Verify the city name is correct (try with country: "City, Country")
- Check the bounding box coordinates are correct
- Try a different method (osmnx vs overpass)
- Expand the search area (larger bounding box)

### Issue: File Already Exists

**Solution:**
- Scripts will ask if you want to re-download
- Delete the existing file manually if you want a fresh download
- Use `--skip-gowalla` or `--skip-osm` flags to skip specific downloads

---

## Data Format / 数据格式

### Gowalla Data Format / Gowalla 数据格式

After download, the file `data/Gowalla_totalCheckins.txt` should contain:
下载后，文件 `data/Gowalla_totalCheckins.txt` 应包含：

```
user_id	timestamp	latitude	longitude	location_id
0	2010-07-24T13:45:06Z	30.285648	-97.741760	145064
```

### OSM POI Data Format / OSM POI 数据格式

The downloaded CSV `data/city_pois.csv` will have these columns:
下载的 CSV `data/city_pois.csv` 将包含以下列：

- `poi_id` - Unique POI identifier
- `lat` - Latitude
- `lon` - Longitude
- `category` - POI category (e.g., "tourism=museum")
- `rating` - Rating (3.5-5.0, synthetic)
- `duration_min` - Estimated visit duration in minutes
- `popularity` - Popularity score (0.0-1.0, can be updated later)
- `name` - POI name
- `opening_hours` - Opening hours string

---

## Next Steps / 下一步

After downloading the data:

下载数据后：

1. **Verify data files** are in the `data/` directory
   验证数据文件是否在 `data/` 目录中

2. **Check data quality** - open the CSV files and verify they look correct
   检查数据质量 - 打开 CSV 文件并验证其是否正确

3. **Run experiments**:
   运行实验：

```bash
python -m planner.experiments
```

---

For more information, see the main [README.md](../README.md).

更多信息，请参阅主 [README.md](../README.md)。

