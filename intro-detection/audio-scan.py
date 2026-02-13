#!/usr/bin/env python3
"""
Fast audio-based intro detection using chromagram + correlation.

Uses pitch-based features (chromagram) which are more robust to
compression and encoding differences than MFCCs.`
"""

import numpy as np
import subprocess
import librosa
from pathlib import Path
import sys
import sqlite3
import os
import struct
from scipy.signal import correlate

# Configuration
SAMPLE_RATE = 22050  # Hz - good balance of quality and speed
SLIDE_INTERVAL = 3  # seconds - how much to slide the window forward each iteration
HOP_LENGTH = 1024  # samples between frames
CORRELATION_THRESHOLD = 0.8  # Correlation coefficient threshold (0-1)

# Two-stage refinement thresholds
REFINEMENT_TRIGGER = 0.42  # Trigger fine-grained search when correlation > this
REFINEMENT_THRESHOLD = 0.8  # Stop when fine-grained search finds correlation > this
REFINEMENT_WINDOW = 15  # seconds before/after to search in fine-grained mode
REFINEMENT_INTERVAL = 0.5  # seconds to slide in fine-grained mode

db_path="intro_timestamps.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("""
        CREATE TABLE IF NOT EXISTS intro_timestamps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            movie_hash TEXT,
            file_size INTEGER,
            start_time REAL NOT NULL,
            end_time REAL NOT NULL,
            correlation_score REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)




