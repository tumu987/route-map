#!/usr/bin/env python3
"""
Extract jindongnan-route-light.html → trips/jindongnan.yaml
"""
import re, json, os

HTML = os.path.join(os.path.dirname(__file__), 'jindongnan-route-light.html')
OUT = os.path.join(os.path.dirname(__file__), 'trips', 'jindongnan.yaml')

with open(HTML, 'r', encoding='utf-8') as f:
    html = f.read()

def extract_var(name):
    """Extract a JS array variable by name."""
    idx = html.find(f'var {name} =')
    if idx == -1:
        return None
    start = idx + len(f'var {name} =')
    depth = 0
    for i in range(start, len(html)):
        if html[i] == '[':
            depth += 1
        elif html[i] == ']':
            depth -= 1
            if depth == 0:
                raw = html[start:i+1]
                raw = re.sub(r'//[^\n]*', '', raw)
                # Wrap unquoted JS object keys in double quotes
                raw = re.sub(r'(\{|,)\s*([a-zA-Z_]\w*)\s*:', r'\1"\2":', raw)
                raw = re.sub(r',\s*([\]}])', r'\1', raw)
                raw = raw.replace("'", '"')
                return json.loads(raw)
    return None

def extract_array_at(pos):
    """Extract JS array starting at given position (pos points to '[')."""
    depth = 1  # pos is already at '[', so depth starts at 1
    for i in range(pos + 1, len(html)):
        if html[i] == '[':
            depth += 1
        elif html[i] == ']':
            depth -= 1
            if depth == 0:
                raw = html[pos:i+1]
                # Strip JS comments (single-line //)
                raw = re.sub(r'//[^\n]*', '', raw)
                # Wrap unquoted JS object keys in double quotes
                raw = re.sub(r'(\{|,)\s*([a-zA-Z_]\w*)\s*:', r'\1"\2":', raw)
                raw = re.sub(r',\s*([\]}])', r'\1', raw)
                raw = raw.replace("'", '"')
                return json.loads(raw)
    return None

# ===== Route coordinates =====
routes = {
    'D1': extract_var('r0'),      # 北京→浊漳河谷 (main)
    'D2': extract_var('r_d2'),    # 浊漳河谷支线 (spur)
    'D3': extract_var('r1'),      # 河谷→长治 (main)
    'D5': extract_var('r2'),      # 长治→高平 (main)
    'D6': extract_var('r3'),      # 高平→皇城 (main)
    'D7': extract_var('r5'),      # 皇城→湘峪→G4 (main)
}

# D4: inline in spurRoutes
idx = html.find('var spurRoutes =')
idx2 = html.find("'#00bcd4',", idx)
if idx2 >= 0:
    arr_start = html.find('[', idx2 + len("'#00bcd4',"))
    d4_raw = extract_array_at(arr_start)
    if d4_raw:
        routes['D4'] = d4_raw

print(f"Extracted routes: {', '.join(f'{k}({len(v)}pts)' for k,v in routes.items() if v)}")

# ===== Cities =====
city_raw = extract_var('cityPosData')
cities = {c['name']: {'lat': c['lat'], 'lng': c['lng'], 'color': c['color']} for c in city_raw}
print(f"Cities: {list(cities.keys())}")

# ===== Day tags =====
dx_raw = extract_var('dxData')
tags = {d['name']: {'lat': d['lat'], 'lng': d['lng'], 'color': d['color']} for d in dx_raw}
print(f"Day tags: {list(tags.keys())}")

# ===== Major spots =====
major_raw = extract_var('majorSpots')
pois = []
for s in major_raw:
    pois.append({
        'name': s[3], 'lat': s[0], 'lng': s[1],
        'color': s[2], 'rank': 'major',
        'iconAnchor': [s[4], s[5]]
    })

# ===== Minor spots =====
minor_raw = extract_var('spots')
for s in minor_raw:
    pois.append({
        'name': s[2], 'lat': s[0], 'lng': s[1],
        'rank': 'minor',
        'color': '#3d7a4a'
    })
print(f"POIs: {len(pois)} total")

# ===== Build YAML =====
os.makedirs(os.path.dirname(OUT), exist_ok=True)

def fmt_route(day):
    """Format a day's route as indented YAML list."""
    coords = routes.get(day)
    if not coords:
        return "  route: []\n"
    lines = [f"  route:"]
    for pt in coords:
        lines.append(f"    - [{pt[0]:.6f}, {pt[1]:.6f}]")
    return '\n'.join(lines) + '\n'

yaml = """# 晋东南古建自驾 — 行程数据
# 自动从 jindongnan-route-light.html v0.1.1 提取
trip:
  title: 晋东南古建自驾路线图
  subtitle: 北京出发 · 浊漳河谷 · 长治 · 高平 · 晋城 · 七日古建巡礼
  dates: 6月8日 — 6月14日
  basemap: light
  colors:
    D1: '#e74c3c'
    D2: '#f39c12'
    D3: '#27ae60'
    D4: '#00bcd4'
    D5: '#3f51b5'
    D6: '#9c27b0'
    D7: '#e91e63'

cities:
"""
for name, c in cities.items():
    yaml += f"  {name}: [{c['lat']:.4f}, {c['lng']:.4f}]\n"

yaml += """
pois:
"""
# Group POIs by day for context
for p in pois:
    yaml += f"  - name: \"{p['name']}\"\n"
    yaml += f"    lat: {p['lat']:.5f}\n"
    yaml += f"    lng: {p['lng']:.5f}\n"
    yaml += f"    rank: {p['rank']}\n"
    if p['rank'] == 'major':
        yaml += f"    iconAnchor: [{p['iconAnchor'][0]}, {p['iconAnchor'][1]}]\n"

