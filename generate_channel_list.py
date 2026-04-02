import re
import os

if not os.path.exists("playlist.m3u"):
    print("playlist.m3u not found")
    exit(1)

f = open("playlist.m3u", "r", encoding="utf-8")
data = f.read()
f.close()

categories = {}
total = 0

for match in re.finditer(r'group-title="([^"]*)"[^,]*,\s*(.+)', data):
    group = match.group(1)
    name = match.group(2).strip()
    if group not in categories:
        categories[group] = []
    categories[group].append(name)
    total += 1

parts = []
parts.append("# Channel List\n\n")
parts.append("Total channels: **" + str(total) + "** across **" + str(len(categories)) + "** categories\n\n---\n\n")
parts.append("## Categories\n\n| Category | Channels |\n|---|---|\n")

for group in sorted(categories.keys()):
    parts.append("| " + group + " | " + str(len(categories[group])) + " |\n")

parts.append("\n---\n\n")

for group in sorted(categories.keys()):
    channels = categories[group]
    parts.append("### " + group + "\n\n" + str(len(channels)) + " channels\n\n| # | Channel |\n|---|---|\n")
    for i, name in enumerate(channels):
        parts.append("| " + str(i + 1) + " | " + name + " |\n")
    parts.append("\n")

f = open("CHANNELS_LIST.md", "w", encoding="utf-8")
f.write("".join(parts))
f.close()

print("Generated CHANNELS_LIST.md")
print("Total: " + str(total) + " channels in " + str(len(categories)) + " categories")