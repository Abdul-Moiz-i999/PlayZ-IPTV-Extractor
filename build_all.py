from Crypto.Cipher import AES
import base64
import json
import urllib.request
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

key = b"m5Kl5nk4xK1kN7pN"
iv = b"k5K4nM8mKlNL7l15"
base_url = "https://adsflw.xyz/"
hdrs = {"User-Agent": "okhttp/4.12.0"}
WORKERS = 10
RETRIES = 3
TIMEOUT = 15

lock = threading.Lock()
progress_file = "progress.json"

def decrypt(data):
    if data.startswith("[") or data.startswith("{"):
        return data
    cipher = AES.new(key, AES.MODE_CBC, iv)
    raw = base64.b64decode(data)
    decrypted = cipher.decrypt(raw)
    pad = decrypted[-1]
    return decrypted[:-pad].decode("utf-8")

def fetch(url, custom_headers=None):
    h = custom_headers if custom_headers else hdrs
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers=h)
            return urllib.request.urlopen(req, timeout=TIMEOUT).read().decode("utf-8", errors="ignore").strip()
        except Exception as e:
            if attempt == RETRIES - 1:
                raise e

def make_tvg_id(name):
    return name.strip().replace(" ", "").replace("/", "").replace("&", "And") + ".tv"

def load_progress():
    if os.path.exists(progress_file):
        f = open(progress_file, "r")
        data = json.loads(f.read())
        f.close()
        return data
    return {"done": [], "entries": []}

def save_progress(done_list, entries):
    f = open(progress_file, "w")
    f.write(json.dumps({"done": done_list, "entries": entries}))
    f.close()

def process_custom_channel(ch, full_group):
    ch_name = ch.get("name", "?").strip()
    links_path = ch.get("links", "")
    logo = ch.get("logo", "")
    if not links_path:
        return []
    try:
        if links_path.startswith("http"):
            raw = fetch(links_path)
        else:
            raw = fetch(base_url + links_path)
        data = decrypt(raw)
        links = json.loads(data)
        entries = []
        for link in links:
            url = link.get("link", "")
            link_name = link.get("name", "")
            if url:
                if link_name and len(links) > 1:
                    label = ch_name + " - " + link_name
                else:
                    label = ch_name
                tvg_id = make_tvg_id(label)
                extinf = '#EXTINF:-1'
                extinf += ' tvg-id="' + tvg_id + '"'
                extinf += ' tvg-name="' + label + '"'
                if logo:
                    extinf += ' tvg-logo="' + logo + '"'
                extinf += ' group-title="' + full_group + '"'
                extinf += ', ' + label
                entries.append(extinf + "\n" + url)
        return entries
    except Exception as e:
        print("    Error fetching " + ch_name + ": " + str(e))
        return []

def process_m3u_category(api, full_group):
    try:
        parts = api.split("|")
        url = parts[0]
        custom_hdrs = dict(hdrs)
        for p in parts[1:]:
            if "=" in p:
                k, v = p.split("=", 1)
                if k.lower() == "user-agent":
                    custom_hdrs["User-Agent"] = v
                else:
                    custom_hdrs[k] = v
        data = fetch(url, custom_hdrs)
        lines = []
        prev_extinf = None
        extras = []
        for line in data.split("\n"):
            line = line.strip()
            if not line or line.startswith("#EXTM3U"):
                continue
            if line.startswith("#EXTINF"):
                if 'group-title="' in line:
                    try:
                        parts2 = line.split('group-title="')
                        before = parts2[0]
                        after = parts2[1].split('"', 1)
                        old_group = after[0]
                        line = before + 'group-title="' + full_group + " - " + old_group + '"' + after[1]
                    except (IndexError, Exception):
                        comma = line.find(",")
                        if comma > 0:
                            line = line[:comma] + ' group-title="' + full_group + '"' + line[comma:]
                else:
                    comma = line.find(",")
                    if comma > 0:
                        line = line[:comma] + ' group-title="' + full_group + '"' + line[comma:]
                prev_extinf = line
                extras = []
            elif line.startswith("#EXTVLCOPT"):
                extras.append(line)
            elif line.startswith("#"):
                continue
            else:
                if prev_extinf:
                    entry = prev_extinf
                    for ex in extras:
                        entry += "\n" + ex
                    entry += "\n" + line
                    lines.append(entry)
                    prev_extinf = None
                    extras = []
        return lines
    except Exception as e:
        print("    Error: " + str(e))
        return []

