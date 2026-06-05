import os

for filename in ['jindongnan-route-dark.html', 'jindongnan-route-light.html']:
    with open(filename) as f:
        c = f.read()

    # 1. Remove border-left from day-cards
    c = c.replace('" style="border-left:4px solid #e74c3c">\n    <div class="day-header"><span class="day-label" style="color:#e74c3c">Day 1',
                  '">\n    <div class="day-header"><span class="day-label" style="color:#e74c3c">Day 1')
    c = c.replace('" style="border-left:4px solid #e67e22">\n    <div class="day-header"><span class="day-label" style="color:#e67e22">Day 2',
                  '">\n    <div class="day-header"><span class="day-label" style="color:#e67e22">Day 2')
    c = c.replace('" style="border-left:4px solid #ccb000">\n    <div class="day-header"><span class="day-label" style="color:#ccb000">Day 3',
                  '">\n    <div class="day-header"><span class="day-label" style="color:#ccb000">Day 3')
    c = c.replace('" style="border-left:4px solid #2ecc71">\n    <div class="day-header"><span class="day-label" style="color:#2ecc71">Day 4',
                  '">\n    <div class="day-header"><span class="day-label" style="color:#2ecc71">Day 4')
    c = c.replace('" style="border-left:4px solid #1abc9c">\n    <div class="day-header"><span class="day-label" style="color:#1abc9c">Day 5',
                  '">\n    <div class="day-header"><span class="day-label" style="color:#1abc9c">Day 5')
    c = c.replace('" style="border-left:4px solid #3498db">\n    <div class="day-header"><span class="day-label" style="color:#3498db">Day 6',
                  '">\n    <div class="day-header"><span class="day-label" style="color:#3498db">Day 6')
    c = c.replace('" style="border-left:4px solid #9b59b6">\n    <div class="day-header"><span class="day-label" style="color:#9b59b6">Day 7',
                  '">\n    <div class="day-header"><span class="day-label" style="color:#9b59b6">Day 7')

    # 2. Remove color from day-date spans (keep original class color)
    c = c.replace('<span class="day-date" style="color:#e74c3c">', '<span class="day-date">')
    c = c.replace('<span class="day-date" style="color:#e67e22">', '<span class="day-date">')
    c = c.replace('<span class="day-date" style="color:#ccb000">', '<span class="day-date">')
    c = c.replace('<span class="day-date" style="color:#2ecc71">', '<span class="day-date">')
    c = c.replace('<span class="day-date" style="color:#1abc9c">', '<span class="day-date">')
    c = c.replace('<span class="day-date" style="color:#3498db">', '<span class="day-date">')
    c = c.replace('<span class="day-date" style="color:#9b59b6">', '<span class="day-date">')

    # 3. Timeline: replace circled numbers with plain digits
    c = c.replace('<div class="stop-dot">①</div>', '<div class="stop-dot">1</div>')
    c = c.replace('<div class="stop-dot">②</div>', '<div class="stop-dot">2</div>')
    c = c.replace('<div class="stop-dot">③</div>', '<div class="stop-dot">3</div>')
    c = c.replace('<div class="stop-dot">④</div>', '<div class="stop-dot">4</div>')
    c = c.replace('<div class="stop-dot">⑤</div>', '<div class="stop-dot">5</div>')
    c = c.replace('<div class="stop-dot">⑥</div>', '<div class="stop-dot">6</div>')
    c = c.replace('<div class="stop-dot">⑦</div>', '<div class="stop-dot">7</div>')

    with open(filename, 'w') as f:
        f.write(c)

    size = os.path.getsize(filename)
    print(f"{filename}: {size} bytes — done")

print("All done.")
