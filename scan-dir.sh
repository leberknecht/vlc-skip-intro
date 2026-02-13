#!/bin/bash

echo $1
find "$1" -type f -exec uv run python intro-detection/audio-scan.py {} $2 \;
