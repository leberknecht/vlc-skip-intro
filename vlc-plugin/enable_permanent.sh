#!/bin/bash
# Enable Skip Intro permanently in VLC

VLC_CONFIG="$HOME/.config/vlc/vlcrc"

echo "Enabling Skip Intro permanently in VLC..."
echo ""

# Backup current config
if [ -f "$VLC_CONFIG" ]; then
    cp "$VLC_CONFIG" "$VLC_CONFIG.backup.$(date +%Y%m%d%H%M%S)"
    echo "✓ Backed up current config"
fi

# Check if extraintf line exists
if grep -q "^extraintf=" "$VLC_CONFIG" 2>/dev/null; then
    # Update existing line
    sed -i 's/^extraintf=.*/extraintf=luaintf/' "$VLC_CONFIG"
    echo "✓ Updated extraintf setting"
else
    # Add new line
    echo "extraintf=luaintf" >> "$VLC_CONFIG"
    echo "✓ Added extraintf setting"
fi

# Check if lua-intf line exists
if grep -q "^lua-intf=" "$VLC_CONFIG" 2>/dev/null; then
    # Update existing line
    sed -i 's/^lua-intf=.*/lua-intf=skip_intro/' "$VLC_CONFIG"
    echo "✓ Updated lua-intf setting"
else
    # Add new line
    echo "lua-intf=skip_intro" >> "$VLC_CONFIG"
    echo "✓ Added lua-intf setting"
fi

echo ""
echo "========================================="
echo "✓ Skip Intro is now PERMANENTLY enabled!"
echo "========================================="
echo ""
echo "Just start VLC normally and it will:"
echo "- Automatically load the skip intro script"
echo "- Monitor all videos for intros"
echo "- Skip intros when detected"
echo ""
echo "No need to activate anything - it just works!"
echo ""
echo "To disable later, edit: $VLC_CONFIG"
echo "and remove the lines starting with 'extraintf' and 'lua-intf'"
