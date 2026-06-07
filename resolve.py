#!/usr/bin/env python3.11
"""
resolve.py — 自驾行程解析器

从 YAML 草稿（地名版）解析、查坐标、算路、校验、缓存，
输出 resolved JSON 供 render.py 使用。

用法:
  python3.11 resolve.py trips/xxx.yaml

输出:
  resolved/xxx.json  （完整 resolved 数据）
  .cache/geocode.json（Geocoding 缓存）
  .cache/osrm/       （OSRM 路线缓存）
"""

import sys
import os
import json
import time
import math
import re
import hashlib
import urllib.request
import urllib.parse
from collections import OrderedDict

import yaml

# ─────────────────────────────────────────────
# 1. Geocoding（Nomatim → 缓存）
# ─────────────────────────────────────────────

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.cache')
GEO_CACHE_PATH = os.path.join(CACHE_DIR, 'geocode.json')
ELEV_CACHE_PATH = os.path.join(CACHE_DIR, 'elevation.json')
OSRM_CACHE_DIR = os.path.join(CACHE_DIR, 'osrm')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESOLVED_DIR = os.path.join(BASE_DIR, 'resolved')

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(OSRM_CACHE_DIR, exist_ok=True)
os.makedirs(RESOLVED_DIR, exist_ok=True)

def load_json_cache(path, default=None):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default or {}

def save_json_cache(path, cache):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

_geo_cache = load_json_cache(GEO_CACHE_PATH)
_elev_cache = load_json_cache(ELEV_CACHE_PATH)

def save_geo_cache():
    save_json_cache(GEO_CACHE_PATH, _geo_cache)

def save_elev_cache():
    save_json_cache(ELEV_CACHE_PATH, _elev_cache)

def geocode(name: str, hint: str = '') -> list[float] | None:
    """查地名坐标，返回 [lat, lng] 或 None
    
    支持 hint 辅助：若 hint 不为空且初次失败，用 name + hint 重试一次。
    即便 name_raw 之前被缓存为 None，有 hint 时仍然重试。
    """
    name_raw = name.strip()
    if name_raw in _geo_cache:
        cached = _geo_cache[name_raw]
        if cached is not None:
            return cached
        # 之前失败过 — 若 hint 为空，维持结论
        if not hint:
            return None
        # 有 hint → 尝试 hint 路径（忽略失败缓存）
    
    # 初次查询: name + 中国
    result = _geocode_query(name_raw + ' 中国', name_raw)
    if result is not None:
        return result
    
    # 有 hint → 重试: name + hint
    if hint:
        hint = hint.strip()
        hinted = f"{name_raw} {hint}"
        if hinted not in _geo_cache:
            result = _geocode_query(hinted, name_raw)
            if result is not None:
                return result
            # Also cache the hinted name to avoid repeat
            _geo_cache[hinted] = None
            save_geo_cache()
    
    print(f"  ⚠ 未找到坐标: {name_raw}" + (f" (尝试 hint: {hint})" if hint else ""))
    _geo_cache[name_raw] = None
    save_geo_cache()
    return None


def _geocode_query(query: str, cache_key: str) -> list[float] | None:
    """向 Nomatim 发起一次查询，缓存结果"""
    url = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({
        'q': query,
        'format': 'json',
        'limit': 1,
    })
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Hermes-RouteMap/1.0',
            'Accept-Language': 'zh-CN',
        })
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read().decode('utf-8'))
        if data and len(data) > 0:
            lat = float(data[0]['lat'])
            lng = float(data[0]['lon'])
            result = [round(lat, 6), round(lng, 6)]
            _geo_cache[cache_key] = result
            save_geo_cache()
            time.sleep(1.1)
            return result
        return None
    except Exception as e:
        print(f"  ⚠ Geocoding 失败 ({query}): {e}")
        return None


# ─────────────────────────────────────────────
# 2. OSRM 算路 + 缓存
# ─────────────────────────────────────────────

OSRM_BASE = 'https://router.project-osrm.org/route/v1/driving/'
_osrm_call_count = 0

def _route_cache_key(start, end, via):
    """生成 OSRM 缓存 key"""
    parts = [f"{start[1]:.4f},{start[0]:.4f}"]
    if via:
        for v in via:
            parts.append(f"{v[1]:.4f},{v[0]:.4f}")
    parts.append(f"{end[1]:.4f},{end[0]:.4f}")
    return hashlib.md5(';'.join(parts).encode()).hexdigest()

