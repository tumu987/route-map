#!/usr/bin/env python3
""" 将 v0.1.1 的缓存坐标注入到生成版 HTML 的 r_2 和 r_4 """
import os, re

os.chdir("/home/xiaobu/route-map")

# 1. Read the generated HTML
with open("jindongnan-gen.html", "r") as f:
    html = f.read()
print(f"Generated HTML: {len(html)} chars")

# 2. Extract r_d2 from v0.1.1 (lines 7323-7748)
with open("jindongnan-route-light.html", "r") as f:
    v011 = f.read()
lines = v011.split('\n')

# Extract r_d2 definition (var r_d2 = [ ... ];)
r_d2_lines = []
in_r_d2 = False
for i, line in enumerate(lines, 1):
    if line.strip().startswith("var r_d2"):
        in_r_d2 = True
        # Rename to var r_2
        r_d2_lines.append(line.replace("var r_d2", "var r_2", 1))
    elif in_r_d2:
        r_d2_lines.append(line)
        if line.strip() == "];":
            break

r_d2_text = '\n'.join(r_d2_lines)
print(f"r_d2 block: {len(r_d2_text)} chars, {len(r_d2_lines)} lines")

# 3. Find the exact position of r_2 in generated HTML
# Pattern: "var r_2 = [[...]];" on a single line
r2_match = re.search(r'var r_2\s*=\s*\[\[.*?\]\];', html, re.DOTALL)
if r2_match:
    print(f"Found r_2 at pos {r2_match.start()}-{r2_match.end()}, length {r2_match.end()-r2_match.start()}")
    # Replace it with the multi-line r_d2
    html = html[:r2_match.start()] + r_d2_text + html[r2_match.end():]
    print(f"After r_2 replacement: {len(html)} chars")
else:
    print("ERROR: Could not find var r_2 in generated HTML!")
    # Let's try a simpler search
    idx = html.find("var r_2 = [[")
    if idx >= 0:
        end_idx = html.find("];\nvar r_3", idx)
        if end_idx >= 0:
            end_idx += 2  # include ];
            print(f"Found r_2 via find at {idx}-{end_idx}")
            html = html[:idx] + r_d2_text + "\n" + html[end_idx+1:]
            print(f"After r_2 replacement: {len(html)} chars")
        else:
            print("Could not find end of r_2")
    else:
        print("Could not find var r_2 at all")
        # Search for r_2 more carefully
        for pattern in ["var r_2", "r_2 =", "r_2"]:
            idx = html.find(pattern)
            if idx >= 0:
                print(f"Found '{pattern}' at pos {idx}")
                print(f"Context: ...{html[max(0,idx-20):idx+50]}...")

# 4. Replace r_4
# Find "var r_4 = [[...]];"  
r4_match = re.search(r'var r_4\s*=\s*\[\[.*?\]\];', html, re.DOTALL)
if r4_match:
    print(f"Found r_4 at pos {r4_match.start()}-{r4_match.end()}")
    # Extract D4 spur coordinates from v0.1.1 spurRoutes
    d4_start = v011.find("['#00bcd4', [       // Day 4: 长治local")
    if d4_start >= 0:
        d4_end = v011.find("]]", d4_start)
        d4_text = v011[d4_start:d4_end+2]
        print(f"D4 spur block: {len(d4_text)} chars")
        # Remove the ['#00bcd4',  prefix and trailing ]], keeping just the array
        # Format: ['#00bcd4', [coords...]]
        # We want: var r_4 = [coords...];
        # Extract just the inner array
        inner_start = d4_text.find("[", d4_text.find("["))  # second [
        if inner_start >= 0:
            inner = d4_text[inner_start:]  # [coords...]]
            if inner.endswith("]]"):
                inner = inner[:-2] + "]"  # remove trailing ]], add ]
            # Also remove the trailing comment "// Day 4: 长治local"
            inner_clean = re.sub(r',\s*//.*$', '', inner, flags=re.MULTILINE)
            r4_new = f"var r_4 = {inner_clean};\n"
            print(f"New r_4: {r4_new[:100]}...")
            html = html[:r4_match.start()] + r4_new + html[r4_match.end():]
            print(f"After r_4 replacement: {len(html)} chars")
        else:
            print("Could not find inner array")
    else:
        print("Could not find D4 spur in v0.1.1")
else:
    print("ERROR: Could not find var r_4")
    idx = html.find("var r_4 = [[")
    if idx >= 0:
        end_idx = html.find("];\nvar r_5", idx)
        if end_idx >= 0:
            end_idx += 2
            print(f"Found r_4 via find at {idx}-{end_idx}")
            # Simple D4 replacement with cached data
            # ... (same d4 extraction logic)
        else:
            print("Could not find end of r_4")

# 5. Write back
with open("jindongnan-gen.html", "w") as f:
    f.write(html)
print(f"\nFinal HTML: {len(html)} chars")
print("Done!")
