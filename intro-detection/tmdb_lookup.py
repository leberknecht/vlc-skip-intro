#!/usr/bin/env python3
import argparse
import os
import re
import sqlite3
import sys
import requests

TMDB_API_BASE = "https://api.themoviedb.org/3"
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "intro_timestamps.db")

def get_auth_header():
    token = os.environ.get("TMDB_API_TOKEN")
    if not token:
        print("Error: TMDB_API_TOKEN environment variable not set", file=sys.stderr)
        print("Get your API Read Access Token at https://www.themoviedb.org/settings/api", file=sys.stderr)
        sys.exit(1)
    return {"Authorization": f"Bearer {token}"}

def parse_filename(filepath):
    """Parse a filename to extract show/movie info."""
    filename = os.path.basename(filepath)
    name_without_ext = os.path.splitext(filename)[0]

    # Try TV show patterns first
    # Pattern: "Show Name S01E02" or "Show Name - S01E02"
    tv_pattern = r'^(.+?)[\s\-\.\_]+[Ss](\d{1,2})[Ee](\d{1,2})'
    match = re.search(tv_pattern, name_without_ext)
    if match:
        show_name = clean_title(match.group(1))
        season = int(match.group(2))
        episode = int(match.group(3))
        return {"type": "tv", "title": show_name, "season": season, "episode": episode}

    # Pattern: "Show Name 1x02" or "Show Name - 1x02"
    tv_pattern2 = r'^(.+?)[\s\-\.\_]+(\d{1,2})x(\d{1,2})'
    match = re.search(tv_pattern2, name_without_ext)
    if match:
        show_name = clean_title(match.group(1))
        season = int(match.group(2))
        episode = int(match.group(3))
        return {"type": "tv", "title": show_name, "season": season, "episode": episode}

    # Try movie patterns
    # Pattern: "Movie Name (2020)" or "Movie Name [2020]"
    movie_pattern = r'^(.+?)[\s\-\.\_]*[\(\[](\d{4})[\)\]]'
    match = re.search(movie_pattern, name_without_ext)
    if match:
        movie_name = clean_title(match.group(1))
        year = int(match.group(2))
        return {"type": "movie", "title": movie_name, "year": year}

    # Pattern: "Movie Name 2020" (year at end)
    movie_pattern2 = r'^(.+?)[\s\-\.\_]+(\d{4})(?:[\s\-\.\_]|$)'
    match = re.search(movie_pattern2, name_without_ext)
    if match:
        movie_name = clean_title(match.group(1))
        year = int(match.group(2))
        if 1900 <= year <= 2100:
            return {"type": "movie", "title": movie_name, "year": year}

    # Fallback: treat as movie without year
    title = clean_title(name_without_ext)
    return {"type": "unknown", "title": title}

def clean_title(title):
    """Clean up a title string."""
    # Remove common video quality indicators
    quality_patterns = [
        r'720p', r'1080p', r'2160p', r'4[kK]', r'[hH][dD][rR]',
        r'[bB][lL][uU][rR][aA][yY]', r'[wW][eE][bB][rR][iI][pP]',
        r'[xX]264', r'[xX]265', r'[hH]\.?264', r'[hH]\.?265',
        r'[aA][aA][cC]', r'[dD][tT][sS]', r'[aA][cC]3',
        r'[rR][eE][mM][uU][xX]', r'[pP][rR][oO][pP][eE][rR]'
    ]
    for pattern in quality_patterns:
        title = re.sub(pattern, '', title)

    # Replace separators with spaces
    title = re.sub(r'[\._]', ' ', title)
    # Remove extra whitespace
    title = re.sub(r'\s+', ' ', title)
    # Remove trailing/leading separators and whitespace
    title = title.strip(' -')
    return title

def search_tv_show(headers, title):
    """Search for a TV show and return matches."""
    url = f"{TMDB_API_BASE}/search/tv"
    params = {"query": title}
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    return response.json().get("results", [])

def search_movie(headers, title, year=None):
    """Search for a movie and return matches."""
    url = f"{TMDB_API_BASE}/search/movie"
    params = {"query": title}
    if year:
        params["year"] = year
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    return response.json().get("results", [])

def search_multi(headers, title):
    """Search across all types."""
    url = f"{TMDB_API_BASE}/search/multi"
    params = {"query": title}
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    return response.json().get("results", [])

def find_tmdb_id(filepath):
    """Find the TMDB ID for a given file."""
    headers = get_auth_header()
    parsed = parse_filename(filepath)

    print(f"Parsed: {parsed}", file=sys.stderr)
    tmdb_id = None
    if parsed["type"] == "tv":
        results = search_tv_show(headers, parsed["title"])
        if results:
            best = results[0]
            if best["season"] and best["episode"]:
                fields = ['id', 'season', 'episode']
                tmdb_id = ':'.join([str(best[x]) for x in fields])
            else:
                tmdb_id = best["id"]
            return tmdb_id

    elif parsed["type"] == "movie":
        results = search_movie(headers, parsed["title"], parsed.get("year"))
        if results:
            best = results[0]
            return best['id']
    else:
        # Unknown type, try multi-search
        results = search_multi(headers, parsed["title"])
        if results:
            best = results[0]
            best = results[0]
            if best["season"] and best["episode"]:
                fields = ['id', 'season', 'episode']
                tmdb_id = ':'.join([str(best[x]) for x in fields])
            else:
                tmdb_id = best["id"]
            return tmdb_id
    return None

def update_database():
    """Update all rows in intro_timestamps.db with TMDB IDs."""
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all rows that don't have a tmdb_id yet
    cursor.execute("SELECT id, file_name FROM intro_timestamps WHERE tmdb_id IS NULL")
    rows = cursor.fetchall()

    if not rows:
        print("No rows without tmdb_id found.")
        return

    print(f"Processing {len(rows)} rows...")
    updated = 0
    failed = 0

    for row_id, file_name in rows:
        print(f"\nLooking up: {file_name}")
        try:
            result = find_tmdb_id(file_name)
            if result:
                cursor.execute(
                    "UPDATE intro_timestamps SET tmdb_id = ? WHERE id = ?",
                    (result, row_id)
                )
                conn.commit()
                print(f"  -> Found TMDB id: {result})")
                updated += 1
            else:
                print("  -> No match found")
                failed += 1
        except Exception as e:
            print(f"  -> Error: {e}", file=sys.stderr)
            failed += 1

    conn.close()
    print(f"\nDone. Updated: {updated}, Failed: {failed}")

def main():
    parser = argparse.ArgumentParser(description="Look up TMDB IDs for media files")
    parser.add_argument("filename", nargs="?", help="Path to the media file")
    parser.add_argument("--update-db", action="store_true",
                        help="Update all rows in intro_timestamps.db with TMDB IDs")
    args = parser.parse_args()

    if args.update_db:
        update_database()
        return

    if not args.filename:
        parser.print_help()
        sys.exit(1)

    result = find_tmdb_id(args.filename)

    if result:
        print(f"TMDB ID: {result}")
        sys.exit(1)

if __name__ == "__main__":
    main()
