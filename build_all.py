from Crypto.Cipher import AES
import base64
import json
import urllib.request
import time

key = b"m5Kl5nk4xK1kN7pN"
iv = b"k5K4nM8mKlNL7l15"
base_url = "https://adsflw.xyz/"
hdrs = {"User-Agent": "okhttp/4.12.0"}

def decrypt(data):
    if data.startswith("[") or data.startswith("{"):
        return data
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = cipher.decrypt(base64.b64decode(data))
    pad = decrypted[-1]
    return decrypted[:-pad].decode("utf-8")

def fetch(url):
    req = urllib.request.Request(url, headers=hdrs)
    return urllib.request.urlopen(req, timeout=10).read().decode("utf-8", errors="ignore").strip()

def make_tvg_id(name):
    return name.strip().replace(" ", "").replace("/", "").replace("&", "And") + ".tv"

def process_categories(source_url, group_prefix=""):
    global m3u, count
    print("\nFetching: " + source_url)
    raw = fetch(source_url)
    data = decrypt(raw)
    categories = json.loads(data)

    for item in categories:
        cat = json.loads(item["cat"])
        if not cat.get("visible", True):
            continue
        cat_name = cat.get("name", "?").strip()
        cat_type = cat.get("type", "")
        api = cat.get("api", "")
        full_group = group_prefix + cat_name if group_prefix else cat_name
        print("\nCategory: " + full_group + " (" + cat_type + ")")

        if cat_type == "m3u":
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
                req = urllib.request.Request(url, headers=custom_hdrs)
                data2 = urllib.request.urlopen(req, timeout=10).read().decode("utf-8", errors="ignore").strip()
                for line in data2.split("\n"):
                    line = line.strip()
                    if line.startswith("#EXTINF"):
                        if 'group-title="' in line:
                            parts = line.split('group-title="')
                            before = parts[0]
                            after = parts[1].split('"', 1)
                            old_group = after[0]
                            line = before + 'group-title="' + full_group + " - " + old_group + '"' + after[1]
                        else:
                            comma = line.find(",")
                            if comma > 0:
                                line = line[:comma] + ' group-title="' + full_group + '"' + line[comma:]
                        m3u += line + "\n"
                    elif line and not line.startswith("#EXTM3U"):
                        m3u += line + "\n"
                        count += 1
            except Exception as e:
                print("  Error: " + str(e))
            time.sleep(0.3)

        elif cat_type == "custom":
            try:
                if api.startswith("http"):
                    raw2 = fetch(api)
                else:
                    raw2 = fetch(base_url + api)
                data2 = decrypt(raw2)
                channels = json.loads(data2)
                for ch_item in channels:
                    ch = json.loads(ch_item["channel"]) if "channel" in ch_item else ch_item
                    if not ch.get("visible", True):
                        continue
                    ch_name = ch.get("name", "?").strip()
                    links_path = ch.get("links", "")
                    logo = ch.get("logo", "")
                    is_playlist = ch.get("is_playlist", False)
                    link_names = ch.get("link_names", [])
                    if not links_path:
                        continue
                    try:
                        if links_path.startswith("http"):
                            raw3 = fetch(links_path)
                        else:
                            raw3 = fetch(base_url + links_path)
                        data3 = decrypt(raw3)
                        links = json.loads(data3)
                        for i, link in enumerate(links):
                            url = link.get("link", "")
                            link_name = link.get("name", "")
                            scheme = link.get("scheme", 0)
                            if url:
                                if link_name and len(links) > 1:
                                    label = ch_name + " - " + link_name
                                else:
                                    label = ch_name
                                tvg_id = make_tvg_id(label)
                                tvg_name = label
                                extinf = '#EXTINF:-1'
                                extinf += ' tvg-id="' + tvg_id + '"'
                                extinf += ' tvg-name="' + tvg_name + '"'
                                if logo:
                                    extinf += ' tvg-logo="' + logo + '"'
                                extinf += ' group-title="' + full_group + '"'
                                extinf += ', ' + label
                                m3u += extinf + "\n"
                                m3u += url + "\n"
                                count += 1
                                print("  " + label)
                        time.sleep(0.3)
                    except Exception as e:
                        print("  Error fetching " + ch_name + ": " + str(e))
            except Exception as e:
                print("  Error: " + str(e))


m3u = "#EXTM3U\n"
count = 0

# Fetch categories
print("=" * 50)
print("FETCHING CATEGORIES")
print("=" * 50)
process_categories(base_url + "categories.txt")

# Fetch sports
print("\n" + "=" * 50)
print("FETCHING SPORTS")
print("=" * 50)
process_categories(base_url + "sports.txt", "Sports - ")

# Save playlist
f = open("playlist.m3u", "w", encoding="utf-8")
f.write(m3u)
f.close()

print("\n" + "=" * 50)
print("Done! " + str(count) + " total streams saved to playlist.m3u")
print("Open in VLC (Ctrl+L for playlist) or any IPTV player")
print("=" * 50)