def process_category(cat, group_prefix, done_set):
    cat_name = cat.get("name", "?").strip()
    cat_type = cat.get("type", "")
    api = cat.get("api", "")
    full_group = group_prefix + cat_name if group_prefix else cat_name
    cat_key = full_group + "|" + api

    if cat_key in done_set:
        print("  SKIP (cached): " + full_group)
        return ([], cat_key)

    print("\n  Category: " + full_group + " (" + cat_type + ")")
    all_entries = []

    if cat_type == "m3u":
        all_entries = process_m3u_category(api, full_group)
        print("    Got " + str(len(all_entries)) + " streams")

    elif cat_type == "custom":
        try:
            if api.startswith("http"):
                raw = fetch(api)
            else:
                raw = fetch(base_url + api)
            data = decrypt(raw)
            channels = json.loads(data)
            channel_list = []
            for ch_item in channels:
                ch = json.loads(ch_item["channel"]) if "channel" in ch_item else ch_item
                if not ch.get("visible", True):
                    continue
                channel_list.append(ch)

            with ThreadPoolExecutor(max_workers=WORKERS) as executor:
                futures = {executor.submit(process_custom_channel, ch, full_group): ch.get("name", "?") for ch in channel_list}
                for future in as_completed(futures):
                    name = futures[future]
                    try:
                        entries = future.result()
                        if entries:
                            all_entries.extend(entries)
                            print("    " + name + " (" + str(len(entries)) + " links)")
                    except Exception as e:
                        print("    Error " + name + ": " + str(e))
        except Exception as e:
            print("    Error: " + str(e))

    return all_entries, cat_key


def write_playlist(entries):
    f = open("playlist.m3u", "w", encoding="utf-8")
    f.write("#EXTM3U\n")
    for entry in entries:
        f.write(entry + "\n")
    f.close()


print("=" * 50)
print("PlayZ TV Playlist Extractor")
print("Multithreaded | Auto-retry | Resume support")
print("=" * 50)

progress = load_progress()
done_set = set(progress["done"])
all_entries = progress["entries"]

if done_set:
    print("\nFound progress: " + str(len(done_set)) + " categories done, " + str(len(all_entries)) + " entries cached")
    resp = input("Resume from where you left off? (y/n): ").strip().lower()
    if resp != "y":
        done_set = set()
        all_entries = []
        if os.path.exists(progress_file):
            os.remove(progress_file)
        print("Starting fresh.\n")
    else:
        print("Resuming...\n")

# Process both sources
sources = [
    (base_url + "categories.txt", "", "CATEGORIES"),
    (base_url + "sports.txt", "Sports - ", "SPORTS"),
]

for source_url, prefix, label in sources:
    print("\n" + "=" * 50)
    print("FETCHING " + label)
    print("=" * 50)

    try:
        raw = fetch(source_url)
        data = decrypt(raw)
        cats = json.loads(data)
    except Exception as e:
        print("  Failed to fetch " + label + ": " + str(e))
        continue

    for item in cats:
        cat = json.loads(item["cat"])
        if not cat.get("visible", True):
            continue
        try:
            entries, cat_key = process_category(cat, prefix, done_set)
            all_entries.extend(entries)
            done_set.add(cat_key)
            save_progress(list(done_set), all_entries)
            write_playlist(all_entries)
        except Exception as e:
            print("  Error: " + str(e))

# Final save
write_playlist(all_entries)

# Clean up progress
if os.path.exists(progress_file):
    os.remove(progress_file)

count = len(all_entries)
print("\n" + "=" * 50)
print("DONE! " + str(count) + " entries saved to playlist.m3u")
print("=" * 50)