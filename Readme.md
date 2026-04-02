# PlayZ-IPTV-Extractor

A reverse-engineered playlist extractor that decrypts and extracts thousands of IPTV channels from an encrypted Android streaming application. Generates a standard M3U playlist compatible with any IPTV player.


## Channels_List

All channels list can be found in CHANNELS_LIST.md file.
 
## What This Does
 
A popular sideloaded Android IPTV app encrypts its entire channel database behind multiple layers of AES encryption, root detection, traffic capture prevention, and code obfuscation. This tool cracks all of it and extracts every channel into a single M3U playlist you can use on any device.
 
**Output:** A `playlist.m3u` file with thousands of live TV channels, sports streams, movies, kids content, and more — complete with channel logos, categories, and metadata.
 
## The Reverse Engineering Journey
 
### APK Decompilation
 
Decompiled the target application using [jadx](https://github.com/skylot/jadx). The manifest revealed an aggressive permission set designed to prevent exactly what we're doing:
 
- Package scanning permission to detect traffic capture tools installed on the device
- Package installation permission for silent self-updates outside the Play Store
- Cleartext traffic enabled — streams served over plain HTTP
- Root/environment detection — app refuses to run if it detects a compromised environment
 
### Tracing the Data Flow
 
Followed the execution path from app launch to channel playback through heavily obfuscated code:
 
```
App Entry → Main Screen → Content Fragment
    → Fetches encrypted index files from remote API
    → Base URL resolved from local config store
    → HTTP response handler decrypts payload using embedded cipher
    → Parsed into structured channel objects with metadata
    → Each object references a secondary encrypted resource containing stream endpoints
    → Three-level encrypted indirection: index → channels → streams
```
 
### Extracting the API Endpoint
 
The base API URL was stored in the app's local configuration, with a fallback hosted on Firebase Remote Config. Extracted both offline using ADB with elevated privileges before the app's environment detection could block access.
 
### Cracking the Encryption
 
The app uses **AES-256-CBC with PKCS5 padding** and Base64-encoded ciphertext.
 
Here's where it got interesting — the codebase contains a decoy decryption method with hardcoded keys sitting in an obvious utility class. Naturally, that was the first thing found during decompilation. Those keys decrypt nothing useful.
 
The real encryption keys were buried deep in an HTTP response callback handler — a class that, based on its naming and package location, you'd never guess had anything to do with cryptography. Finding it required tracing the entire network request lifecycle from the initial fetch call through the response pipeline, across multiple abstraction layers of obfuscated callback interfaces.
 
### Decrypted Data Structure
 
The API serves a nested encrypted architecture:
 
```
Encrypted Index File
  → Decrypts to JSON array of category objects
    → Each category points to another encrypted file
      → Decrypts to JSON array of channel objects  
        → Each channel points to yet another encrypted file
          → Decrypts to JSON array with actual stream URLs and metadata
```
 
**Two category types discovered:**
- **Encrypted custom channels** — three levels of AES-encrypted indirection on the app's own servers
- **External M3U playlists** — direct URLs to public playlists from GitHub repos, CDNs, and third-party sources (some requiring custom headers passed via pipe-separated values in the URL)
 
### Bypassing Anti-Reverse-Engineering
 
| Protection | How It Was Bypassed |
|---|---|
| Environment detection | Extracted all config data offline via privileged shell access before the app could detect and block |
| Traffic capture prevention | App scans installed packages to find capture tools — made traffic capture unnecessary by extracting keys directly from decompiled source |
| Code obfuscation | Manual tracing through single-letter class names, renamed methods, and scattered package structures |
| Decoy cryptography | Identified and discarded the obvious cipher; traced the actual HTTP response pipeline to find the real decryption buried in an unrelated-looking callback class |
| Server-side request blocking | Reverse-engineered the HTTP client configuration to mimic the app's exact request headers, including parsing dynamically injected headers from playlist URL parameters |
| Dual data sources | Discovered the app serves both encrypted proprietary channels and external M3U playlists using different fetching and authentication strategies |
 
## Installation
 
```bash
git clone https://github.com/YOUR_USERNAME/PlayZ-IPTV-Extractor.git
cd PlayZ-IPTV-Extractor
pip install pycryptodome
```
 
## Usage
 
```bash
python build_all.py
```
 
The script will:
 
1. Fetch and decrypt category indexes from both content endpoints (general + sports)
2. For encrypted categories: decrypt the channel list, then fetch and decrypt each channel's stream URLs using **10 parallel threads**
3. For external M3U categories: fetch the playlist with appropriate headers and rewrite group metadata
4. Automatically retry failed requests up to 3 times
5. Save progress after every category — if interrupted, resume from where you stopped
6. Output `playlist.m3u` with all channels, updated incrementally as each category completes
 
### Generate Channel List
 
After running the extractor, generate a browsable channel list:
 
```bash
python generate_channel_list.py
```
 
This creates `CHANNELS_LIST.md` — a formatted list of every channel organized by category with counts. Check here: **[Full Channel List](CHANNELS_LIST.md)**
 
### Pre-built Playlist
 
Don't want to run the extractor yourself? Download the latest pre-built playlist:
 
**[Download playlist.m3u](https://github.com/Abdul-Moiz-i999/PlayZ-IPTV-Extractor/releases/download/v1.0/playlist.m3u)**
 
> Note: Stream URLs expire and change frequently. The pre-built playlist may have dead links. For the freshest results, run the extractor yourself.
 
### Features
 
- **Multithreaded** — 10 concurrent workers per category, ~10x faster than sequential extraction
- **Auto-retry** — each request retries 3 times before failing, handles transient network issues
- **Resume support** — progress checkpointed to disk after every category; re-run to continue from where you stopped
- **Incremental saves** — playlist file updated after each category, partial results always available even if the script crashes
- **Full metadata** — M3U entries include `tvg-id`, `tvg-name`, `tvg-logo`, and `group-title` for rich IPTV player display
- **Custom header support** — parses pipe-separated headers from playlist URLs to bypass server-side request validation
- **VLC compatibility** — preserves `#EXTVLCOPT` tags from source playlists for proper playback with required HTTP headers
 
### Output Format
 
```
#EXTM3U
#EXTINF:-1 tvg-id="ChannelName.tv" tvg-name="Channel Name" tvg-logo="https://example.com/logo.png" group-title="Category", Channel Name
https://stream.example.com/live/channel/master.m3u8
```
 
### Recommended Players
 
| Player | Platform | Logos | Groups | Notes |
|---|---|---|---|---|
| **IPTV Smarters (RECOMMENDED)** | PC, Android, iOS | Yes | Yes | Best overall experience with full metadata |
| **VLC** | PC | No | List only | Use `Ctrl+L` for playlist view, `Ctrl+N` for network streams |
| **Kodi + PVR IPTV Simple Client** | PC, Android | Yes | Yes | Free, open source, highly customizable |
| **PotPlayer** | PC | No | List only | Lightweight alternative to VLC |
 
## Project Structure
 
```
PlayZ-IPTV-Extractor/
├── build_all.py              # Main extractor — multithreaded with resume support
├── generate_channel_list.py  # Generates CHANNELS_LIST.md from playlist.m3u
├── CHANNELS_LIST.md               # Browsable list of all extracted channels
├── requirements.txt          # Python dependencies
└── README.md                 # You are here
```
 
## Technical Summary
 
| Component | Detail |
|---|---|
| Encryption | AES-256-CBC, PKCS5 padding, Base64 encoded |
| Key Location | Embedded in HTTP response callback handler (not the decoy utility class) |
| API Config | Firebase Remote Config + local preference store |
| HTTP Client | OkHttp-based, mimicked user-agent and custom headers |
| Data Architecture | Three-level nested encrypted JSON |
| Threading | 10 concurrent workers using Python's ThreadPoolExecutor |
| Resilience | 3 retries per request, checkpoint-based resume, incremental playlist saves |
 
## How It Was Built
 
This wasn't a weekend project. The extraction required:
 
1. **APK decompilation** and reading thousands of lines of obfuscated Java
2. **Identifying a decoy** encryption key that wasted hours before the real one was found
3. **Tracing callback chains** across 6+ abstraction layers to find where decryption actually happens
4. **Extracting config data** via ADB before the app's environment detection could intervene
5. **Handling two completely different data source types** (encrypted API vs external M3U) with different authentication requirements
6. **Multiple iterations** of the extraction script — from single-threaded proof of concept to the final multithreaded, crash-resilient version


## A Note on Longevity

This tool works by exploiting the app's current encryption scheme, API endpoints, and server configuration. Any of these could change without notice — new keys, new endpoints, new obfuscation layers. If that happens, the extractor will break.

I'll try to keep up with changes when I can, but no promises. This project started because I was tired of squinting at IPTV on my phone and just wanted to watch on my PC. The reverse engineering rabbit hole turned out to be way deeper (and more fun) than expected, but at the end of the day — my playlist is generated, my channels are playing on a proper screen, and the itch is scratched.

If it breaks and you're feeling adventurous, the methodology documented above should point you in the right direction to crack it again yourself. That's the real takeaway here — not the playlist, but the process.