def fetch_route(start: list, end: list, via: list | None = None) -> dict:
    """
    获取路线 polyline + 距离 + 时间
    返回: {"polyline": [[lat,lng],...], "distance_km": float, "duration_min": float}
    或 None
    """
    global _osrm_call_count
    
    # start == end → local route, no OSRM needed
    if start[0] == end[0] and start[1] == end[1]:
        print(f"  ✓ 当地行程，直线路径")
        return {
            "polyline": [[start[0], start[1]], [end[0], end[1]]],
            "distance_km": 0,
            "duration_min": 0,
        }
    
    # Check cache
    key = _route_cache_key(start, end, via)
    cache_path = os.path.join(OSRM_CACHE_DIR, f"{key}.json")
    if os.path.exists(cache_path):
        with open(cache_path, 'r') as f:
            cached = json.load(f)
            print(f"  ✓ 缓存命中 ({len(cached['polyline'])} 点)")
            return cached
    
    # Rate limit
    _osrm_call_count += 1
    if _osrm_call_count > 3:
        time.sleep(0.3)
    
    coords = []
    coords.append(f"{start[1]},{start[0]}")
    if via:
        for v in via:
            coords.append(f"{v[1]},{v[0]}")
    coords.append(f"{end[1]},{end[0]}")
    
    url = OSRM_BASE + ';'.join(coords) + '?geometries=geojson&overview=simplified&steps=false'
    print(f"  OSRM: {start} → {end}" + (f" via {via}" if via else ""))
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Hermes-RouteMap/1.0'})
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read().decode('utf-8'))
        if data.get('code') != 'Ok' or not data.get('routes'):
            print(f"  ⚠ OSRM 错误: {data.get('code', 'unknown')}, 直线 fallback")
            return _straight_line(start, end, via)
        route = data['routes'][0]
        coords_raw = route['geometry']['coordinates']
        polyline = [[round(c[1], 6), round(c[0], 6)] for c in coords_raw]
        distance_km = round(route['distance'] / 1000)
        duration_min = round(route['duration'] / 60)
        result = {
            "polyline": polyline,
            "distance_km": distance_km,
            "duration_min": duration_min,
        }
        # Save cache
        with open(cache_path, 'w') as f:
            json.dump(result, f)
        print(f"  ✓ {len(polyline)} 点, {distance_km}km, {duration_min}min")
        return result
    except Exception as e:
        print(f"  ⚠ OSRM 请求失败: {e}")
        return _straight_line(start, end, via)


def _straight_line(start, end, via=None):
    """直线 fallback"""
    pts = [start]
    if via:
        pts.extend(via)
    pts.append(end)
    result = []
    for i in range(len(pts) - 1):
        n = max(2, int(20 / (len(pts) - 1)))
        for j in range(n):
            t = j / n
            lat = pts[i][0] + (pts[i+1][0] - pts[i][0]) * t
            lng = pts[i][1] + (pts[i+1][1] - pts[i][1]) * t
            result.append([round(lat, 6), round(lng, 6)])
    result.append(pts[-1])
    # Estimate distance from straight line (very rough)
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    est_km = round(((dx * 111) ** 2 + (dy * 111 * 0.8) ** 2) ** 0.5)
    return {
        "polyline": result,
        "distance_km": est_km,
        "duration_min": round(est_km * 1.2),  # rough: 1min per km
    }


# ─────────────────────────────────────────────
# 3. 校验规则
# ─────────────────────────────────────────────

SPEED_GRADIENTS = {
    'highway':  (85, 90,   '高速公路/干线'),
    'national': (45, 50,   '国道/省道'),
    'mountain': (20, 30,   '山路/非铺装'),
}

DAILY_CEILING = {
    'single_highway':  600,
    'single_mountain': 300,
    'dual_highway':    700,
    'dual_mountain':   300,
}

