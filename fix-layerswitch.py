import os, re

for fname in ['jindongnan-route-dark.html', 'jindongnan-route-light.html']:
    with open(fname) as f:
        c = f.read()

    # Determine if dark or light
    is_dark = 'dark' in fname

    # 1. Remove the default layer control
    c = c.replace("L.control.layers(tiles, null, { position: 'topright', collapsed: true }).addTo(map);", "")

    # 2. Add custom layer switch HTML right after the map-section div
    switch_html = '''<div id="layer-switch">
  <span class="ls-btn active" data-layer="standard">标准</span>
  <span class="ls-btn" data-layer="terrain">地形</span>
</div>'''
    c = c.replace('<div id="map"></div>', '<div id="map"></div>\n' + switch_html)

    # 3. Add CSS for the layer switch
    if is_dark:
        switch_css = '\n#layer-switch{position:absolute;top:4.5em;right:12px;z-index:1000;display:flex;gap:0;background:rgba(30,41,59,0.9);border:1px solid #334155;border-radius:8px;overflow:hidden;backdrop-filter:blur(8px)}\n.ls-btn{padding:6px 12px;font-size:12px;cursor:pointer;color:#94a3b8;transition:all .15s;user-select:none}\n.ls-btn.active{background:#334155;color:#fbbf24;font-weight:600}\n.ls-btn:not(.active):hover{color:#e2e8f0}'
    else:
        switch_css = '\n#layer-switch{position:absolute;top:4.5em;right:12px;z-index:1000;display:flex;gap:0;background:rgba(255,255,255,0.92);border:1px solid #f0ede6;border-radius:8px;overflow:hidden;backdrop-filter:blur(8px);box-shadow:0 1px 4px rgba(0,0,0,0.06)}\n.ls-btn{padding:6px 12px;font-size:12px;cursor:pointer;color:#a0987a;transition:all .15s;user-select:none}\n.ls-btn.active{background:#efece4;color:#7a6a4a;font-weight:600}\n.ls-btn:not(.active):hover{color:#3d3929}'

    # Insert before the map-section closing or at the end of map-section CSS
    # Actually, insert it in the style section before the mobile media query
    if is_dark:
        insert_point = '@media(max-width:640px){#map{height:280px;touch-action:pan-y}}'
    else:
        insert_point = '@media(max-width:640px){#map{height:280px;touch-action:pan-y}}'

    c = c.replace(insert_point, switch_css + '\n' + insert_point)

    # 4. Replace the tile initialization and add layer switching logic
    # Dark version tiles
    if is_dark:
        tiles_js = '''var standardTile = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {maxZoom:19, attribution:''});
var terrainTile = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}', {maxZoom:18, attribution:''});
standardTile.addTo(map);
document.getElementById('layer-switch').addEventListener('click', function(e){
  var btn = e.target.closest('.ls-btn');
  if(!btn || btn.classList.contains('active')) return;
  document.querySelectorAll('.ls-btn').forEach(function(b){b.classList.remove('active')});
  btn.classList.add('active');
  if(btn.dataset.layer === 'standard'){map.removeLayer(terrainTile);standardTile.addTo(map)}
  else{map.removeLayer(standardTile);terrainTile.addTo(map)}
});'''
    else:
        tiles_js = '''var standardTile = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {maxZoom:19, attribution:''});
var terrainTile = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}', {maxZoom:18, attribution:''});
standardTile.addTo(map);
document.getElementById('layer-switch').addEventListener('click', function(e){
  var btn = e.target.closest('.ls-btn');
  if(!btn || btn.classList.contains('active')) return;
  document.querySelectorAll('.ls-btn').forEach(function(b){b.classList.remove('active')});
  btn.classList.add('active');
  if(btn.dataset.layer === 'standard'){map.removeLayer(terrainTile);standardTile.addTo(map)}
  else{map.removeLayer(standardTile);terrainTile.addTo(map)}
});'''

    # Remove the old tiles variable and map layer control
    # The old code has:
    # var tiles = { ... };
    # var map = L.map(...)
    # map.addLayer(tiles['Positron 浅灰']);
    # L.control.layers(tiles, null, ...).addTo(map);

    # Replace the tiles object and layer control with new code
    old_tiles_block = re.search(r"var tiles = \{.*?\};", c, re.DOTALL)
    if old_tiles_block:
        c = c.replace(old_tiles_block.group(), tiles_js)
        print(f"  {fname}: tiles replaced")
    else:
        print(f"  {fname}: WARNING - tiles block not found!")

    # Replace: map.addLayer(tiles['...']) since we already did standardTile.addTo(map)
    # Actually, the map init has: var map = L.map('map', { center: [36.5, 113.5], zoom: 8, ..., layers: [tiles['Positron 浅灰']] });
    # We need to replace the layers in the map init
    c = c.replace("layers: [tiles['Positron 浅灰']]", "layers: [standardTile]")

    # Also remove any remaining tileLayer calls from tiles object
    c = c.replace("'Esri 地形 中文': L.tileLayer(", "//'Esri 地形 中文': L.tileLayer(")

    with open(fname, 'w') as f:
        f.write(c)

    # JS syntax check
    scripts = re.findall(r'<script>(.*?)</script>', c, re.DOTALL)
    for s in scripts:
        if 'var standardTile' in s:
            with open(f'/tmp/{fname}_check.js', 'w') as f:
                f.write(s)
            break

    print(f"  {fname}: {os.path.getsize(fname)} bytes")

print("\nDone. Running syntax check...")
os.system("node --check /tmp/jindongnan-route-dark.html_check.js 2>&1 && echo '✓ Dark JS OK' || echo '✗ Dark JS FAIL'")
os.system("node --check /tmp/jindongnan-route-light.html_check.js 2>&1 && echo '✓ Light JS OK' || echo '✗ Light JS FAIL'")