def format_timestamp(seconds):
    """Format seconds as mm:ss."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def calculate_opensubtitles_hash(video_path):
    """
    Calculate OpenSubtitles hash for a video file.

    OpenSubtitles uses a special hash algorithm:
    - Take file size in bytes
    - Sum 64-bit integers from first 64KB of file
    - Sum 64-bit integers from last 64KB of file
    - Add file size to the sum
    - Return as 16-character hex string

    Args:
        video_path: Path to video file

    Returns:
        Tuple of (hash string, file size in bytes)
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Path is not a file: {video_path}")

    longlongformat = '<q'  # little-endian long long (64-bit)
    bytesize = struct.calcsize(longlongformat)
    file_size = os.path.getsize(video_path)

    file_hash = file_size

    with open(video_path, "rb") as f:
        # Read first 64KB
        for _ in range(65536 // bytesize):
            buffer = f.read(bytesize)
            if len(buffer) < bytesize:
                break
            (l_value,) = struct.unpack(longlongformat, buffer)
            file_hash += l_value
            file_hash &= 0xFFFFFFFFFFFFFFFF  # Keep it 64-bit

        # Read last 64KB
        f.seek(max(0, file_size - 65536), 0)
        for _ in range(65536 // bytesize):
            buffer = f.read(bytesize)
            if len(buffer) < bytesize:
                break
            (l_value,) = struct.unpack(longlongformat, buffer)
            file_hash += l_value
            file_hash &= 0xFFFFFFFFFFFFFFFF  # Keep it 64-bit

    hash_string = "%016x" % file_hash
    return hash_string, file_size


def save_intro_timestamps(video_path, start_time, end_time, correlation_score, movie_hash, file_size, outro_length=0):
    try:

        print(f"  Movie hash: {movie_hash} (size: {file_size} bytes)")
    except Exception as e:
        print(f"  Warning: Could not calculate movie hash: {e}")
        movie_hash = None
        file_size = None

    file_name = str(os.path.basename(video_path))

    # Insert or replace the record for this video
    cursor.execute("""
        INSERT INTO intro_timestamps (file_name, movie_hash, file_size, start_time, end_time, correlation_score, outro_length)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (file_name, movie_hash, file_size, start_time, end_time, correlation_score, outro_length))

    conn.commit()
    conn.close()

    print(f"\n✓ Saved to database: {db_path}")
    print(f"  Video: {video_path}")
    print(f"  Intro: {format_timestamp(start_time)} - {format_timestamp(end_time)}")
    if outro_length > 0:
        print(f"  Outro: last {format_timestamp(outro_length)}")


def extract_audio_features(audio_data, sr=SAMPLE_RATE):
    """
    Extract audio fingerprint using chromagram (pitch-based features).

    Chromagram is more robust to compression and encoding variations than MFCCs,
    and preserves musical/tonal content better.
    """
    # Compute chromagram (12 pitch classes)
    chroma = librosa.feature.chroma_cqt(
        y=audio_data,
        sr=sr,
        hop_length=HOP_LENGTH
    )

    # Normalize each frame
    chroma = librosa.util.normalize(chroma, axis=0)

    return chroma


def compute_correlation(intro_features, chunk_features):
    """
    Compute normalized cross-correlation between intro and chunk.

    Returns:
        Array of correlation scores for each possible alignment position.
    """
    # Flatten features to 1D for correlation
    intro_flat = intro_features.flatten()
    chunk_flat = chunk_features.flatten()

    # Normalize
    intro_norm = (intro_flat - np.mean(intro_flat)) / (np.std(intro_flat) + 1e-8)
    chunk_norm = (chunk_flat - np.mean(chunk_flat)) / (np.std(chunk_flat) + 1e-8)

    # Cross-correlation
    correlation = correlate(chunk_norm, intro_norm, mode='valid')

    # Normalize by length
    correlation = correlation / len(intro_norm)

    return correlation


def load_audio_from_file(file_path, sr=SAMPLE_RATE):
    """Load complete audio from a file (for the intro snippet)."""
    print(f"Loading intro audio: {file_path}")

    if not Path(file_path).exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    # Use librosa to load audio
    audio, _ = librosa.load(file_path, sr=sr, mono=True)

    duration_sec = len(audio) / sr
    print(f"Loaded {format_timestamp(duration_sec)} of audio")
    return audio


def stream_audio_from_video(video_path, chunk_duration, sr=SAMPLE_RATE):
    print(f"Streaming audio from video: {video_path}")

    if not Path(video_path).exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # Get video duration first
    duration_cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]

    try:
        duration_output = subprocess.check_output(duration_cmd, stderr=subprocess.STDOUT, text=True)
        total_duration = float(duration_output.strip())
        print(f"Video duration: {format_timestamp(total_duration)}")
    except Exception as e:
        print(f"Warning: Could not get video duration: {e}")
        total_duration = None

    # Stream audio in chunks
    chunk_start = 0
    chunk_num = 0

    while True:
        # Stop if we know we're past the end
        if total_duration and chunk_start >= total_duration:
            break

        # Extract audio chunk using ffmpeg
        cmd = [
            'ffmpeg',
            '-ss', str(chunk_start),  # Start time
            '-t', str(chunk_duration),  # Duration
            '-i', video_path,
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # Raw PCM
            '-ar', str(sr),  # Sample rate
            '-ac', '1',  # Mono
            '-f', 's16le',  # Output format
            '-'  # Output to stdout
        ]

        try:
            # Run ffmpeg
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            audio_data, stderr = process.communicate()

            if process.returncode != 0:
                if chunk_num == 0:
                    # First chunk failed - real error
                    raise RuntimeError(f"ffmpeg failed: {stderr.decode()}")
                else:
                    # Later chunk failed - probably reached end of file
                    break

            if len(audio_data) == 0:
                # No more data
                break

            # Convert bytes to numpy array
            audio_chunk = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
            audio_chunk /= 32768.0  # Normalize to [-1, 1]

            if len(audio_chunk) == 0:
                break

            chunk_num += 1
            window_end = chunk_start + chunk_duration
            actual_duration = len(audio_chunk) / sr
            print(f"  Window {chunk_num}: {format_timestamp(chunk_start)} - {format_timestamp(window_end)} "
                  f"({format_timestamp(actual_duration)} actual)")

            yield audio_chunk, chunk_start

            chunk_start += SLIDE_INTERVAL  # Slide window forward by 5 seconds

        except Exception as e:
            print(f"Error extracting audio chunk: {e}")
            break


def extract_audio_snippet(video_path, start_time, duration, sr=SAMPLE_RATE):
    # Ensure start_time is not negative
    start_time = max(0, start_time)

    cmd = [
        'ffmpeg',
        '-ss', str(start_time),
        '-t', str(duration),
        '-i', video_path,
        '-vn',
        '-acodec', 'pcm_s16le',
        '-ar', str(sr),
        '-ac', '1',
        '-f', 's16le',
        '-'
    ]

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        audio_data, stderr = process.communicate()

        if process.returncode != 0 or len(audio_data) == 0:
            return None

        audio_chunk = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
        audio_chunk /= 32768.0

        return audio_chunk
    except Exception:
        return None


def refine_match_location(video_path, intro_features, coarse_match_time, intro_duration):
    """
    Perform fine-grained search around a coarse match location.

    Args:
        video_path: Path to video file
        intro_features: Pre-computed intro features
        coarse_match_time: Timestamp from coarse search
        intro_duration: Duration of intro in seconds

    Returns:
        (best_time, best_score) tuple
    """
    # Extract a snippet around the coarse match
    snippet_start = coarse_match_time - REFINEMENT_WINDOW
    snippet_duration = 2 * REFINEMENT_WINDOW + intro_duration + REFINEMENT_INTERVAL

    print(f"\n  → Refining search around {format_timestamp(coarse_match_time)}...")
    print(f"     Extracting snippet: {format_timestamp(max(0, snippet_start))} - {format_timestamp(snippet_start + snippet_duration)}")

    snippet_audio = extract_audio_snippet(video_path, snippet_start, snippet_duration)

    if snippet_audio is None:
        print(f"     Failed to extract snippet for refinement")
        return coarse_match_time, 0.0

    # Slide through snippet with fine-grained intervals
    best_time = coarse_match_time
    best_score = 0.0

    actual_snippet_start = max(0, snippet_start)
    window_start = 0
    snippet_duration_actual = len(snippet_audio) / SAMPLE_RATE

    while window_start < snippet_duration_actual - intro_duration:
        # Extract window from snippet
        window_start_sample = int(window_start * SAMPLE_RATE)
        window_end_sample = int((window_start + intro_duration) * SAMPLE_RATE)

        if window_end_sample > len(snippet_audio):
            break

        window_audio = snippet_audio[window_start_sample:window_end_sample]
        window_features = extract_audio_features(window_audio)

        # Check if window is long enough
        if window_features.shape[1] >= intro_features.shape[1]:
            correlation_scores = compute_correlation(intro_features, window_features)

            if len(correlation_scores) > 0:
                max_corr_idx = np.argmax(correlation_scores)
                max_corr_score = correlation_scores[max_corr_idx]

                # Convert to absolute timestamp
                offset_frames = max_corr_idx // intro_features.shape[0]
                offset_time = offset_frames * HOP_LENGTH / SAMPLE_RATE
                absolute_time = actual_snippet_start + window_start + offset_time

                if max_corr_score > best_score:
                    best_score = max_corr_score
                    best_time = absolute_time
                    print(f"     Fine-grained match: {format_timestamp(best_time)} (correlation: {max_corr_score:.4f})")

                # Found strong match - stop refining!
                if max_corr_score >= REFINEMENT_THRESHOLD:
                    print(f"     ✓ Strong match found!")
                    break

        window_start += REFINEMENT_INTERVAL

    return best_time, best_score


def find_intro_in_video(video_path, intro_audio_path, movie_hash, file_size, correlation_threshold=CORRELATION_THRESHOLD, outro_length=0):
    # Load intro audio and extract features
    intro_audio = load_audio_from_file(intro_audio_path)
    intro_features = extract_audio_features(intro_audio)
    intro_duration = len(intro_audio) / SAMPLE_RATE

    print(f"\nIntro features shape: {intro_features.shape}")
    print(f"Intro duration: {format_timestamp(intro_duration)}")
    print(f"Correlation threshold: {correlation_threshold}")
    print(f"\nScanning video...")

    best_match_time = None
    best_match_score = 0.0

    # Stream through video chunks using intro duration as window size
    for chunk_audio, chunk_start_time in stream_audio_from_video(video_path, intro_duration):
        chunk_duration_actual = len(chunk_audio) / SAMPLE_RATE

        # Extract features from chunk
        chunk_features = extract_audio_features(chunk_audio)

        # Check if chunk is long enough
        intro_frames = intro_features.shape[1]
        chunk_frames = chunk_features.shape[1]

        if chunk_frames < intro_frames:
            # Chunk too short to contain intro
            continue

        # Compute correlation across entire chunk
        correlation_scores = compute_correlation(intro_features, chunk_features)

        # Find peak correlation
        if len(correlation_scores) > 0:
            max_corr_idx = np.argmax(correlation_scores)
            max_corr_score = correlation_scores[max_corr_idx]

            # Convert correlation index to timestamp
            # Each correlation point corresponds to a feature frame
            feature_size = intro_features.shape[0] * intro_features.shape[1]
            offset_frames = max_corr_idx // intro_features.shape[0]
            offset_time = offset_frames * HOP_LENGTH / SAMPLE_RATE
            match_time = chunk_start_time + offset_time

            # Update best match
            if max_corr_score > best_match_score:
                best_match_score = max_corr_score
                best_match_time = match_time

                print(f"    New best match at {format_timestamp(best_match_time)} (correlation: {max_corr_score:.4f})")

                # Trigger fine-grained refinement if score is promising
                if max_corr_score >= REFINEMENT_TRIGGER:
                    refined_time, refined_score = refine_match_location(
                        video_path, intro_features, best_match_time, intro_duration
                    )

                    if refined_score > best_match_score:
                        best_match_score = refined_score
                        best_match_time = refined_time

                    # Found strong match after refinement - stop searching!
                    if refined_score >= REFINEMENT_THRESHOLD:
                        print(f"\n✓ MATCH FOUND (after refinement)!")
                        print(f"  Timestamp: {format_timestamp(best_match_time)}")
                        print(f"  Correlation: {best_match_score:.4f}")

                        # Save to database
                        end_time = best_match_time + intro_duration
                        save_intro_timestamps(video_path, best_match_time, end_time, best_match_score,
                                              movie_hash, file_size, outro_length)

                        return best_match_time, best_match_score

            # Found a match above threshold in coarse search - stop searching!
            if max_corr_score >= correlation_threshold:
                print(f"\n✓ MATCH FOUND!")
                print(f"  Timestamp: {format_timestamp(best_match_time)}")
                print(f"  Correlation: {max_corr_score:.4f}")

                # Save to database
                end_time = best_match_time + intro_duration
                save_intro_timestamps(video_path, best_match_time, end_time, max_corr_score, movie_hash, file_size, outro_length)

                return best_match_time, max_corr_score

    # Finished scanning without finding match above threshold
    if best_match_time is not None:
        print(f"\n✗ No match above threshold")
        print(f"  Best match: {format_timestamp(best_match_time)} (correlation: {best_match_score:.4f})")
        print(f"  Try lowering --correlation-threshold below {best_match_score:.4f}")
    else:
        print(f"\n✗ No match found")

    return best_match_time, best_match_score


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Find where an audio snippet occurs in a video file using chromagram correlation"
    )
    parser.add_argument("video", help="Path to video file")
    parser.add_argument("audio_snippet", help="Path to audio snippet (intro)")
    parser.add_argument(
        "--correlation-threshold",
        type=float,
        default=CORRELATION_THRESHOLD,
        help=f"Correlation threshold 0-1 (default: {CORRELATION_THRESHOLD})"
    )
    parser.add_argument(
        "--outro-length",
        type=float,
        default=0,
        help="Length of outro in seconds (default: 0, disabled)"
    )

    args = parser.parse_args()


    file_name = os.path.basename(args.video)
    movie_hash, file_size = calculate_opensubtitles_hash(args.video)

    print(f'checking name: {file_name}, hash: {movie_hash}')
    cursor.execute("SELECT COUNT(*) FROM intro_timestamps WHERE file_name = ? or movie_hash = ?", (file_name, movie_hash))
    count = int(cursor.fetchone()[0])
    if count != 0:
        print(f'file already known, skipping')
        exit(0)

    # Run detection
    timestamp, score = find_intro_in_video(
        args.video,
        args.audio_snippet,
        movie_hash,
        file_size,
        correlation_threshold=args.correlation_threshold,
        outro_length=args.outro_length
    )

    if timestamp is not None and score >= args.correlation_threshold:
        print(f"\n{'='*60}")
        print(f"SUCCESS: Intro found at {format_timestamp(timestamp)}")
        print(f"Correlation score: {score:.4f}")
        print(f"{'='*60}")
        sys.exit(0)
    else:
        print(f"\n{'='*60}")
        print(f"FAILED: Intro not found with correlation >= {args.correlation_threshold}")
        if timestamp:
            print(f"Best match: {format_timestamp(timestamp)} (correlation: {score:.4f})")
        print(f"{'='*60}")
        sys.exit(1)
