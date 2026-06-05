#!/usr/bin/env python3.11
"""
generate.py — 自驾游路线图生成器

从 YAML 数据文件生成完整的 Leaflet 交互式 HTML 路线图。

用法:
  python3.11 generate.py trips/xxx.yaml
  python3.11 generate.py trips/xxx.yaml --output mymap.html

依赖: pip install pyyaml requests（已装）
"""

import sys
import os
import json
import time
import re
import urllib.request
import urllib.parse
from collections import OrderedDict

# ─────────────────────────────────────────────
# 1. YAML 解析（使用 PyYAML 标准库）
# ─────────────────────────────────────────────

import yaml

def parse_yaml(text):
    """使用标准 PyYAML 解析"""
    return yaml.safe_load(text) or {}


# ─────────────────────────────────────────────
# 2. 色盘
# ─────────────────────────────────────────────
COLOR_PALETTE = [
    '#e74c3c',  # D1  红
    '#f39c12',  # D2  橙
    '#27ae60',  # D3  绿
    '#00bcd4',  # D4  青
    '#3f51b5',  # D5  蓝
    '#9c27b0',  # D6  紫
    '#e91e63',  # D7  玫红
    '#00acc1',  # D8  浅青
    '#ff9800',  # D9  橙黄
    '#795548',  # D10 棕
    '#607d8b',  # D11 灰蓝
    '#8bc34a',  # D12 草绿
    '#ff5722',  # D13 深橙
    '#9e9e9e',  # D14 灰
]

def get_day_color(day_index):
    """获取第 N 天的颜色"""
    return COLOR_PALETTE[day_index % len(COLOR_PALETTE)]


# ─────────────────────────────────────────────
# 3. OSRM 算路
# ─────────────────────────────────────────────
OSRM_BASE = 'https://router.project-osrm.org/route/v1/driving/'

def fetch_osrm_route(start, end, via=None):
    """
    调用 OSRM API 获取行车路线
    start/end: [lat, lng]
    via: [[lat, lng], ...]
    Returns: [[lat, lng], ...] polyline
    """
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
            print(f"  ⚠ OSRM 返回错误: {data.get('code', 'unknown')}, 使用直线")
            return _straight_line(start, end, via)
        coords_raw = data['routes'][0]['geometry']['coordinates']
        # OSRM 返回 [lng, lat]，转成 [lat, lng]
        polyline = [[c[1], c[0]] for c in coords_raw]
        print(f"  ✓ 获取 {len(polyline)} 个坐标点")
        return polyline
    except Exception as e:
        print(f"  ⚠ OSRM 请求失败: {e}, 使用直线")
        return _straight_line(start, end, via)


def _straight_line(start, end, via=None):
    """无 OSRM 时的直线路径"""
    pts = [start]
    if via:
        pts.extend(via)
    pts.append(end)
    # 插值生成平滑路径（至少20个点）
    result = []
    for i in range(len(pts) - 1):
        n = max(2, int(20 / (len(pts) - 1)))
        for j in range(n):
            t = j / n
            lat = pts[i][0] + (pts[i+1][0] - pts[i][0]) * t
            lng = pts[i][1] + (pts[i+1][1] - pts[i][1]) * t
            result.append([round(lat, 6), round(lng, 6)])
    result.append(pts[-1])
    return result


# ─────────────────────────────────────────────
# 4. HTML 生成
# ─────────────────────────────────────────────

def load_leaflet():
    """返回内联 Leaflet JS 和 CSS"""
    base = os.path.dirname(os.path.abspath(__file__))
    js_path = os.path.join(base, 'leaflet.js')
    css_path = os.path.join(base, 'leaflet.css')

    leaflet_js = ''
    leaflet_css = ''
    if os.path.exists(js_path):
        with open(js_path, 'r') as f:
            leaflet_js = f.read()
    if os.path.exists(css_path):
        with open(css_path, 'r') as f:
            leaflet_css = f.read()

    # 如果本地没有，走CDN（先备选）
    if not leaflet_js:
        leaflet_js = '<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>'
    else:
        leaflet_js = f'<script>{leaflet_js}</script>'

    if not leaflet_css:
        leaflet_css = '<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>'
    else:
        leaflet_css = f'<style>{leaflet_css}</style>'
    return leaflet_css, leaflet_js


