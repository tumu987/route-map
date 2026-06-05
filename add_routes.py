#!/usr/bin/env python3
"""Add route start/end/via coords to jindongnan.yaml"""
import yaml

yaml_path = '/home/xiaobu/route-map/trips/jindongnan.yaml'
with open(yaml_path, 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

# Add route endpoints to each day
route_meta = [
    {'day': 1, 'start': [39.9042, 116.4074], 'via': [[38.0428, 114.5149]], 'end': [36.2000, 113.4390], 'segment_labels': ['北京→石家庄', '石家庄→平顺']},
    {'day': 2, 'start': [36.2020, 113.5740], 'end': [36.3533, 113.4258]},  # 浊漳河谷 loop (龙门寺→原起寺)
    {'day': 3, 'start': [36.2000, 113.4390], 'end': [36.1910, 113.1160]},  # 平顺→长治
    {'day': 4, 'start': [36.1910, 113.1160], 'end': [36.1910, 113.1160]},  # 长治local (loop)
    {'day': 5, 'start': [36.1910, 113.1160], 'end': [35.8000, 112.9300]},  # 长治→高平
    {'day': 6, 'start': [35.8000, 112.9300], 'end': [35.5144, 112.5778]},  # 高平→皇城
    {'day': 7, 'start': [35.6720, 112.1820], 'end': [39.9042, 116.4074], 'via': [[36.72, 114.03]], 'segment_labels': ['湘峪→G4', 'G4→北京（与去程同路重叠）']},
]

for day_data in data['days']:
    day_num = day_data['day']
    rm = next(r for r in route_meta if r['day'] == day_num)
    day_data['start'] = rm['start']
    day_data['end'] = rm['end']
    if 'via' in rm:
        day_data['via'] = rm['via']
    if 'segment_labels' in rm:
        day_data['segment_labels'] = rm['segment_labels']

with open(yaml_path, 'w', encoding='utf-8') as f:
    yaml.dump(data, f, allow_unicode=True, default_flow_style=None, sort_keys=False, indent=2, width=120)

print("✅ Route metadata added to YAML")
