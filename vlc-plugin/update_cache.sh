#!/bin/bash
# Quick script to update VLC cache when database changes

set -e

DB_PATH="${1:-../intro_timestamps.db}"
CACHE_FILE="intro_timestamps_cache.json"

if [ ! -f "$DB_PATH" ]; then
    echo "Error: Database not found at $DB_PATH"
    echo "Usage: $0 [path/to/intro_timestamps.db]"
    exit 1
fi

echo "Exporting database to cache (filename-based)..."
python3 export_db_cache.py "$DB_PATH" "$CACHE_FILE"

# Determine VLC extensions directory
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    VLC_EXT_DIR="$HOME/.local/share/vlc/lua/extensions"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    VLC_EXT_DIR="$HOME/Library/Application Support/org.videolan.vlc/lua/extensions"
else
    echo "Warning: Unknown OS, not copying to VLC directory"
    exit 0
fi

# Copy to VLC if extension is installed
if [ -f "$VLC_EXT_DIR/skip_intro_standalone.lua" ]; then
    echo "Copying cache to VLC extensions directory..."
    cp "$CACHE_FILE" "$VLC_EXT_DIR/"
    echo "✓ Cache updated in VLC!"
    echo ""
    echo "The extension will use the new cache next time you play a video."
else
    echo "Note: VLC extension not found at $VLC_EXT_DIR"
    echo "Cache file saved to: $(pwd)/$CACHE_FILE"
fi
