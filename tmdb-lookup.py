#!/usr/bin/env python3
import os
import re
import sys
import requests
from urllib.parse import quote

TMDB_API_BASE = "https://api.themoviedb.org/3"

def get_api_key():
    api_key = os.environ.get("TMDB_API_KEY")
    if not api_key:
        print("Error: TMDB_API_KEY environment variable not set", file=sys.stderr)
        print("Get your API key at https://www.themoviedb.org/settings/api", file=sys.stderr)
        sys.exit(1)
    return api_key

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

def search_tv_show(api_key, title):
    """Search for a TV show and return matches."""
    url = f"{TMDB_API_BASE}/search/tv"
    params = {"api_key": api_key, "query": title}
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json().get("results", [])

def search_movie(api_key, title, year=None):
    """Search for a movie and return matches."""
    url = f"{TMDB_API_BASE}/search/movie"
    params = {"api_key": api_key, "query": title}
    if year:
        params["year"] = year
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json().get("results", [])

def search_multi(api_key, title):
    """Search across all types."""
    url = f"{TMDB_API_BASE}/search/multi"
    params = {"api_key": api_key, "query": title}
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json().get("results", [])

def find_tmdb_id(filepath):
    """Find the TMDB ID for a given file."""
    api_key = get_api_key()
    parsed = parse_filename(filepath)

    print(f"Parsed: {parsed}", file=sys.stderr)

    if parsed["type"] == "tv":
        results = search_tv_show(api_key, parsed["title"])
        if results:
            best = results[0]
            return {
                "type": "tv",
                "id": best["id"],
                "name": best.get("name", best.get("original_name")),
                "first_air_date": best.get("first_air_date"),
                "season": parsed["season"],
                "episode": parsed["episode"],
                "confidence": "high" if len(results) == 1 else "medium"
            }

    elif parsed["type"] == "movie":
        results = search_movie(api_key, parsed["title"], parsed.get("year"))
        if results:
            best = results[0]
            return {
                "type": "movie",
                "id": best["id"],
                "title": best.get("title", best.get("original_title")),
                "release_date": best.get("release_date"),
                "confidence": "high" if len(results) == 1 else "medium"
            }

    else:
        # Unknown type, try multi-search
        results = search_multi(api_key, parsed["title"])
        if results:
            best = results[0]
            media_type = best.get("media_type")
            if media_type == "tv":
                return {
                    "type": "tv",
                    "id": best["id"],
                    "name": best.get("name", best.get("original_name")),
                    "first_air_date": best.get("first_air_date"),
                    "confidence": "low"
                }
            elif media_type == "movie":
                return {
                    "type": "movie",
                    "id": best["id"],
                    "title": best.get("title", best.get("original_title")),
                    "release_date": best.get("release_date"),
                    "confidence": "low"
                }

    return None

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <filename>", file=sys.stderr)
        print(f"Example: {sys.argv[0]} '/path/to/Star Trek - Voyager S03E01.mp4'", file=sys.stderr)
        sys.exit(1)

    filepath = sys.argv[1]
    result = find_tmdb_id(filepath)

    if result:
        print(f"TMDB ID: {result['id']}")
        print(f"Type: {result['type']}")
        if result['type'] == 'tv':
            print(f"Name: {result.get('name')}")
            print(f"First Air Date: {result.get('first_air_date')}")
            if 'season' in result:
                print(f"Season: {result['season']}")
                print(f"Episode: {result['episode']}")
        else:
            print(f"Title: {result.get('title')}")
            print(f"Release Date: {result.get('release_date')}")
        print(f"Confidence: {result['confidence']}")
    else:
        print("No match found", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()