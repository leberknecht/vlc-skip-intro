#!/bin/bash
# Test VLC Skip Intro

VIDEO="/media/nfs-series/star trek ds9/Staffel 2/Star.Trek.Deep.Space.Nine.S02E12.German.AC3.DL.1080p.WebHD.x265-FuN.mkv"

echo "========================================="
echo "Testing VLC Skip Intro Interface Script"
echo "========================================="
echo ""
echo "This will:"
echo "1. Start VLC with the skip intro interface"
echo "2. Open the DS9 episode"
echo "3. Show debug messages in the terminal"
echo ""
echo "Watch for '[Skip Intro]' messages"
echo "The intro should skip at 05:52 (352 seconds)"
echo ""
echo "Press Ctrl+C to stop"
echo ""
sleep 3

vlc --extraintf=luaintf --lua-intf=skip_intro --verbose 2 "$VIDEO" 2>&1 | grep --line-buffered -E "\[skip_intro\]|\[Skip Intro\]|skip.intro"
