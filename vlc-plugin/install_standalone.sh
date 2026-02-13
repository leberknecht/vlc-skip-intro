#!/bin/bash
# Installation script for VLC Skip Intro extension (Standalone version - no Python dependency!)

set -e

echo "Installing VLC Skip Intro extension (Standalone)..."

# Determine OS and set paths
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    VLC_EXTENSIONS_DIR="$HOME/.local/share/vlc/lua/extensions"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    VLC_EXTENSIONS_DIR="$HOME/Library/Application Support/org.videolan.vlc/lua/extensions"
else
    echo "Error: Unsupported OS. Please install manually."
    exit 1
fi

# Create extensions directory if it doesn't exist
mkdir -p "$VLC_EXTENSIONS_DIR"

# Export database cache if database exists
if [ -f "../intro_timestamps.db" ]; then
    echo "Exporting database cache..."
    python3 export_db_cache.py ../intro_timestamps.db intro_timestamps_cache.json
elif [ -f "intro_timestamps_cache.json" ]; then
    echo "Using existing cache file..."
else
    echo "Warning: No database or cache file found!"
    echo "You'll need to run: python3 export_db_cache.py"
fi

# Copy files
echo "Copying files to $VLC_EXTENSIONS_DIR..."
cp skip_intro_intf.lua "$VLC_EXTENSIONS_DIR/"

if [ -f "intro_timestamps_cache.json" ]; then
    cp intro_timestamps_cache.json "$VLC_EXTENSIONS_DIR/"
    echo "✓ Cache file copied"
fi

echo ""
echo "✓ Installation complete!"
echo ""
echo "Next steps:"
echo "1. Restart VLC if it's running"
echo "2. Go to View > Skip Intro (Standalone) to activate the extension"
echo ""
echo "To update the intro database:"
echo "1. Run: python3 export_db_cache.py /path/to/intro_timestamps.db"
echo "2. Copy intro_timestamps_cache.json to: $VLC_EXTENSIONS_DIR/"
echo ""
echo "NO PYTHON REQUIRED AT RUNTIME! ✨"
