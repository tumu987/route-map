import os

with open('jindongnan-route-dark.html') as f:
    c = f.read()

# === Convert dark theme to light theme ===

# Background & text
c = c.replace('background: #0f172a; color: #e2e8f0', 'background: #faf8f5; color: #3d3929')

# Header badge
c = c.replace('background: #1e293b; border: 1px solid #334155; border-radius: 20px; padding: 6px 16px; font-size: 13px; color: #94a3b8;',
              'background: #efece4; border: 1px solid #ddd8ce; border-radius: 20px; padding: 6px 16px; font-size: 13px; color: #7a7258;')

# Header sub
c = c.replace('font-size: 14px; color: #64748b; font-weight: 300;', 'font-size: 14px; color: #a0987a; font-weight: 400;')

# Header h1 - remove gradient, use solid color
c = c.replace('background: linear-gradient(135deg, #fbbf24, #f59e0b); -webkit-background-clip: text; -webkit-text-fill-color: transparent;',
              'color: #3d3929; font-weight: 900;')

# Stat cards
c = c.replace('.stat-card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 16px; text-align: center; }',
              '.stat-card { background: #fff; border: 1px solid #f0ede6; border-radius: 12px; padding: 16px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }')

# Stat card num - remove gradient
c = c.replace('.stat-card .num { font-size: 24px; font-weight: 700; background: linear-gradient(135deg, #fbbf24, #f59e0b); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }',
              '.stat-card .num { font-size: 24px; font-weight: 700; color: #c49a6c; }')

# Stat card label
c = c.replace('.stat-card .label { font-size: 12px; color: #64748b; margin-top: 4px; }',
              '.stat-card .label { font-size: 12px; color: #a0987a; margin-top: 4px; }')

# Route map
c = c.replace('position: relative; background: #1e293b; border: 1px solid #334155; border-radius: 16px; padding: 40px 24px; margin-bottom: 36px; overflow: hidden;',
              'position: relative; background: #fff; border: 1px solid #f0ede6; border-radius: 16px; padding: 40px 24px; margin-bottom: 36px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.04);')

# Route map grid overlay color
c = c.replace('rgba(51,65,85,0.2)', 'rgba(0,0,0,0.04)')

# Stop dot background
c = c.replace('.stop-dot { width: 20px; height: 20px; border-radius: 50%; border: 3px solid; background: #1e293b;',
              '.stop-dot { width: 20px; height: 20px; border-radius: 50%; border: 3px solid; background: #fff;')

# Stop meta
c = c.replace('font-size: 12px; color: #64748b; margin-bottom: 6px;', 'font-size: 12px; color: #a0987a; margin-bottom: 6px;')

# Tags
c = c.replace('.tag { font-size: 11px; padding: 2px 8px; border-radius: 10px; background: rgba(251,191,36,0.1); border: 1px solid rgba(251,191,36,0.2); color: #fbbf24; }',
              '.tag { font-size: 11px; padding: 2px 8px; border-radius: 10px; background: rgba(196,154,108,0.08); border: 1px solid rgba(196,154,108,0.2); color: #b0885a; }')

c = c.replace('.tag-star { background: rgba(251,191,36,0.2); border-color: #fbbf24; }',
              '.tag-star { background: rgba(196,154,108,0.15); border-color: #c49a6c; color: #c49a6c; }')

c = c.replace('.tag-purple { background: rgba(167,139,250,0.1); border-color: rgba(167,139,250,0.2); color: #a78bfa; }',
              '.tag-purple { background: rgba(131,151,207,0.1); border-color: rgba(131,151,207,0.2); color: #7a8eb8; }')

c = c.replace('.tag-rose { background: rgba(251,113,133,0.1); border-color: rgba(251,113,133,0.2); color: #fb7185; }',
              '.tag-rose { background: rgba(200,120,120,0.1); border-color: rgba(200,120,120,0.2); color: #b07878; }')

# Stop title colors (muted versions for light theme)
c = c.replace('.stop-0 .stop-title { color: #f87171; }', '.stop-0 .stop-title { color: #d46060; }')
c = c.replace('.stop-1 .stop-title { color: #fbbf24; }', '.stop-1 .stop-title { color: #c49a6c; }')
c = c.replace('.stop-2 .stop-title { color: #34d399; }', '.stop-2 .stop-title { color: #3da87a; }')
c = c.replace('.stop-3 .stop-title { color: #38bdf8; }', '.stop-3 .stop-title { color: #4a8fc7; }')
c = c.replace('.stop-4 .stop-title { color: #a78bfa; }', '.stop-4 .stop-title { color: #8a7bc4; }')
c = c.replace('.stop-5 .stop-title { color: #f472b6; }', '.stop-5 .stop-title { color: #c46a94; }')
c = c.replace('.stop-6 .stop-title { color: #fb923c; }', '.stop-6 .stop-title { color: #c47a38; }')