def validate_daily(d, day_idx, day_colors, cities_data, city_coords_dict):
    """对单天行程做 6 项校验，返回 warnings 列表"""
    warnings = []
    theme = d.get('theme', '')
    distance_km = d.get('_resolved_distance', 0)
    terrain = d.get('route', {}).get('terrain', 'highway')
    start_coord = d.get('_resolved_start')
    end_coord = d.get('_resolved_end')
    day_type = d.get('day_type', 'transit')
    city = d.get('city', '')
    
    # 3.1 里程天花板
    if terrain == 'mountain':
        ceiling = DAILY_CEILING['single_mountain']
        label = '山路'
    else:
        ceiling = DAILY_CEILING['single_highway']
        label = '平原/高速'
    if distance_km > ceiling:
        warnings.append(f"⚠️ D{d['day']} {theme}: {distance_km}km 超过{label}上限 ({ceiling}km)")
    
    # 3.2 速度梯度校验
    if terrain in SPEED_GRADIENTS:
        low, high, tname = SPEED_GRADIENTS[terrain]
        if distance_km > 0:
            expected_hours = distance_km / high
            if d.get('_resolved_duration', 0) > 0:
                actual_hours = d['_resolved_duration'] / 60
                ratio = actual_hours / expected_hours if expected_hours > 0 else 0
                if ratio > 2.0:
                    warnings.append(f"⏱ D{d['day']} 实际时间({actual_hours:.1f}h)远超{low}-{high}km/h均速预期({expected_hours:.1f}h)")
    
    # 3.3 3:1 时间修正（只是记录在 data 里，不算警告）
    # （在 resolve 中直接乘 1.33 生成 display duration）
    
    # 3.4 高反检测（第一天 > 2500m 或跳跃上升）
    if day_idx >= 0:
        city_elev = None
        if city and city in city_coords_dict:
            city_elev = city_coords_dict[city].get('elevation')
        if city_elev and city_elev > 2500 and day_idx <= 1:
            warnings.append(f"🏔️ D{d['day']} {city} 海拔 {city_elev}m — 第一/二晚超过 2500m 建议，考虑低海拔适应")
        # Check for jumps: previous city elevation
        if day_idx > 0 and city_elev:
            prev_city = d.get('city', '')
            # find previous day's city
            for pd in reversed(cities_data[:day_idx]):
                pc = pd.get('city', '')
                if pc and pc in city_coords_dict:
                    prev_elev = city_coords_dict[pc].get('elevation', 0)
                    if prev_elev > 0 and city_elev - prev_elev > 1000:
                        warnings.append(f"🏔️ D{d['day']} 从 {prev_elev}m 跃升至 {city_elev}m（+{city_elev-prev_elev}m）")
                    break
    
    # 3.5 迎光驾驶检测
    if start_coord and end_coord:
        # Simple direction detection: compare longitudes
        lng_diff = end_coord[1] - start_coord[1]
        if lng_diff > 2:  # Going east
            warnings.append(f"🌅 D{d['day']} 由西向东 — 早晨 07:00-09:00 迎光驾驶，注意遮阳")
        elif lng_diff < -2:  # Going west
            warnings.append(f"🌅 D{d['day']} 由东向西 — 下午 16:00-18:00 迎光驾驶，注意遮阳")
    
    # 3.6 OSRM 异常路线检测（路网缺失导致大绕路）
    if start_coord and end_coord and distance_km > 0:
        lat_avg = math.radians((start_coord[0] + end_coord[0]) / 2)
        dlat = abs(start_coord[0] - end_coord[0]) * 111
        dlng = abs(start_coord[1] - end_coord[1]) * 111 * math.cos(lat_avg)
        straight_km = (dlat ** 2 + dlng ** 2) ** 0.5
        # 两种异常检测：远超直线 或 远超YAML预期里程
        if straight_km > 10 and distance_km / straight_km > 4:
            warnings.append(f"🔄 D{d['day']} {theme}: OSRM路线({distance_km}km)远超直线({straight_km:.0f}km)，路网可能缺失")
        elif distance_km > 0 and straight_km > 10:
            distance_expected = d.get('distance', '')
            if distance_expected:
                nums = re.findall(r'\d+', distance_expected.replace(',', ''))
                if nums and int(nums[0]) > 10 and distance_km / int(nums[0]) > 2:
                    warnings.append(f"🔄 D{d['day']} {theme}: OSRM路线({distance_km}km)是YAML预期({nums[0]}km)的{distance_km//int(nums[0])}倍，路网可能缺失请核对")
    
    return warnings


def validate_route(start_coord, end_coord, via):
    """基础的坐标校验"""
    warnings = []
    # China bounding box
    if not (73 < start_coord[1] < 135 and 18 < start_coord[0] < 54):
        warnings.append(f"📍 起点坐标异常: [{start_coord[0]}, {start_coord[1]}]")
    if not (73 < end_coord[1] < 135 and 18 < end_coord[0] < 54):
        warnings.append(f"📍 终点坐标异常: [{end_coord[0]}, {end_coord[1]}]")
    return warnings


