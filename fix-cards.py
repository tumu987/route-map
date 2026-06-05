import os

route_colors = {
    1: '#e74c3c',
    2: '#e67e22',
    3: '#ccb000',
    4: '#2ecc71',
    5: '#1abc9c',
    6: '#3498db',
    7: '#9b59b6',
}

for filename in ['jindongnan-route-dark.html', 'jindongnan-route-light.html']:
    with open(filename) as f:
        c = f.read()

    # 1. Remove Hermes/G先生 text
    c = c.replace('由 Hermes Agent 为 G先生定制 · 2026年6月 · 深色版', '')
    c = c.replace('由 Hermes Agent 为 G先生定制 · 2026年6月 · 浅色版', '')
    c = c.replace('<div class="badge">🚗 G先生专属定制</div>', '')
    c = c.replace('🚗 G先生定制', '')

    # 2. Remove grid background from route-map ::before
    c = c.replace('.route-map::before { content: \'\'; position: absolute; top: 0; left: 0; right: 0; bottom: 0; background-image: linear-gradient(rgba(0,0,0,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(0,0,0,0.04) 1px, transparent 1px); background-size: 40px 40px; pointer-events: none; }', '')
    c = c.replace('.route-map::before { content: \'\'; position: absolute; top: 0; left: 0; right: 0; bottom: 0; background-image: linear-gradient(rgba(51,65,85,0.2) 1px, transparent 1px), linear-gradient(90deg, rgba(51,65,85,0.2) 1px, transparent 1px); background-size: 40px 40px; pointer-events: none; }', '')

    # 3. Add card colors matching route colors
    day_colors = {1: '#e74c3c', 2: '#e67e22', 3: '#ccb000', 4: '#2ecc71', 5: '#1abc9c', 6: '#3498db', 7: '#9b59b6'}

    for day_num, color in day_colors.items():
        # Day label - e.g. <span class="day-label">Day 1 · 6/8（一）</span>
        old_label = f'<span class="day-label">Day {day_num}'
        new_label = f'<span class="day-label" style="color:{color}">Day {day_num}'
        c = c.replace(old_label, new_label)

        # Day date - e.g. <span class="day-date">🚗 ...
        # Need to find the NEXT .day-date after the current day's label
        # Since replacements are sequential, the labels were already updated above
        pass

    # Since the date spans are harder to match sequentially, let me do specific replacements
    # Day 1 date
    c = c.replace(f'<span class="day-label" style="color:{day_colors[1]}">Day 1 · 6/8（一）</span><span class="day-date">',
                  f'<span class="day-label" style="color:{day_colors[1]}">Day 1 · 6/8（一）</span><span class="day-date" style="color:{day_colors[1]}">')
    c = c.replace(f'<span class="day-label" style="color:{day_colors[2]}">Day 2 · 6/9（二）</span><span class="day-date">',
                  f'<span class="day-label" style="color:{day_colors[2]}">Day 2 · 6/9（二）</span><span class="day-date" style="color:{day_colors[2]}">')
    c = c.replace(f'<span class="day-label" style="color:{day_colors[3]}">Day 3 · 6/10（三）</span><span class="day-date">',
                  f'<span class="day-label" style="color:{day_colors[3]}">Day 3 · 6/10（三）</span><span class="day-date" style="color:{day_colors[3]}">')
    c = c.replace(f'<span class="day-label" style="color:{day_colors[4]}">Day 4 · 6/11（四）</span><span class="day-date">',
                  f'<span class="day-label" style="color:{day_colors[4]}">Day 4 · 6/11（四）</span><span class="day-date" style="color:{day_colors[4]}">')
    c = c.replace(f'<span class="day-label" style="color:{day_colors[5]}">Day 5 · 6/12（五）</span><span class="day-date">',
                  f'<span class="day-label" style="color:{day_colors[5]}">Day 5 · 6/12（五）</span><span class="day-date" style="color:{day_colors[5]}">')
    c = c.replace(f'<span class="day-label" style="color:{day_colors[6]}">Day 6 · 6/13（六）</span><span class="day-date">',
                  f'<span class="day-label" style="color:{day_colors[6]}">Day 6 · 6/13（六）</span><span class="day-date" style="color:{day_colors[6]}">')
    c = c.replace(f'<span class="day-label" style="color:{day_colors[7]}">Day 7 · 6/14（日）</span><span class="day-date">',
                  f'<span class="day-label" style="color:{day_colors[7]}">Day 7 · 6/14（日）</span><span class="day-date" style="color:{day_colors[7]}">')

    # Also add border-left-color to day-card to make it match
    # Day 1 card border
    c = c.replace('<div class="day-card">\n    <div class="day-header"><span class="day-label" style="color:#e74c3c">Day 1',
                  '<div class="day-card" style="border-left:4px solid #e74c3c">\n    <div class="day-header"><span class="day-label" style="color:#e74c3c">Day 1')
    c = c.replace('<div class="day-card">\n    <div class="day-header"><span class="day-label" style="color:#e67e22">Day 2',
                  '<div class="day-card" style="border-left:4px solid #e67e22">\n    <div class="day-header"><span class="day-label" style="color:#e67e22">Day 2')
    c = c.replace('<div class="day-card">\n    <div class="day-header"><span class="day-label" style="color:#ccb000">Day 3',
                  '<div class="day-card" style="border-left:4px solid #ccb000">\n    <div class="day-header"><span class="day-label" style="color:#ccb000">Day 3')
    c = c.replace('<div class="day-card">\n    <div class="day-header"><span class="day-label" style="color:#2ecc71">Day 4',
                  '<div class="day-card" style="border-left:4px solid #2ecc71">\n    <div class="day-header"><span class="day-label" style="color:#2ecc71">Day 4')
    c = c.replace('<div class="day-card">\n    <div class="day-header"><span class="day-label" style="color:#1abc9c">Day 5',
                  '<div class="day-card" style="border-left:4px solid #1abc9c">\n    <div class="day-header"><span class="day-label" style="color:#1abc9c">Day 5')
    c = c.replace('<div class="day-card">\n    <div class="day-header"><span class="day-label" style="color:#3498db">Day 6',
                  '<div class="day-card" style="border-left:4px solid #3498db">\n    <div class="day-header"><span class="day-label" style="color:#3498db">Day 6')
    c = c.replace('<div class="day-card">\n    <div class="day-header"><span class="day-label" style="color:#9b59b6">Day 7',
                  '<div class="day-card" style="border-left:4px solid #9b59b6">\n    <div class="day-header"><span class="day-label" style="color:#9b59b6">Day 7')

    with open(filename, 'w') as f:
        f.write(c)

    size = os.path.getsize(filename)
    print(f"{filename}: {size} bytes — done")

print("All changes applied.")
