#!/bin/bash

echo $1
DIR="$1"
INTRO="$2"
shift 2
find "$DIR" -type f -exec uv run python intro-detection/audio-scan.py {} "$INTRO" "$@" \;
