import os, re

for fname in ['jindongnan-route-dark.html', 'jindongnan-route-light.html']:
    with open(fname) as f:
        c = f.read()

    # Find the broken order and fix it
    # Old: 
    #   var standardTile = L.tileLayer(...)
    #   var terrainTile = L.tileLayer(...)
    #   standardTile.addTo(map)
    #   document.getElementById(...).addEventListener(...)
    #   var map = L.map('map', { ... layers: [standardTile] });
    #
    # New:
    #   var map = L.map('map', { ... });
    #   var standardTile = L.tileLayer(...)
    #   var terrainTile = L.tileLayer(...)
    #   standardTile.addTo(map)
    #   document.getElementById(...).addEventListener(...)

    # Move map init before tile creation
    # Find the map init line and the tile lines
    old_pattern = '''var standardTile = L.tileLayer('https://{s}.basemaps.cartocdn.com/'''
    map_line = '''var map = L.map('map', { center: [36.5, 113.5], zoom: 8, scrollWheelZoom: true, attributionControl: false, zoomControl: true, layers: [standardTile] });'''

    if old_pattern in c:
        # Extract the standardTile and terrainTile declarations
        idx_std = c.find('var standardTile')
        idx_tiles_end = c.find('});', c.find('terrainTile')) + 3
        tiles_block = c[idx_std:idx_tiles_end]
        
        idx_map = c.find('var map = L.map')
        idx_map_end = c.find('});', idx_map) + 3
        map_block = c[idx_map:idx_map_end]
        
        # Get the event listener block that comes between
        idx_listener = c.find("document.getElementById('layer-switch')", idx_tiles_end)
        idx_listener_end = c.find('});', idx_listener) + 3
        listener_block = c[idx_listener:idx_listener_end]
        
        # Reorder: map first, then tiles, then listener
        new_order = map_block + '\n' + tiles_block + '\n' + standardTile_addTo_and_listener
        
        print(f"  {fname}: reordering...")
        print(f"    tiles at: {idx_std}, map at: {idx_map}")

    # Simpler approach: just swap the blocks directly by finding exact positions
    idx_std = c.find('\nvar standardTile')
    idx_map = c.find('\nvar map = L.map')
    
    if idx_std > 0 and idx_map > 0 and idx_std < idx_map:
        # Extract the three blocks
        # Block 1: var standardTile ... to before var map
        block1_end = idx_map
        block1 = c[idx_std:block1_end]
        
        # Block 2: var map = L.map(...);
        block2_end = c.find('});', idx_map) + 3
        block2 = c[idx_map:block2_end]
        
        # Block 3: event listener code (after map)
        block3_start = block2_end
        # Find the next realistic code start
        remaining = c[block3_start:]
        
        # Reconstruct: standardTile block then map block (but keep standardTile.addTo(map) in block1)
        # Actually the issue is standardTile.addTo(map) in block1, and map defined in block2
        # Solution: move map block BEFORE the addTo call, OR move the addTo AFTER map
        
        # Simplest fix: extract addTo and listener, move them after map
        addTo_idx = c.find('standardTile.addTo(map)', idx_std)
        listener_idx = c.find("document.getElementById('layer-switch')")
        end_of_code = c.find('\n\n', listener_idx) if listener_idx > 0 else c.find('\n}\n', listener_idx)
        if end_of_code < 0:
            end_of_code = listener_idx + 400
        
        # Build: standardTile + terrainTile declarations, then map, then addTo + listener
        tiles_decl = c[idx_std:addTo_idx].rstrip()
        add_to = 'standardTile.addTo(map);'
        listener_code = c[listener_idx:listener_idx + 400]
        # Truncate listener at next var
        next_var = listener_code.find('\nvar ')
        if next_var > 0:
            listener_code = listener_code[:next_var].rstrip()
        
        new_code = tiles_decl + '\n' + block2 + '\n' + add_to + '\n' + listener_code
        
        old_code = c[idx_std:idx_std + len(tiles_decl) + len(add_to) + (block2_end - idx_map) + (listener_idx + 400 - idx_std - len(tiles_decl) - len(add_to))]
        actual_end = listener_idx + len(listener_code) - (listener_idx - idx_std)
        
        # Safer: just replace the specific addTo line and move it
        c_fixed = c.replace('standardTile.addTo(map);', '', 1)
        c_fixed = c_fixed.replace('var map = L.map', 'standardTile.addTo(map);\n' + 'var map = L.map', 1)
        
        # But also need to handle the event listener which references map
        # The listener is after map so it should be fine
        
        with open(fname, 'w') as f:
            f.write(c_fixed)
        
        print(f"  {fname}: reordered")

    # Verify
    with open(fname) as f:
        c2 = f.read()
    
    idx_std2 = c2.find('standardTile.addTo(map)')
    idx_map2 = c2.find('var map = L.map')
    
    if idx_std2 > 0 and idx_map2 > 0:
        if idx_std2 > idx_map2:
            print(f"    ✓ addTo after map (correct)")
        else:
            print(f"    ✗ addTo still before map!")
    
    # JS check
    scripts = re.findall(r'<script>(.*?)</script>', c2, re.DOTALL)
    for s in scripts:
        if 'var standardTile' in s:
            with open(f'/tmp/{fname}_check2.js', 'w') as f:
                f.write(s)
            break

print("\nSyntax check:")
os.system("node --check /tmp/jindongnan-route-dark.html_check2.js 2>&1 && echo '✓ Dark' || echo '✗ Dark'")
os.system("node --check /tmp/jindongnan-route-light.html_check2.js 2>&1 && echo '✓ Light' || echo '✗ Light'")