# Day cards
c = c.replace('.day-card { background: #1e293b; border: 1px solid #334155; border-radius: 14px; padding: 20px; transition: border-color 0.2s; }',
              '.day-card { background: #fff; border: 1px solid #f0ede6; border-radius: 14px; padding: 20px; transition: box-shadow 0.2s; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }')

c = c.replace('.day-card:hover { border-color: #fbbf24; }',
              '.day-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.08); }')

c = c.replace('.day-card .day-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px solid #334155; }',
              '.day-card .day-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px solid #f0ede6; }')

c = c.replace('.day-card .day-date { font-size: 12px; color: #64748b; }',
              '.day-card .day-date { font-size: 12px; color: #a0987a; }')

c = c.replace('.day-card .day-route { font-size: 12px; color: #fbbf24; margin-bottom: 8px; }',
              '.day-card .day-route { font-size: 12px; color: #c49a6c; margin-bottom: 8px; }')

c = c.replace('.day-card .day-items { list-style: none; font-size: 13px; line-height: 1.7; color: #cbd5e1; }',
              '.day-card .day-items { list-style: none; font-size: 13px; line-height: 1.7; color: #5a5240; }')

c = c.replace(".day-card .day-items li::before { content: '▸ '; color: #fbbf24; }",
              ".day-card .day-items li::before { content: '▸ '; color: #c49a6c; }")

c = c.replace('.day-card .highlight { color: #fbbf24; font-weight: 500; }',
              '.day-card .highlight { color: #c49a6c; font-weight: 600; }')

# Tips
c = c.replace('.tip { background: rgba(251,191,36,0.05); border: 1px solid rgba(251,191,36,0.15); border-radius: 10px; padding: 14px 16px; font-size: 13px; color: #94a3b8;',
              '.tip { background: #fff; border: 1px solid #f0ede6; border-radius: 10px; padding: 14px 16px; font-size: 13px; color: #7a7258; box-shadow: 0 1px 3px rgba(0,0,0,0.04);')

# Footer
c = c.replace('.footer { text-align: center; margin-top: 48px; padding-top: 24px; border-top: 1px solid #1e293b; font-size: 12px; color: #475569; }',
              '.footer { text-align: center; margin-top: 48px; padding-top: 24px; border-top: 1px solid #f0ede6; font-size: 12px; color: #b8b09a; }')

# Section title
c = c.replace('font-size:18px;font-weight:700;margin-bottom:16px;color:#94a3b8',
              'font-size:18px;font-weight:700;margin-bottom:16px;color:#a0987a')

# Map section
c = c.replace('.map-section{position:relative;margin-bottom:36px;border-radius:16px;overflow:hidden;border:1px solid #334155}',
              '.map-section{position:relative;margin-bottom:36px;border-radius:16px;overflow:hidden;border:1px solid #f0ede6;box-shadow:0 1px 4px rgba(0,0,0,0.04)}')

c = c.replace('.map-section .legend{display:flex;gap:10px;padding:8px 16px;background:#1e293b;border-bottom:1px solid #334155;font-size:11px;color:#94a3b8;flex-wrap:wrap;align-items:center}',
              '.map-section .legend{display:flex;gap:10px;padding:8px 16px;background:#faf8f5;border-bottom:1px solid #f0ede6;font-size:11px;color:#7a7258;flex-wrap:wrap;align-items:center}')

c = c.replace('.map-section .legend-dash{width:20px;height:0;border-top:3px dashed #475569}',
              '.map-section .legend-dash{width:20px;height:0;border-top:3px dashed #b8b09a}')

c = c.replace('.map-section .legend-sep{color:#475569;margin:0 2px}',
              '.map-section .legend-sep{color:#ddd8ce;margin:0 2px}')

c = c.replace('.map-section .legend-hint{color:#64748b;font-size:10px}',
              '.map-section .legend-hint{color:#b8b09a;font-size:10px}')

# Map background
c = c.replace('#map{height:500px;width:100%;background:#0f172a}',
              '#map{height:500px;width:100%;background:#faf8f5}')

# Switch tiles to light
c = c.replace("L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png')",
              "L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png')")

# Footer text
c = c.replace('深色版', '浅色版')

# Title
c = c.replace('<title>晋东南古建自驾 · 路线图 (深色版)</title>', '<title>晋东南古建自驾 · 路线图</title>')

with open('jindongnan-route-light.html', 'w') as f:
    f.write(c)

size = os.path.getsize('jindongnan-route-light.html')
print(f"Light version: {size} bytes ({size/1024:.0f} KB)")

# Validate
with open('jindongnan-route-light.html') as f:
    c2 = f.read()
print(f"Starts OK: {c2.startswith('<!DOCTYPE')}")
print(f"Ends OK: {c2.rstrip().endswith('</html>')}")
dark_bg = c2.count('#0f172a')
dark_card = c2.count('#1e293b')
print(f"Dark bg (#0f172a) remaining: {dark_bg}")
print(f"Dark card (#1e293b) remaining: {dark_card}")
print(f"Light tiles: {'light_all' in c2}")