# ─────────────────────────────────────────────
# 4. 海拔查询（Open-Elevation API + 缓存 + 批量）
# ─────────────────────────────────────────────

def fetch_elevation(lat: float, lng: float) -> int | None:
    """查海拔，返回米数（优先缓存）"""
    key = f"{round(lat, 4)},{round(lng, 4)}"
    if key in _elev_cache:
        return _elev_cache.get(key)
    return _batch_elevation([(lat, lng)]).get(key)

def batch_fetch_elevation(coords: list) -> dict:
    """
    批量查海拔，返回 { 'lat,lng': elevation } 字典。
    coords: [(lat, lng), ...]
    跳过已缓存项，仅查未命中项。
    """
    todo = []
    result = {}
    for lat, lng in coords:
        key = f"{round(lat, 4)},{round(lng, 4)}"
        if key in _elev_cache:
            result[key] = _elev_cache[key]
        else:
            result[key] = None  # placeholder
            todo.append((lat, lng, key))
    
    if not todo:
        return result
    
    # Batch uncached
    batch_keys = [t[2] for t in todo]
    batch_coords = [(t[0], t[1]) for t in todo]
    batch_results = _batch_elevation(batch_coords)
    
    for key in batch_keys:
        if key in batch_results:
            _elev_cache[key] = batch_results[key]
        else:
            _elev_cache[key] = None
        result[key] = _elev_cache[key]
    
    save_elev_cache()
    return result

def _batch_elevation(coords: list) -> dict:
    """向 Open-Elevation 发起批量查询，管道分隔"""
    if not coords:
        return {}
    loc_str = '|'.join(f"{lat},{lng}" for lat, lng in coords)
    url = f'https://api.open-elevation.com/api/v1/lookup?locations={loc_str}'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Hermes-RouteMap/1.0'})
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read().decode('utf-8'))
        if data.get('results'):
            result = {}
            for r in data['results']:
                key = f"{round(r['latitude'], 4)},{round(r['longitude'], 4)}"
                result[key] = round(r['elevation'])
            return result
        return {}
    except Exception as e:
        print(f"  ⚠ 批量海拔查询失败: {e}")
        return {}


# ─────────────────────────────────────────────
# 5. 主流程
# ─────────────────────────────────────────────

COLOR_PALETTE = [
    '#e74c3c', '#f39c12', '#27ae60', '#00bcd4', '#3f51b5',
    '#9c27b0', '#e91e63', '#00acc1', '#ff9800', '#795548',
    '#607d8b', '#8bc34a', '#ff5722', '#9e9e9e', '#5c6bc0',
    '#ec407a', '#26a69a', '#d4e157', '#7e57c2', '#ffa726',
    '#ef5350', '#42a5f5', '#ab47bc', '#66bb6a', '#ff7043',
    '#78909c', '#8d6e63', '#bdbdbd', '#f06292', '#4db6ac',
]

def get_day_color(day_index: int, colors_override: dict | None = None) -> str:
    if colors_override:
        key = f'D{day_index + 1}'
        if key in colors_override:
            return colors_override[key]
    if day_index < len(COLOR_PALETTE):
        return COLOR_PALETTE[day_index]
    h = hashlib.md5(str(day_index).encode())
    return '#' + h.hexdigest()[:6]