def generate_html(trip_data, yaml_path):
    """生成完整 HTML"""
    title = trip_data.get('trip', {}).get('title', '自驾路线图')
    subtitle = trip_data.get('trip', {}).get('subtitle', '')
    dates = trip_data.get('trip', {}).get('dates', '')
    basemap = trip_data.get('trip', {}).get('basemap', 'light')
    stats_data = trip_data.get('trip', {}).get('stats', {})

    days_data = trip_data.get('days', [])
    cities_yaml = trip_data.get('cities', {})
    pois_yaml = trip_data.get('pois', [])

    N = len(days_data)
    # 颜色映射
    day_colors = [get_day_color(i) for i in range(N)]

    # 城市数据：从 YAML cities 中取，但需要 deduplicate 住过的城市
    city_names = list(cities_yaml.keys())
    city_coords = list(cities_yaml.values())

    # 提取所有POI
    major_spots = []
    minor_spots = []
    for p in pois_yaml:
        anchor = p.get('iconAnchor', [0, -20])
        spot = [p['lat'], p['lng'], '#8b6a4a', p['name'], anchor[0], anchor[1]]
        if p.get('rank') == 'major':
            major_spots.append(spot)
        else:
            minor_spots.append([p['lat'], p['lng'], p['name']])

    # 生成路线
    out_name = os.path.splitext(os.path.basename(yaml_path))[0]
    output_file = os.path.join(os.path.dirname(yaml_path), '..', 'output', out_name + '.html')
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # ── OSRM: 获取每条路线的 polyline ──
    print(f"\n🚗 获取 {N} 天路线的 OSRM 坐标...")
    main_routes = []
    spur_routes = []
    dx_positions = []  # [[lat, lng, color, name, subtext, disttime], ...]
    day_cards_html = ''
    sidebar_html = ''

    for idx, day in enumerate(days_data):
        d = day.get('day', idx + 1)
        theme = day.get('theme', '')
        distance = day.get('distance', '')
        route_class = day.get('route_class', 'main')
        route_data = day.get('route', {})
        start = route_data.get('start')
        end = route_data.get('end')
        via_list = route_data.get('via', []) or []
        items = day.get('items', [])
        stop_tags = day.get('stop_tags', [])
        tips = day.get('tips', [])

        color = day_colors[idx]
        name = f'D{d}'

        # 生成 Dx 位置（取出发地或第一个途经点与目的地的中点）
        dx_lat = (start[0] + end[0]) / 2 if start and end else (start or [0,0])[0]
        dx_lng = (start[1] + end[1]) / 2 if start and end else (start or [0,0])[1]
        subtext = ''
        disttime = f'🚗 {distance}' if distance else ''
        dx_positions.append([dx_lat, dx_lng, color, name, subtext, disttime])

        # 获取路线坐标
        print(f"\n  D{d}: {theme}")
        time.sleep(0.3)  # OSRM 限流保护
        polyline = fetch_osrm_route(start, end, via_list) if start and end else [[0,0],[0,0]]
        # 至少2个点
        if len(polyline) < 2:
            polyline = [start or [0,0], end or [0,0]]

        if route_class == 'main':
            main_routes.append((color, polyline))
        else:
            spur_routes.append((color, polyline))

        # ── 侧边栏 stop ──
        full_name = name
        day_label = day.get('label', '')
        sidebar_html += f'''    <div class="stop stop-{idx}">
      <div class="stop-marker"><div class="stop-dot">{idx+1}</div><div class="stop-line"></div></div>
      <div class="stop-content">
        <div class="stop-title" style="color:{color}">{full_name} <span class="st-sub">{theme}</span></div>
        <div class="stop-meta">{day_label} 🚗 {distance}</div>
        <div class="stop-tags">{''.join(f'<span class="tag{tcls}">{t}</span>' for t, tcls in [(t, ' tag-purple' if '🕌' in t else (' tag-rose' if '返程' in t else (' tag-star' if '⭐' in t else ''))) for t in stop_tags[:5]])}</div>
        {''.join(f'<div class="tip-note">{tip}</div>' for tip in tips[:2])}
      </div>
    </div>'''

        # ── 每日卡片 ──
        items_html = '\n'.join(f'<li>{item}</li>' for item in items)
        day_label = day.get('label', '')
        day_cards_html += f'''  <div class="day-card card-{idx}">
    <div class="day-header"><span class="day-label" style="color:{color}">Day {d} · {day_label}</span><span class="day-date">{disttime}</span></div>
    <div class="day-route">{theme}</div>
    <ul class="day-items">{items_html}</ul>
  </div>'''

    # ── 提取侧边栏中出现的城市 ──
    # 从 day route 的 end 坐标匹配城市
    # 简化：直接用 YAML 定义的 cities
    city_pos_data = []
    # 给城市分配颜色：匹配第一个出现的日期的颜色
    # 先精确匹配坐标（start/via/end），没匹配到的找最近的路段日
    city_day_assigned = {}
    for idx, day in enumerate(days_data):
        route_data = day.get('route', {})
        check_coords = []
        sc = route_data.get('start')
        if sc: check_coords.append(sc)
        for v in (route_data.get('via') or []):
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                check_coords.append(v)
        ec = route_data.get('end')
        if ec: check_coords.append(ec)

        for cname, coord in zip(city_names, city_coords):
            for cc in check_coords:
                if abs(coord[0] - cc[0]) < 0.01 and abs(coord[1] - cc[1]) < 0.01:
                    if cname not in city_day_assigned:
                        city_day_assigned[cname] = idx

    # 未匹配的城市按坐标最近的路段日分配
    for i, (cname, coord) in enumerate(zip(city_names, city_coords)):
        if cname in city_day_assigned:
            continue
        # 找最近的 route 起终点
        best_idx = 0
        best_dist = 999
        for idx, day in enumerate(days_data):
            rd = day.get('route', {})
            for pt in [rd.get('start'), rd.get('end')]:
                if pt and len(pt) >= 2:
                    d = (coord[0]-pt[0])**2 + (coord[1]-pt[1])**2
                    if d < best_dist:
                        best_dist = d
                        best_idx = idx
        city_day_assigned[cname] = best_idx

    for cname, coord in zip(city_names, city_coords):
        day_idx = city_day_assigned.get(cname, 0)
        city_color = day_colors[day_idx] if day_idx < len(day_colors) else '#b8b09a'
        city_pos_data.append({'name': cname, 'lat': coord[0], 'lng': coord[1],
                             'color': city_color})

    # ── 生成 CSS stop 颜色段 ──
    stop_css = ''
    for i in range(N):
        color = day_colors[i]
        if i < N - 1:
            next_color = day_colors[i + 1]
            stop_css += f'  .stop-{i} .stop-dot {{ border-color: {color}; }} .stop-{i} .stop-line {{ background: linear-gradient(to bottom, {color}, {next_color}); }} .stop-{i} .stop-title {{ color: {color}; }}\n'
        else:
            stop_css += f'  .stop-{i} .stop-dot {{ border-color: {color}; }} .stop-{i} .stop-title {{ color: {color}; }}\n'

    # ── 路线数据 JS ──
    # 每条路线存为 r_1, r_2, ...
    route_js = ''
    for idx, (color, polyline) in enumerate(main_routes):
        pts_str = json.dumps([[round(p[0],6), round(p[1],6)] for p in polyline])
        route_js += f'var r_{idx+1} = {pts_str};\n'
    for idx, (color, polyline) in enumerate(spur_routes):
        pts_str = json.dumps([[round(p[0],6), round(p[1],6)] for p in polyline])
        route_js += f'var sr_{idx+1} = {pts_str};\n'

    # mainRoutes / spurRoutes
    main_routes_js = 'var mainRoutes = [\n' + '\n'.join(f"  ['{color}', r_{i+1}]," for i, (color, _) in enumerate(main_routes)) + '\n];'
    spur_routes_js = 'var spurRoutes = [\n' + '\n'.join(f"  ['{color}', sr_{i+1}]," for i, (color, _) in enumerate(spur_routes)) + '\n];' if spur_routes else 'var spurRoutes = [];'

    # 城市数据
    cities_js = 'var cityPosData = ' + json.dumps(city_pos_data, ensure_ascii=False) + ';'

    # Dx 数据
    dx_data_js = 'var dxData = ' + json.dumps([{'name': d[3], 'lat': d[0], 'lng': d[1], 'color': d[2], 'dist': d[5]} for d in dx_positions], ensure_ascii=False) + ';'

    # POI 数据
    major_js = 'var majorSpots = ' + json.dumps(major_spots, ensure_ascii=False) + ';'
    minor_js = 'var spots = ' + json.dumps(minor_spots, ensure_ascii=False) + ';'

    # 初始中心点（所有城市坐标的平均）
    lat_sum = sum(c[0] for c in city_coords) + sum(d[0] for d in dx_positions)
    lng_sum = sum(c[1] for c in city_coords) + sum(d[1] for d in dx_positions)
    total = len(city_coords) + len(dx_positions)
    center_lat = round(lat_sum / total, 4) if total > 0 else 36.0
    center_lng = round(lng_sum / total, 4) if total > 0 else 113.5

    # 加载 Leaflet
    leaflet_css, leaflet_js = load_leaflet()

    # 底图 URL
    if basemap == 'dark':
        tile_url = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
    else:
        tile_url = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"

    # ── 拼装 CSS ──
    css_text = f"""  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700;900&display=swap');
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: #faf8f5; color: #3d3929; font-family: 'Noto Sans SC', system-ui, sans-serif; min-height: 100vh; }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 40px 24px; }}

  header {{ margin-bottom: 40px; display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 12px; }}
  header h1 {{ font-size: 28px; font-weight: 900; color: #3d3929; }}
  header .sub {{ font-size: 14px; color: #a0987a; font-weight: 400; }}
  header .badge {{ background: #efece4; border: 1px solid #ddd8ce; border-radius: 20px; padding: 6px 16px; font-size: 13px; color: #7a7258; }}

  .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 36px; }}
  .stat-card {{ background: #fff; border: 1px solid #f0ede6; border-radius: 12px; padding: 16px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }}
  .stat-card .num {{ font-size: 24px; font-weight: 700; color: #3d3929; }}
  .stat-card .label {{ font-size: 12px; color: #a0987a; margin-top: 4px; }}

  .map-section {{ position: relative; background: #fff; border: 1px solid #f0ede6; border-radius: 16px; margin-bottom: 36px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.04); }}
  .legend {{ display: flex; gap: 10px; padding: 8px 16px; background: #faf8f5; border-bottom: 1px solid #f0ede6; font-size: 11px; color: #7a7258; flex-wrap: wrap; align-items: center; }}
  .legend-item {{ display: flex; align-items: center; gap: 4px; }}
  .legend-line {{ width: 20px; height: 3px; border-radius: 2px; }}
  #map {{ height: 500px; width: 100%; background: #faf8f5; border-radius: 0; }}
  #layer-switch {{ position: absolute; top: 4.5em; right: 12px; z-index: 1000; display: flex; gap: 0; background: rgba(255,255,255,0.92); border: 1px solid #f0ede6; border-radius: 8px; overflow: hidden; backdrop-filter: blur(8px); }}
  .ls-btn {{ padding: 6px 12px; font-size: 12px; cursor: pointer; color: #a0987a; transition: all .15s; user-select: none; background: transparent; border: none; font-family: inherit; }}
  .ls-btn.active {{ background: #efece4; color: #7a6a4a; font-weight: 600; }}
  .ls-btn:not(.active):hover {{ color: #3d3929; }}
  #zoom-display {{ position: absolute; bottom: 12px; left: 12px; z-index: 1000; background: rgba(255,255,255,0.85); border: 1px solid #f0ede6; border-radius: 6px; padding: 4px 10px; font-size: 11px; color: #7a7258; font-family: monospace; }}

  .route-map {{ position: relative; background: #fff; border: 1px solid #f0ede6; border-radius: 16px; padding: 40px 24px; margin-bottom: 36px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.04); }}
  .route-stops {{ position: relative; z-index: 1; display: flex; flex-direction: column; gap: 0; }}
  .stop {{ display: flex; gap: 20px; position: relative; padding: 16px 0; min-height: 80px; }}
  .stop:last-child {{ min-height: 0; }}
  .stop-marker {{ display: flex; flex-direction: column; align-items: center; width: 40px; flex-shrink: 0; position: relative; }}
  .stop-dot {{ width: 20px; height: 20px; border-radius: 50%; border: 3px solid; background: #fff; z-index: 2; position: relative; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 700; margin-top: 3px; }}
  .stop-line {{ width: 2px; flex-grow: 1; min-height: 40px; margin: 4px 0; }}
  .stop:last-child .stop-line {{ display: none; }}
  .stop-content {{ flex: 1; padding-top: 2px; }}
  .stop-title {{ font-size: 16px; font-weight: 700; margin-bottom: 2px; line-height: 1.4; }}
  .stop-title .st-sub {{ font-size: 13px; font-weight: 400; color: #a0987a; display: block; line-height: 1.4; }}
  .stop-meta {{ font-size: 12px; color: #a0987a; margin-bottom: 6px; }}
  .stop-tags {{ display: flex; flex-wrap: wrap; gap: 6px; }}
  .tag {{ font-size: 11px; padding: 2px 8px; border-radius: 10px; background: rgba(196,154,108,0.08); border: 1px solid rgba(196,154,108,0.2); color: #b0885a; }}
  .tag-star {{ background: rgba(196,154,108,0.15); border-color: #c49a6c; color: #c49a6c; }}
  .tag-purple {{ background: rgba(131,151,207,0.1); border-color: rgba(131,151,207,0.2); color: #7a8eb8; }}
  .tag-rose {{ background: rgba(200,120,120,0.1); border-color: rgba(200,120,120,0.2); color: #b07878; }}
  .tip-note {{ font-size: 12px; margin-top: 6px; display: flex; align-items: center; gap: 4px; }}
  .tip-note .ti {{ flex-shrink: 0; }}
{stop_css}
  .day-cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px,1fr)); gap: 16px; margin-top: 36px; }}
  .day-card {{ background: #fff; border: 1px solid #f0ede6; border-radius: 14px; padding: 20px; transition: box-shadow 0.2s; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }}
  .day-card:hover {{ box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
  .day-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px solid #f0ede6; }}
  .day-label {{ font-size: 14px; font-weight: 700; }}
  .day-date {{ font-size: 12px; color: #a0987a; }}
  .highlight {{ color: #c49a6c; font-weight: 600; }}
  .day-route {{ font-size: 14px; color: #c49a6c; margin-bottom: 8px; }}
  .day-items {{ list-style: none; font-size: 13px; line-height: 1.7; color: #5a5240; }}
  .day-items li::before {{ content: '\\25b8 '; color: #fbbf24; }}

  .footer {{ text-align: center; margin-top: 48px; padding-top: 24px; border-top: 1px solid #f0ede6; font-size: 12px; color: #b8b09a; }}

  @media (max-width: 640px) {{ #map {{ height: 280px; touch-action: pan-y; }} }}
  @media (max-width: 640px) {{ .container {{ padding: 20px 16px; }} header h1 {{ font-size: 22px; }} .stop {{ gap: 12px; }} .stop-title {{ font-size: 14px; }} .day-cards {{ grid-template-columns: 1fr; }} .day-label{{font-size:16px!important}} .day-date{{font-size:13px!important}} .day-route{{font-size:14px!important}} .day-items{{font-size:14px!important}} }}
"""

    # ── stats HTML ──
    sd = stats_data
    stats_html = f'''<div class="stats">
  <div class="stat-card"><div class="num">{sd.get('days','')}</div><div class="label">天数</div></div>
  <div class="stat-card"><div class="num">{sd.get('distance','')}</div><div class="label">总车程 (km)</div></div>
  <div class="stat-card"><div class="num">{sd.get('heritage','')}</div><div class="label">国保单位</div></div>
  <div class="stat-card"><div class="num">{sd.get('people','')}</div><div class="label">同行人数</div></div>
</div>'''

    # 拼接完整 HTML
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
{leaflet_css}
<style>
{css_text}
</style>
</head>
<body>
<div class="container">

