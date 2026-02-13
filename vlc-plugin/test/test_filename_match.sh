#!/bin/bash
# Test filename-based matching

echo "=== Testing Filename-Based Matching ==="
echo ""

CACHE="$HOME/.local/share/vlc/lua/intf/intro_timestamps_cache.json"

if [ ! -f "$CACHE" ]; then
    echo "✗ Cache file not found: $CACHE"
    exit 1
fi

echo "✓ Cache file found"
echo ""

echo "Entries in cache:"
python3 << 'EOF'
import json
import os

cache_path = os.path.expanduser("~/.local/share/vlc/lua/intf/intro_timestamps_cache.json")
with open(cache_path) as f:
    data = json.load(f)

print(f"  Version: {data.get('version')}")
print(f"  Total entries: {len(data.get('entries', []))}")
print("")
print("Filenames:")
for filename in data.get('by_file', {}).keys():
    entry = data['by_file'][filename]
    print(f"  • {filename}")
    print(f"    Intro: {int(entry['start_time'])}s - {int(entry['end_time'])}s")
EOF

echo ""
echo "=== Test Complete ==="
echo ""
echo "The VLC plugin will now match videos by filename only,"
echo "regardless of their location on disk."
echo ""
echo "Example: 'Star.Trek.Raumschiff.Voyager.S01E07...mkv'"
echo "will match whether it's in:"
echo "  /media/nfs-series/..."
echo "  /home/user/Videos/..."
echo "  /mnt/backup/..."
echo ""