yaml += """
days:
"""
# Day card data extracted from HTML (hardcoded from visual inspection)
days_data = [
    {
        'day': 1, 'label': '6/8（一）', 'theme': '北京 → 浊漳河谷',
        'distance': '586km · 6.8h',
        'items': ['早 7:00 从北京出发', '龙门寺 ⭐ 六朝木构于一寺', '淳化寺 金代大殿', '🏨 宿平顺/河谷区'],
        'tags': ['龙门寺', '淳化寺'],
        'pois_refs': ['龙门寺', '淳化寺'],
        'tips': ['提前下载离线地图 — 太行山区多无信号', '上午看古建光线最好，下午背光'],
    },
    {
        'day': 2, 'label': '6/9（二）', 'theme': '浊漳河谷全天',
        'distance': '85km · 1.5h',
        'items': ['龙门寺 → 天台庵 → 大云院', '原起寺 → 淳化寺', '🏨 宿平顺/河谷区'],
        'tags': ['大云院', '天台庵', '原起寺', '九天圣母庙'],
        'pois_refs': ['大云院', '天台庵', '原起寺'],
        'tips': ['古殿内多无照明，自带手电筒', '备零钱10-20元，找文保员开门', '河谷山路雨后易滑，注意安全'],
    },
    {
        'day': 3, 'label': '6/10（三）', 'theme': '河谷 → 长治',
        'distance': '53km · 52min',
        'items': ['上午河谷扫尾或补觉', '观音堂 明代悬塑巅峰', '上党门（长治地标）', '🏨 长治精品酒店 · 🕌 铜锅街清真晚餐'],
        'tags': ['观音堂悬塑', '上党门', '🕌 铜锅街清真晚餐'],
        'pois_refs': ['观音堂'],
    },
    {
        'day': 4, 'label': '6/11（四）', 'theme': '长治周边',
        'distance': '72km · 1.2h',
        'items': ['法兴寺 宋代十二圆觉彩塑', '崇庆寺 宋代罗汉像', '可选：金灯寺石窟（悬崖石窟）', '🏨 长治'],
        'tags': ['法兴寺彩塑', '崇庆寺', '金灯寺石窟'],
        'pois_refs': ['法兴寺', '崇庆寺'],
    },
    {
        'day': 5, 'label': '6/12（五）', 'theme': '长治 → 高平',
        'distance': '100km · 2h',
        'items': ['开化寺 北宋壁画 88㎡', '崇明寺 北宋早期大木作', '姬氏民居 全国最早元代民居', '🏨 高平'],
        'tags': ['开化寺壁画', '姬氏民居', '崇明寺'],
        'pois_refs': ['开化寺', '姬氏民居', '崇明寺'],
    },
    {
        'day': 6, 'label': '6/13（六）', 'theme': '高平 → 晋城 · 皇城相府',
        'distance': '107km · 2h',
        'items': ['玉皇庙 ⭐⭐ 二十八星宿彩塑', '青莲寺 唐代彩塑', '下午：皇城相府（清代相府）', '🏨 宿皇城相府/阳城县'],
        'tags': ['玉皇庙星宿彩塑', '青莲寺', '皇城相府', '🕌 南大街清真美食'],
        'pois_refs': ['玉皇庙星宿彩塑', '青莲寺', '皇城相府'],
    },
    {
        'day': 7, 'label': '6/14（日）', 'theme': '湘峪古堡 → 🏠 北京',
        'distance': '79→752km · 8.5h',
        'items': ['早：湘峪古堡 明代藏兵城堡', '🚗 7h 一路北上回北京', '预计晚 7-8 点到家'],
        'tags': ['湘峪古堡早', '返程 🏠'],
        'pois_refs': ['湘峪古堡'],
    },
]

for dd in days_data:
    d = dd['day']
    day_key = f"D{d}"
    yaml += f"  - day: {d}\n"
    yaml += f"    label: \"{dd['label']}\"\n"
    yaml += f"    theme: \"{dd['theme']}\"\n"
    yaml += f"    distance: \"{dd['distance']}\"\n"
    yaml += f"    route_class: \"{'main' if d in [1,3,5,6,7] else 'spur'}\"\n"
    yaml += f"    items:\n"
    for item in dd['items']:
        yaml += f"      - \"{item}\"\n"
    yaml += f"    stop_tags:\n"
    for tag in dd['tags']:
        yaml += f"      - \"{tag}\"\n"
    yaml += f"    tips:\n"
    for tip in dd.get('tips', []):
        yaml += f"      - \"{tip}\"\n"
    # Reference POIs
    yaml += f"    pois:\n"
    for ref in dd['pois_refs']:
        # Find matching POI
        match = None
        for p in pois:
            if p['name'].startswith(ref.replace('⭐', '').strip()):
                match = p
                break
        if match:
            yaml += f"      - name: \"{match['name']}\"\n"
            yaml += f"        coord: [{match['lat']:.5f}, {match['lng']:.5f}]\n"
            yaml += f"        rank: {match['rank']}\n"
        else:
            # Find by partial match
            for p in pois:
                if ref.replace('⭐','').strip() in p['name'] or p['name'][:2] in ref:
                    yaml += f"      - name: \"{p['name']}\"\n"
                    yaml += f"        coord: [{p['lat']:.5f}, {p['lng']:.5f}]\n"
                    yaml += f"        rank: {p['rank']}\n"
                    break

# Write YAML
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(yaml)

print(f"\n✅ Written to {OUT}")
print(f"   YAML size: {len(yaml)} chars")
