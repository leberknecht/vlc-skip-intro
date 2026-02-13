# VLC Skip Intro Extensions

Automatically skip TV show intros in VLC using pre-detected timestamps!

## 📦 Two Versions Available

### 🚀 Standalone Version (RECOMMENDED)
**Pure Lua - No Python dependency at runtime!**

Perfect for:
- Media centers and TV boxes
- Systems without Python
- Easy distribution to multiple machines
- Non-technical users

[📖 Read more](README_STANDALONE.md) | [🔧 Quick Start](#standalone-quick-start)

### 🐍 Python Version (Original)
**Direct database access**

Perfect for:
- Development machines
- Systems with Python installed
- Automatic database updates

[📖 Read more](INSTALLATION_GUIDE.md) | [🔧 Quick Start](#python-quick-start)

**Not sure which to choose?** See [COMPARISON.md](COMPARISON.md)

---

## 🎯 Features

- ✨ **Automatic Detection**: Matches videos by OpenSubtitles hash or file path
- ⚡ **Seamless Skipping**: Automatically jumps over intros
- 🎬 **Non-intrusive**: Brief OSD message when skipping
- 🔒 **Reliable**: Dual matching (hash + path) for maximum compatibility
- 📊 **Accurate**: Uses audio fingerprinting for precise detection

---

## 🚀 Standalone Quick Start

**Best for most users - no Python needed on VLC machine!**

```bash
# 1. Export database to JSON cache (requires Python once)
cd vlc-plugin
python3 export_db_cache.py ../intro_timestamps.db

# 2. Install to VLC
./install_standalone.sh

# 3. Restart VLC and enable: View → Skip Intro (Standalone)
```

**That's it!** The extension is now fully standalone with no dependencies.

### Updating After Adding New Intros

```bash
# Quick update script
./update_cache.sh
```

This exports the database and copies the cache to VLC automatically.

---

## 🐍 Python Quick Start

**For development machines with Python**

```bash
# 1. Install
cd vlc-plugin
./install.sh

# 2. Restart VLC and enable: View → Skip Intro
```

Database updates are automatically detected!

---

## 📚 How It Works

### Step 1: Detect Intros (One Time Per Show)

Use the audio scanner to detect intro timestamps:

```bash
cd /home/delf/dev/vlc-skip-intro

uv run python intro-detection/audio-scan.py \
  "/path/to/episode.mkv" \
  "intro-sequences/show-intro.wav"
```

This:
- Calculates the video's OpenSubtitles hash
- Finds the intro using audio fingerprinting
- Saves to `intro_timestamps.db`

### Step 2: VLC Extension Auto-Skips

When you play any episode:
1. Extension calculates video hash
2. Looks up intro times in database/cache
3. Automatically skips when intro starts
4. Shows "⏭ Intro skipped!" message

**Works for:**
- Different file paths (same episode, different location)
- Renamed files (matches by content hash)
- Network shares and local files

---

## 🗂️ File Structure

```
vlc-plugin/
├── skip_intro_standalone.lua    # Standalone version (pure Lua)
├── skip_intro.lua                # Python version (Lua)
├── intro_checker.py              # Python helper
├── export_db_cache.py            # Export DB to JSON
├── intro_timestamps_cache.json   # JSON cache (generated)
├── install_standalone.sh         # Install standalone
├── install.sh                    # Install Python version
├── update_cache.sh               # Quick cache update
├── README.md                     # This file
├── README_STANDALONE.md          # Standalone docs
├── INSTALLATION_GUIDE.md         # Python version docs
└── COMPARISON.md                 # Version comparison
```

---

## 🎬 Usage Example

### First Time: Scan an Intro

```bash
# Extract intro audio from any episode (first 2-3 minutes is usually good)
ffmpeg -i "Show.S01E01.mkv" -t 180 -q:a 0 intro.wav

# Scan all episodes in a season
for ep in /media/shows/Season\ 1/*.mkv; do
  uv run python intro-detection/audio-scan.py "$ep" intro.wav
done
```

### Playback: Automatic Skipping

1. Open VLC
2. Enable extension: **View → Skip Intro** (or **Skip Intro (Standalone)**)
3. Play any episode
4. Intro is automatically skipped! ⏭

### Update Database

When you add more episodes:

**Standalone:**
```bash
./update_cache.sh
```

**Python version:** No action needed - updates automatically!

---

## 🔧 Configuration

### Skip Timing

Edit the `.lua` file:

```lua
local check_interval = 0.5  -- How often to check position (seconds)
```

### Cache/Database Location

The extension searches for files in these locations:

**Standalone** (`intro_timestamps_cache.json`):
- `~/.local/share/vlc/lua/extensions/`
- `~/dev/vlc-skip-intro/vlc-plugin/`
- `~/`

**Python** (`intro_timestamps.db`):
- `~/.local/share/vlc/lua/extensions/`
- `~/dev/vlc-skip-intro/`
- `~/`

---

## 🐛 Troubleshooting

### Extension Not Visible in Menu

```bash
# Check files are in place
ls -l ~/.local/share/vlc/lua/extensions/skip_intro*.lua

# Restart VLC completely
pkill vlc && vlc
```

### Intro Not Skipped

**Enable debug logs:**
1. VLC → Tools → Messages (Ctrl+M)
2. Set Verbosity to **2 - Debug**
3. Look for `[Skip Intro]` messages

**Expected output:**
```
[Skip Intro] Extension activated
[Skip Intro] Checking file: /path/to/episode.mkv
[Skip Intro] Hash: 5d7d82efcdded0f5
[Skip Intro] ✓ Found entry by hash
[Skip Intro] Intro: 352.00 - 459.00
[Skip Intro] ⏭ Skipping: 352.00s → 459.00s
```

**Common issues:**

| Issue | Solution |
|-------|----------|
| "Cache/DB not found" | Copy cache/database to VLC extensions directory |
| "Could not calculate hash" | Check file permissions |
| "No intro data found" | Verify entry in database: `sqlite3 intro_timestamps.db "SELECT * FROM intro_timestamps;"` |
| Hash mismatch | Re-scan the episode with audio-scan.py |

### Test Components Individually

**Standalone:**
```bash
# Test JSON cache parsing
grep -A 5 "5d7d82efcdded0f5" intro_timestamps_cache.json
```

**Python:**
```bash
# Test Python helper
python3 ~/.local/share/vlc/lua/extensions/intro_checker.py "/path/to/episode.mkv"
```

---

## 📊 Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Hash calculation | 50-100ms | Once per file |
| Cache loading | 10ms | Once at startup (standalone) |
| Database query | 20-50ms | Once per file (Python) |
| Position check | <1ms | Every 0.5s |
| Memory per entry | ~1KB | Standalone cache |

---

## 🌟 Advanced Usage

### Multi-Machine Setup

**Development machine** (with Python):
```bash
# Scan episodes
uv run python intro-detection/audio-scan.py *.mkv intro.wav

# Export cache
python3 export_db_cache.py intro_timestamps.db
```

**Media center** (no Python):
```bash
# Copy cache file
scp intro_timestamps_cache.json mediapc:~/.local/share/vlc/lua/extensions/
```

### Batch Processing

```bash
# Scan entire TV show
find /media/shows/MyShow -name "*.mkv" | while read ep; do
  uv run python intro-detection/audio-scan.py "$ep" intro.wav
done

# Update VLC cache
./update_cache.sh
```

### Custom Thresholds

Edit `intro-detection/audio-scan.py`:

```python
CORRELATION_THRESHOLD = 0.65      # Lower = more lenient matching
REFINEMENT_THRESHOLD = 0.8        # Threshold for precise match
SLIDE_INTERVAL = 5                # Seconds between checks
```

---

## 📖 Documentation

- **[COMPARISON.md](COMPARISON.md)** - Which version should you use?
- **[README_STANDALONE.md](README_STANDALONE.md)** - Standalone version details
- **[INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)** - Python version details

---

## 🤝 Contributing

Ideas for improvements:

- [ ] Auto-reload cache when file changes
- [ ] Configuration UI in VLC
- [ ] Skip button option (instead of auto-skip)
- [ ] Multiple intro segments per episode
- [ ] Skip statistics and analytics
- [ ] Cloud sync for shared databases
- [ ] Machine learning for better detection

---

## 📝 License

Part of the VLC Skip Intro project.

---

## 🎉 Quick Reference

### Current Database Status

```bash
# View all entries
sqlite3 intro_timestamps.db "SELECT video_path, start_time, end_time, movie_hash FROM intro_timestamps;"

# Count entries
sqlite3 intro_timestamps.db "SELECT COUNT(*) FROM intro_timestamps;"

# Check specific hash
sqlite3 intro_timestamps.db "SELECT * FROM intro_timestamps WHERE movie_hash='5d7d82efcdded0f5';"
```

### Your Current Setup

Based on your recent scan:

```
File: Star.Trek.Deep.Space.Nine.S02E12...
Hash: 5d7d82efcdded0f5
Intro: 05:52 - 07:39 (352s - 459s)
Correlation: 0.9428 (excellent!)
```

This episode will now automatically skip its intro in VLC! 🎉