<header>
  <div>
    <h1>{title}</h1>
    <div class="sub">{subtitle}</div>
  </div>
</header>

{stats_html}

<div class="map-section">
  <div class="legend">
    {''.join(f'<span class="legend-item"><span class="legend-line" style="background:{day_colors[i]}"></span>D{i+1}</span>' for i in range(N))}
  </div>
  <div id="map"></div>
  <div id="layer-switch">
    <span class="ls-btn active" data-layer="standard">标准</span>
    <span class="ls-btn" data-layer="terrain">地形</span>
  </div>
  <div id="zoom-display" style="position:absolute;bottom:12px;left:12px;z-index:1000;background:rgba(255,255,255,0.85);border:1px solid #f0ede6;border-radius:6px;padding:4px 10px;font-size:11px;color:#7a7258;font-family:monospace;">Zoom 5</div>
</div>
  <div class="route-map">
    <div class="route-stops">
{sidebar_html}
    </div>
  </div>
  <h2 style="font-size:18px;font-weight:700;margin-bottom:16px;color:#94a3b8;">📋 每日详情</h2>
  <div class="day-cards">
{day_cards_html}
  </div>
  <div class="footer"></div>
</div>
{leaflet_js}
<script>
// ═══════════════════ Route Data ═══════════════════
{route_js}
{main_routes_js}
{spur_routes_js}
{cities_js}
{dx_data_js}
{major_js}
{minor_js}
// ═══════════════════════════════════════════════════
// 地图初始化
var map = L.map('map', {{ center: [{center_lat}, {center_lng}], zoom: 7, zoomControl: true, scrollWheelZoom: true }});
L.tileLayer('{tile_url}', {{ attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>', subdomains: 'abcd', maxZoom: 20 }}).addTo(map);

var standardTile = L.tileLayer('{tile_url}', {{ attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>', subdomains: 'abcd', maxZoom: 20 }});
var terrainTile = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{{z}}/{{y}}/{{x}}', {{ attribution: 'Tiles &copy; Esri', maxZoom: 17 }});

standardTile.addTo(map);
document.querySelectorAll('.ls-btn').forEach(function(btn) {{
  btn.addEventListener('click', function() {{
    document.querySelectorAll('.ls-btn').forEach(function(b) {{ b.classList.remove('active'); }});
    this.classList.add('active');
    if (this.dataset.layer === 'standard') {{ map.removeLayer(terrainTile); standardTile.addTo(map); }}
    else {{ map.removeLayer(standardTile); terrainTile.addTo(map); }}
  }});
}});

// Layer groups
var ov = L.layerGroup().addTo(map);
var cityOv = L.layerGroup().addTo(map);
var dayOv = L.layerGroup().addTo(map);
var cityLite = L.layerGroup();
var dayLite = L.layerGroup();
var sp = L.layerGroup();
var su = L.layerGroup();
var sub = L.layerGroup();
var ld = L.layerGroup();
var ld2 = L.layerGroup();
var cityOvOrig = L.layerGroup();

// Draw main routes
for (var i = 0; i < mainRoutes.length; i++) {{
  ov.addLayer(L.polyline(mainRoutes[i][1], {{ color: mainRoutes[i][0], weight: 4, opacity: 0.85, smoothFactor: 1 }}));
}}
// Draw spur routes
for (var i = 0; i < spurRoutes.length; i++) {{
  su.addLayer(L.polyline(spurRoutes[i][1], {{ color: spurRoutes[i][0], weight: 3, opacity: 0.6, smoothFactor: 1 }}));
}}

// ===== 碰撞检测引擎 =====
var routePts = [];
function collectPts(arr) {{ for (var i=0;i<arr.length;i++) for (var j=0;j<arr[i][1].length;j+=20) routePts.push(arr[i][1][j]); }}
collectPts(mainRoutes); collectPts(spurRoutes);

function minDistToOtherRoutes(lat, lng, excludeLat, excludeLng) {{
  var m = Infinity;
  for (var i = 0; i < routePts.length; i++) {{
    var dx = routePts[i][0] - excludeLat;
    var dy = routePts[i][1] - excludeLng;
    if (dx*dx + dy*dy < 0.0009) continue;
    dx = lat - routePts[i][0]; dy = lng - routePts[i][1];
    var d = dx*dx + dy*dy; if (d < m) m = d;
  }}
  return Math.sqrt(m);
}}

var placedLabels = [];
function minLabelDist(lat, lng) {{
  var m = 1;
  for (var i = 0; i < placedLabels.length; i++) {{
    var dx = lat - placedLabels[i][0], dy = lng - placedLabels[i][1];
    var d = Math.sqrt(dx*dx + dy*dy); if (d < m) m = d;
  }}
  return m;
}}

function findLeader(lat, lng, minGap, maxStep) {{
  var dirs = [[0,1],[0.7,0.7],[1,0],[0.7,-0.7],[0,-1],[-0.7,-0.7],[-1,0],[-0.7,0.7]];
  for (var step = 1; step <= maxStep; step++) {{
    var d = step * (minGap * 1.2);
    for (var di = 0; di < dirs.length; di++) {{
      var nl = lat + dirs[di][0] * d;
      var ng = lng + dirs[di][1] * d;
      if (minDistToOtherRoutes(nl, ng, lat, lng) >= minGap && minLabelDist(nl, ng) >= minGap)
        return [nl, ng];
    }}
  }}
  return [lat + minGap * 2, lng + minGap * 2];
}}

function placeLabel(lat, lng, minGap, maxStep) {{
  if (minDistToOtherRoutes(lat, lng, lat, lng) >= minGap && minLabelDist(lat, lng) >= minGap) {{
    placedLabels.push([lat, lng]); return [lat, lng];
  }}
  var pos = findLeader(lat, lng, minGap, maxStep);
  placedLabels.push(pos); return pos;
}}

// ===== 标签避让计算 =====
var closeGap = 0.025, closeStep = 8;
var farGap = 0.08, farStep = 20;

placedLabels = [];
var cityClose = [], cityFar = [], dxClose = [], dxFar = [];
for (var i = 0; i < cityPosData.length; i++) {{
  var c = cityPosData[i];
  cityClose.push(placeLabel(c.lat, c.lng, closeGap, closeStep));
}}
placedLabels = [];
for (var i = 0; i < cityPosData.length; i++) {{
  var c = cityPosData[i];
  cityFar.push(placeLabel(c.lat, c.lng, farGap, farStep));
}}
placedLabels = [];
var dxClose = [], dxFar = [];
for (var i = 0; i < dxData.length; i++) {{
  var d = dxData[i];
  dxClose.push(placeLabel(d.lat, d.lng, closeGap, closeStep));
}}
placedLabels = [];
var dxFar = [];
for (var i = 0; i < dxData.length; i++) {{
  var d = dxData[i];
  dxFar.push(placeLabel(d.lat, d.lng, farGap, farStep));
}}

// ===== 绘制标注 =====

// zoom ≥ 9 城市标签
for (var i = 0; i < cityPosData.length; i++) {{
  var c = cityPosData[i], p = cityClose[i];
  cityOv.addLayer(L.marker(p, {{
    icon: L.divIcon({{ className: '', html: '<div style="display:inline-block;color:'+c.color+';font-size:14px;font-weight:700;white-space:nowrap;background:rgba(255,255,255,0.85);border-radius:4px;padding:1px 6px;box-shadow:0 1px 3px rgba(0,0,0,0.06);">'+c.name+'</div>', iconSize: null, iconAnchor: [c.name.length * 7 + 6, 15] }})
  }}));
}}

// zoom ≥ 10 城市标签（原始坐标）
for (var i = 0; i < cityPosData.length; i++) {{
  var c = cityPosData[i];
  cityOvOrig.addLayer(L.marker([c.lat, c.lng], {{
    icon: L.divIcon({{ className: '', html: '<div style="display:inline-block;color:'+c.color+';font-size:14px;font-weight:700;white-space:nowrap;background:rgba(255,255,255,0.92);border-radius:4px;padding:2px 8px;box-shadow:0 1px 4px rgba(0,0,0,0.1);">'+c.name+'</div>', iconSize: null, iconAnchor: [c.name.length * 7 + 8, 15] }})
  }}));
}}

// zoom < 9 简洁版
for (var i = 0; i < cityPosData.length; i++) {{
  var c = cityPosData[i], p = cityFar[i];
  var dx = p[0] - c.lat, dy = p[1] - c.lng;
  if (dx*dx + dy*dy > 0.0004) {{
    ld.addLayer(L.circleMarker([c.lat, c.lng], {{ radius: 4, color: c.color, weight: 2, fillColor: '#fff', fillOpacity: 1 }}));
    ld.addLayer(L.polyline([[c.lat, c.lng], p], {{ color: c.color, weight: 2, opacity: 0.5, dashArray: '5,4' }}));
  }}
  cityLite.addLayer(L.marker(p, {{ icon: L.divIcon({{className:'',html:'<span style="display:inline-block;color:'+c.color+';font-size:14px;font-weight:700;white-space:nowrap;text-shadow:0 0 4px #fff,0 0 8px #fff;">'+c.name+'</span>',iconSize:null,iconAnchor:[c.name.length*7,10]}}) }}));
}}

// Dx 标签
for (var i = 0; i < dxData.length; i++) {{
  var d = dxData[i], p = dxClose[i];
  var fullName = d.name;
  var distTime = d.dist || '';
  var label = '<div style="text-align:center;line-height:1.3;white-space:nowrap;"><div style="font-weight:700;font-size:12px;color:'+d.color+';text-shadow:0 0 4px #fff,0 0 8px #fff;">'+fullName+'</div><div style="font-size:10px;color:#7a7258;text-shadow:0 0 4px #fff,0 0 8px #fff;">'+distTime+'</div></div>';
  dayOv.addLayer(L.marker(p, {{
    icon: L.divIcon({{ className: '', html: label, iconSize: [80, 32], iconAnchor: [40, 16] }})
  }}));
  dayLite.addLayer(L.marker(p, {{ icon: L.divIcon({{className:'',html:'<div style="text-align:center;line-height:1.3;white-space:nowrap;"><div style="font-weight:700;font-size:12px;color:'+d.color+';text-shadow:0 0 4px #fff,0 0 8px #fff;">'+d.name+'</div></div>', iconSize: [40,16], iconAnchor: [20,8]}}) }}));
}}

// zoom = 9 引线
for (var i = 0; i < cityPosData.length; i++) {{
  var c = cityPosData[i], p = dxClose[i];
  var orig = [c.lat, c.lng];
  var p2 = cityClose[i];
  var dx = p2[0] - orig[0], dy = p2[1] - orig[1];
  if (dx*dx + dy*dy > 0.0004) {{
    ld2.addLayer(L.circleMarker(orig, {{ radius: 4, color: c.color, weight: 2, fillColor: '#fff', fillOpacity: 1 }}));
    ld2.addLayer(L.polyline([orig, p2], {{ color: c.color, weight: 2, opacity: 0.5, dashArray: '5,4' }}));
  }}
}}

// Major POIs
for (var i = 0; i < majorSpots.length; i++) {{
  var s = majorSpots[i];
  sp.addLayer(L.marker([s[0], s[1]], {{
    icon: L.divIcon({{ className: '', html: '<div style="display:flex;align-items:center;gap:3px;"><div style="width:6px;height:6px;background:'+s[2]+';border-radius:50%;flex-shrink:0;"></div><span style="font-size:12px;font-weight:700;color:'+s[2]+';white-space:nowrap;">'+s[3]+'</span></div>', iconSize: [40,28], iconAnchor: [s[4]+20, s[5]+14] }})
  }}));
}}
// Minor POIs
for (var i = 0; i < spots.length; i++) {{
  var s = spots[i];
  sub.addLayer(L.marker([s[0], s[1]], {{
    icon: L.divIcon({{ className: '', html: '<div style="display:flex;align-items:center;gap:3px;"><div style="width:6px;height:6px;background:#3d7a4a;border-radius:50%;flex-shrink:0;"></div><span style="font-size:11px;font-weight:700;color:#3d7a4a;white-space:nowrap;">'+s[2]+'</span></div>', iconSize: [80,18], iconAnchor: [4,9] }})
  }}));
}}

// Fit map to all route/data bounds
var allBounds = L.latLngBounds([routePts[0]]);
for (var i = 1; i < routePts.length; i++) {{ allBounds.extend(routePts[i]); }}
cityPosData.forEach(function(c) {{ allBounds.extend([c.lat, c.lng]); }});
dxData.forEach(function(d) {{ allBounds.extend([d.lat, d.lng]); }});
majorSpots.forEach(function(s) {{ allBounds.extend([s[0], s[1]]); }});
spots.forEach(function(s) {{ allBounds.extend([s[0], s[1]]); }});
map.fitBounds(allBounds, {{ padding: [50, 50] }});

// Zoom level handler
function u() {{
  var z = map.getZoom();
  document.getElementById('zoom-display').textContent = 'Zoom ' + z;
  if (z < 9) {{
    if (!map.hasLayer(cityLite)) map.addLayer(cityLite);
    if (!map.hasLayer(dayLite)) map.addLayer(dayLite);
    if (!map.hasLayer(ld)) map.addLayer(ld);
    if (map.hasLayer(cityOv)) map.removeLayer(cityOv);
    if (map.hasLayer(cityOvOrig)) map.removeLayer(cityOvOrig);
    if (map.hasLayer(dayOv)) map.removeLayer(dayOv);
  }} else if (z >= 10) {{
    if (map.hasLayer(cityLite)) map.removeLayer(cityLite);
    if (map.hasLayer(dayLite)) map.removeLayer(dayLite);
    if (map.hasLayer(ld)) map.removeLayer(ld);
    if (map.hasLayer(cityOv)) map.removeLayer(cityOv);
    if (!map.hasLayer(cityOvOrig)) map.addLayer(cityOvOrig);
    if (!map.hasLayer(dayOv)) map.addLayer(dayOv);
  }} else {{
    if (map.hasLayer(cityLite)) map.removeLayer(cityLite);
    if (map.hasLayer(dayLite)) map.removeLayer(dayLite);
    if (map.hasLayer(ld)) map.removeLayer(ld);
    if (!map.hasLayer(cityOv)) map.addLayer(cityOv);
    if (map.hasLayer(cityOvOrig)) map.removeLayer(cityOvOrig);
    if (!map.hasLayer(dayOv)) map.addLayer(dayOv);
  }}
  if (z >= 10) {{
    if (!map.hasLayer(sp)) map.addLayer(sp);
    if (!map.hasLayer(su)) map.addLayer(su);
    if (map.hasLayer(ld2)) map.removeLayer(ld2);
  }} else {{
    if (map.hasLayer(sp)) map.removeLayer(sp);
    if (map.hasLayer(su)) map.removeLayer(su);
    if (!map.hasLayer(ld2)) map.addLayer(ld2);
  }}
  if (z >= 11) {{ if (!map.hasLayer(sub)) map.addLayer(sub); }} else {{ if (map.hasLayer(sub)) map.removeLayer(sub); }}
}}
map.on('zoomend', u); u();
</script>
</body>
</html>'''

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\n✅ 生成成功: {output_file}")
    print(f"   大小: {os.path.getsize(output_file):,} 字节")
    return output_file


# ─────────────────────────────────────────────
# 5. 主入口
# ─────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("用法: python3.11 generate.py trips/xxx.yaml [--output output.html]")
        sys.exit(1)

    yaml_path = sys.argv[1]
    if not os.path.exists(yaml_path):
        print(f"❌ 文件不存在: {yaml_path}")
        sys.exit(1)

    # 解析 YAML
    print(f"\n📖 读取 YAML: {yaml_path}")
    with open(yaml_path, 'r', encoding='utf-8') as f:
        text = f.read()
    data = parse_yaml(text)
    print(f"   行程: {data.get('trip', {}).get('title', '未知')}")
    days = data.get('days', [])
    print(f"   天数: {len(days)}")

    # 生成 HTML
    output = generate_html(data, yaml_path)

    # HTTP 预览提示
    print(f"\n🌐 预览: http://localhost:9120/{os.path.basename(output)}")


if __name__ == '__main__':
    main()