def resolve(yaml_path: str, output_path: str | None = None):
    """解析 YAML 并输出 resolved JSON"""
    
    print(f"\n📖 读取 YAML: {yaml_path}")
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f.read()) or {}
    
    trip_meta = data.get('trip', {})
    days_data = data.get('days', [])
    pois_yaml = data.get('pois', [])
    cities_yaml = data.get('cities', [])
    yaml_colors = trip_meta.get('colors', {}) or {}
    
    title = trip_meta.get('title', '自驾路线图')
    subtitle = trip_meta.get('subtitle', '')
    basemap = trip_meta.get('basemap', 'light')
    
    print(f"   行程: {title}")
    print(f"   天数: {len(days_data)}")
    
    if not days_data:
        print("❌ YAML 没有 days 字段")
        sys.exit(1)
    
    N = len(days_data)
    day_colors = [get_day_color(i, yaml_colors) for i in range(N)]
    all_warnings = []
    
    # ── 5a. 解析城市（支持地名 → 坐标） ──
    print(f"\n📍 解析城市坐标...")
    cities_res = []
    city_name_to_coord = {}
    
    # cities_yaml can be list (names) or dict (name->coord)
    if isinstance(cities_yaml, dict):
        city_items = [(name, coord) for name, coord in cities_yaml.items()]
    elif isinstance(cities_yaml, list):
        city_items = [(c, None) for c in cities_yaml]
    else:
        city_items = []
    
    for cname, ccoord in city_items:
        if ccoord and isinstance(ccoord, (list, tuple)) and len(ccoord) == 2:
            coord = ccoord
        else:
            coord = geocode(cname)
        if coord:
            cities_res.append({"name": cname, "lat": coord[0], "lng": coord[1]})
            city_name_to_coord[cname] = {"lat": coord[0], "lng": coord[1], "elevation": 0}
            print(f"  ✓ {cname}: [{coord[0]}, {coord[1]}]")
        else:
            print(f"  ❌ 无法解析城市坐标: {cname}")
            sys.exit(1)
    
    # 查海拔（批量 + 缓存）
    print(f"\n🏔️ 查询城市海拔...")
    elev_map = batch_fetch_elevation([(c['lat'], c['lng']) for c in cities_res])
    for c in cities_res:
        key = f"{round(c['lat'], 4)},{round(c['lng'], 4)}"
        elev = elev_map.get(key) if key in elev_map else None
        if elev is not None:
            c['elevation'] = elev
            city_name_to_coord[c['name']]['elevation'] = elev
            print(f"  {c['name']}: {elev}m")
        else:
            c['elevation'] = 0
            print(f"  {c['name']}: 未知")
    
    # ── 5b. 解析 POI（支持地名 → 坐标 + coord 简写 + hint 辅助） ──
    print(f"\n📍 解析 POI 坐标...")
    major_spots = []
    minor_spots = []
    for p in pois_yaml:
        if 'lat' in p and 'lng' in p:
            coord = [p['lat'], p['lng']]
        elif 'coord' in p and isinstance(p['coord'], (list, tuple)) and len(p['coord']) == 2:
            coord = [float(p['coord'][0]), float(p['coord'][1])]
        elif 'name' in p:
            coord = geocode(p['name'], hint=p.get('hint', ''))
        else:
            print(f"  ⚠ POI 无效: {p.get('name', '?')}")
            continue
        if coord:
            anchor = p.get('iconAnchor', [0, -20])
            if p.get('rank') == 'major':
                major_spots.append([coord[0], coord[1], '#8b6a4a', p['name'], anchor[0], anchor[1]])
            else:
                minor_spots.append([coord[0], coord[1], p['name']])
            print(f"  ✓ {p['name']}: [{coord[0]}, {coord[1]}]")
        else:
            print(f"  ❌ 无法解析 POI: {p.get('name', '?')}")
    
    # POI 摆渡车映射
    poi_shuttle_map = {p['name']: p.get('shuttle', False) for p in pois_yaml if 'name' in p}
    
    # ── 5c. 算路 + 校验 ──
    print(f"\n🚗 获取 {N} 天路线...")
    main_routes = []
    spur_routes = []
    dx_data = []
    sidebar_items = []
    day_card_items = []
    timelines = []  # 微观执行日志
    
    for idx, day in enumerate(days_data):
        d = day.get('day', idx + 1)
        theme = day.get('theme', '')
        route_data = day.get('route', {})
        route_class = day.get('route_class', 'main')
        day_type = day.get('day_type', 'transit')
        city = day.get('city', '')
        items = day.get('items', [])
        stop_tags = day.get('stop_tags', [])
        tips = day.get('tips', [])
        distance_manual = day.get('distance', '')
        
        # 获取城市海拔
        city_elev = None
        if city and city in city_name_to_coord:
            city_elev = city_name_to_coord[city].get('elevation', 0)
        
        color = day_colors[idx]
        name = f'D{d}'
        
        # Resolve start/end/via from names or coordinates
        def resolve_coord(v):
            if isinstance(v, str):
                if v in city_name_to_coord:
                    c = city_name_to_coord[v]
                    return [c['lat'], c['lng']]
                return geocode(v)
            return [round(float(v[0]), 6), round(float(v[1]), 6)] if v else None
        
        start = resolve_coord(route_data.get('start'))
        end = resolve_coord(route_data.get('end'))
        via_raw = route_data.get('via', []) or []
        via = [resolve_coord(v) for v in via_raw if resolve_coord(v)]
        
        # Validate coordinates
        if start and end:
            all_warnings.extend(validate_route(start, end, via))
        
        # Store resolved coords in day for validation
        day['_resolved_start'] = start
        day['_resolved_end'] = end
        day['_resolved_via'] = via
        
        # Fetch route
        print(f"\n  D{d}: {theme}")
        route_result = fetch_route(start, end, via) if start and end else None
        
        if route_result:
            polyline = route_result['polyline']
            distance_km = route_result['distance_km']
            duration_min = route_result['duration_min']
            day['_resolved_distance'] = distance_km
            day['_resolved_duration'] = duration_min
            # 用 OSRM polyline 端点覆盖入参坐标（OSRM 会 snap 到公路）
            day['_resolved_start'] = polyline[0]
            day['_resolved_end'] = polyline[-1]
        else:
            polyline = [[0,0],[0,0]]
            distance_km = 0
            duration_min = 0
            day['_resolved_distance'] = 0
            day['_resolved_duration'] = 0
        
        if len(polyline) < 2:
            polyline = [start or [0,0], end or [0,0]]
        
        if route_class == 'main':
            main_routes.append({"day": d, "color": color, "polyline": polyline})
        else:
            spur_routes.append({"day": d, "color": color, "polyline": polyline})
        
        # Dx position — 优先用 OSRM 路线中点（保证在路线上）
        if day_type == 'local' and city and city in city_name_to_coord:
            cc = city_name_to_coord[city]
            dx_lat = cc['lat'] + 0.02
            dx_lng = cc['lng']
        elif route_result and route_result.get('polyline') and len(route_result['polyline']) > 1:
            poly = route_result['polyline']
            mid = len(poly) // 2
            dx_lat = poly[mid][0]
            dx_lng = poly[mid][1]
        elif start and end:
            dx_lat = (start[0] + end[0]) / 2
            dx_lng = (start[1] + end[1]) / 2
        else:
            dx_lat, dx_lng = (start or [0,0])[0], (start or [0,0])[1]
        
        # Display distance/time
        if distance_manual:
            # YAML 写了的直接使用，不叠加 OSRM
            disttime = f"🚗 {distance_manual}"
        elif route_result and route_result['distance_km'] > 0:
            corrected_min = round(duration_min * 1.33)
            dist_display = f"{distance_km}km"
            # Display: OSRM time + corrected time
            h = corrected_min // 60
            m = corrected_min % 60
            time_display = f"{h}h" + (f"{m}" if m > 0 else "")
            disttime = f"🚗 {dist_display}·{time_display}"
        else:
            disttime = ''
        
        subtext = f'{city}全天' if day_type == 'local' else ''
        dx_data.append({
            "name": name,
            "lat": round(dx_lat, 6),
            "lng": round(dx_lng, 6),
            "color": color,
            "dist": disttime,
            "sub": subtext,
        })
        
        # Validation
        all_warnings.extend(validate_daily(day, idx, day_colors, days_data[:idx+1], city_name_to_coord))
        
        # Sidebar HTML
        day_label = day.get('label', '')
        tag_htmls = []
        for t in stop_tags[:5]:
            tcls = ''
            if '🕌' in t:
                tcls = ' tag-purple'
            elif '返程' in t:
                tcls = ' tag-rose'
            elif '⭐' in t:
                tcls = ' tag-star'
            tag_htmls.append(f'<span class="tag{tcls}">{t}</span>')
        
        # 检测当天是否有摆渡车景点（从 pois 字段 + items 文本匹配）
        day_shuttle_notes = set()
        all_day_text = ' '.join(items + stop_tags + [str(dpoi) for dpoi in day.get('pois', [])])
        for pname, has_shuttle in poi_shuttle_map.items():
            if has_shuttle and pname in all_day_text:
                day_shuttle_notes.add(pname)
                if not any('含摆渡车' in st for st in stop_tags):
                    stop_tags.append(f'🔄 含摆渡车')
                    tag_htmls.append(f'<span class="tag">🔄 含摆渡车</span>')
        
        tips_html = ''.join(f'<div class="tip-note">{tip}</div>' for tip in tips[:5])
        
        elev_tag = ''
        if city_elev and city_elev > 2000:
            elev_tag = f'<span class="tag tag-elev">🏔️{city_elev}m</span>'
        
        sidebar_items.append(f'''    <div class="stop stop-{idx}">
      <div class="stop-marker"><div class="stop-dot">{d}</div><div class="stop-line"></div></div>
      <div class="stop-content">
        <div class="stop-title" style="color:{color}">{name} <span class="st-sub">{theme}</span></div>
        <div class="stop-meta">{day_label} {disttime}</div>
        <div class="stop-tags">{''.join(tag_htmls)}{elev_tag}</div>
        {tips_html}
      </div>
    </div>''')
        
        # Day card HTML
        items_html = '\n'.join(f'<li>{item}</li>' for item in items)
        
        # 摆渡车备注
        shuttle_note = ''
        if day_shuttle_notes:
            shuttle_note = f'<div class="day-shuttle-note">🔄 含摆渡车：{"、".join(sorted(day_shuttle_notes))}（+2h）</div>'
        
        # 微观执行日志（timeline）
        tl = day.get('timeline', [])
        timelines.append(tl)
        timeline_html = ''
        if tl:
            tl_items = '\n'.join(
                f'<div class="tl-row"><span class="tl-time">{t.get("time","")}</span><span class="tl-action">{t.get("action","")}</span></div>'
                for t in tl
            )
            timeline_html = f'''  <div class="timeline-wrap">
    <div class="timeline-toggle" onclick="var n=this.nextElementSibling;n.style.display=n.style.display==='none'?'':'none';this.textContent=this.textContent==='📋 微观日志 ▼'?'📋 微观日志 ▶':'📋 微观日志 ▼';">📋 微观日志 ▼</div>
    <div class="timeline" style="display:none;">
      {tl_items}
    </div>
  </div>'''
        
        day_card_items.append(f'''  <div class="day-card card-{idx}">
    <div class="day-header"><span class="day-label" style="color:{color}">Day {d} · {day_label}</span><span class="day-date">{disttime}</span></div>
    <div class="day-route">{theme}</div>
    <ul class="day-items">{items_html}</ul>
    {shuttle_note}
    {timeline_html}
  </div>''')
    
    # ── 城市坐标同步到路线端点 ──
    # 修正: Nominatim 返回的城区中心和 OSRM 公路入口可能差数公里
    # 导致城市圆点不在路线上。同步 route start/end 到对应城市。
    for c in cities_res:
        cname = c['name']
        for d in days_data:
            sc = d.get('_resolved_start')
            ec = d.get('_resolved_end')
            for pt, role in [(sc, 'start'), (ec, 'end')]:
                if not pt: continue
                rd = d.get('route', {})
                if rd.get(role) == cname:
                    c['lat'] = pt[0]
                    c['lng'] = pt[1]
                    if cname in city_name_to_coord:
                        city_name_to_coord[cname]['lat'] = pt[0]
                        city_name_to_coord[cname]['lng'] = pt[1]
    
    # ── 5d. 城市-颜色分配 ──
    city_assigned = {}
    city_pos_data = []
    
    for idx, day in enumerate(days_data):
        rd = day.get('route', {})
        check_coords = []
        sc = day.get('_resolved_start')
        if sc: check_coords.append(sc)
        for v in (day.get('_resolved_via') or []):
            if v: check_coords.append(v)
        ec = day.get('_resolved_end')
        if ec: check_coords.append(ec)
        
        for c in cities_res:
            ccoord = [c['lat'], c['lng']]
            for cc in check_coords:
                if abs(ccoord[0] - cc[0]) < 0.01 and abs(ccoord[1] - cc[1]) < 0.01:
                    if c['name'] not in city_assigned:
                        city_assigned[c['name']] = idx
    
    for i, c in enumerate(cities_res):
        if c['name'] not in city_assigned:
            best_idx = 0
            best_dist = 999
            for idx, day in enumerate(days_data):
                rd = day.get('route', {})
                for pt in [day.get('_resolved_start'), day.get('_resolved_end')]:
                    if pt and len(pt) >= 2:
                        d = (c['lat']-pt[0])**2 + (c['lng']-pt[1])**2
                        if d < best_dist:
                            best_dist = d
                            best_idx = idx
            city_assigned[c['name']] = best_idx
    
    for c in cities_res:
        day_idx = city_assigned.get(c['name'], 0)
        color = day_colors[day_idx] if day_idx < len(day_colors) else '#b8b09a'
        city_pos_data.append({
            "name": c['name'],
            "lat": c['lat'],
            "lng": c['lng'],
            "color": color,
            "elevation": c.get('elevation', 0),
        })
    
    # ── 5e. 计算中心点 ──
    lat_sum = sum(c['lat'] for c in cities_res) + sum(d['lat'] for d in dx_data)
    lng_sum = sum(c['lng'] for c in cities_res) + sum(d['lng'] for d in dx_data)
    total = len(cities_res) + len(dx_data)
    center_lat = round(lat_sum / total, 4) if total > 0 else 36.0
    center_lng = round(lng_sum / total, 4) if total > 0 else 113.5
    
    # ── 5f. 底图 ──
    tile_url = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
    if basemap == 'dark':
        tile_url = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
    
    # ── 5g. Stop CSS ──
    stop_css = ''
    for i in range(N):
        color = day_colors[i]
        if i < N - 1:
            next_color = day_colors[i + 1]
            stop_css += f'  .stop-{i} .stop-dot {{ border-color: {color}; }} .stop-{i} .stop-line {{ background: linear-gradient(to bottom, {color}, {next_color}); }} .stop-{i} .stop-title {{ color: {color}; }}\n'
        else:
            stop_css += f'  .stop-{i} .stop-dot {{ border-color: {color}; }} .stop-{i} .stop-title {{ color: {color}; }}\n'
    
    # ── 5h. Stats HTML ──
    sd = trip_meta.get('stats', {})
    stats_html = f'''<div class="stats">
  <div class="stat-card"><div class="num">{sd.get('days','')}</div><div class="label">天数</div></div>
  <div class="stat-card"><div class="num">{sd.get('distance','')}</div><div class="label">总车程 (km)</div></div>
  <div class="stat-card"><div class="num">{sd.get('heritage','')}</div><div class="label">国保单位</div></div>
  <div class="stat-card"><div class="num">{sd.get('people','')}</div><div class="label">同行人数</div></div>
</div>'''
    
    # ── 5i. Warnings HTML ──
    warnings_html = ''
    if all_warnings:
        w_lines = '\n'.join(f'    <div style="padding:6px 12px;background:#fff6e5;border-left:3px solid #e8a838;margin:0 0 4px 0;font-size:13px;color:#7a5a20;">{w}</div>' for w in all_warnings)
        warnings_html = f'<div style="margin-bottom:24px;">\n{w_lines}\n</div>'
    
    # ── 5j. Legend HTML ──
    legend_html = '\n    '.join(f'<span class="legend-item"><span class="legend-line" style="background:{day_colors[i]}"></span>D{i+1}</span>' for i in range(N))
    
    # ── 输出 resolved JSON ──
    resolved = {
        "trip": {
            "title": title,
            "subtitle": subtitle,
            "basemap": basemap,
            "stats": sd,
        },
        "cities": city_pos_data,
        "pois": {
            "major": major_spots,
            "minor": minor_spots,
        },
        "routes": {
            "main": main_routes,
            "spur": spur_routes,
        },
        "dx_data": dx_data,
        "sidebar": sidebar_items,
        "day_cards": day_card_items,
        "timelines": timelines,
        "legend_html": legend_html,
        "stats_html": stats_html,
        "warnings_html": warnings_html,
        "warnings": all_warnings,
        "stop_css": stop_css,
        "tile_url": tile_url,
        "center": {"lat": center_lat, "lng": center_lng},
        "day_colors": day_colors,
    }
    
    # Save
    if output_path:
        resolved_path = output_path
    else:
        base = os.path.splitext(os.path.basename(yaml_path))[0]
        resolved_path = os.path.join(RESOLVED_DIR, f"{base}.json")
    
    with open(resolved_path, 'w', encoding='utf-8') as f:
        json.dump(resolved, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ resolved 写入: {resolved_path}")
    
    if all_warnings:
        print(f"\n⚠️ 校验告警 ({len(all_warnings)} 条):")
        for w in all_warnings:
            print(f"  {w}")
    
    return resolved, resolved_path


def main():
    if len(sys.argv) < 2:
        print("用法: python3.11 resolve.py trips/xxx.yaml [--output resolved/xxx.json]")
        sys.exit(1)
    
    yaml_path = sys.argv[1]
    output_path = None
    if '--output' in sys.argv:
        idx = sys.argv.index('--output')
        if idx + 1 < len(sys.argv):
            output_path = sys.argv[idx + 1]
    
    if not os.path.exists(yaml_path):
        print(f"❌ 文件不存在: {yaml_path}")
        sys.exit(1)
    
    resolve(yaml_path, output_path)


if __name__ == '__main__':
    main()
