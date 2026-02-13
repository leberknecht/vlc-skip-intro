#!/usr/bin/env python3
"""
Export intro_timestamps.db to a simple JSON cache file.
Run this script whenever you update the database.

Usage:
    python3 export_db_cache.py [database_path] [output_path]

Defaults:
    database_path: ../intro_timestamps.db
    output_path: intro_timestamps_cache.json
"""

import sqlite3
import json
import sys
from pathlib import Path


def export_database_to_json(db_path, output_path):
    """Export database to JSON format that Lua can easily parse."""

    if not Path(db_path).exists():
        print(f"Error: Database not found at {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Fetch all entries
    cursor.execute("""
        SELECT file_name, movie_hash, file_size, start_time, end_time, correlation_score, outro_length
        FROM intro_timestamps
        ORDER BY id DESC
    """)

    entries = []
    hash_map = {}
    filename_map = {}

    for row in cursor.fetchall():
        file_name, movie_hash, file_size, start_time, end_time, correlation_score, outro_length = row

        # Handle binary data
        if isinstance(movie_hash, bytes):
            movie_hash = movie_hash.decode('utf-8')

        entry = {
            'file_name': file_name,
            'movie_hash': movie_hash,
            'file_size': file_size,
            'start_time': float(start_time),
            'end_time': float(end_time),
            'correlation_score': float(correlation_score) if not isinstance(correlation_score, bytes) else 0.0,
            'outro_length': float(outro_length) if outro_length is not None else 0.0
        }

        entries.append(entry)

        # Build lookup maps
        if movie_hash:
            hash_map[movie_hash] = entry
        if file_name:
            filename_map[file_name] = entry

    conn.close()

    # Create compact output format
    output = {
        'version': 1,
        'entries': entries,
        'by_hash': hash_map,
        'by_file': filename_map
    }

    # Write to file
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"✓ Exported {len(entries)} entries to {output_path}")
    print(f"  By hash: {len(hash_map)} entries")
    print(f"  By path: {len(filename_map)} entries")

    return True


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "../intro_timestamps.db"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "intro_timestamps_cache.json"

    export_database_to_json(db_path, output_path)
