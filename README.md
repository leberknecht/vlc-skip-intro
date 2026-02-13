# VLC Skip Intro

The goal of this vibe-coded ball-of-mud is to enable VLC to skip intro sequences. For that we need a database with start- and end-offset of the intro. Unfortunately there doesnt seem to be usable source of that information available, so we/you have to build that on your own :/ (There is https://introdb.app/ though, but atm it only has ~4k entries in it... i guess i will add a script to fire your local records to their API at some point). For creating, i use a audio-sample of the intro-sequence. Which means you have to provide this :/ We then scan through a video file to find a good match of the intro audio sequence to identify the offsets. You can also add information how long the outro is, so the VLC plugin can skip-to-next.

## Create new entry on your local intro-DB
The crap-code uses a simple sqlite DB for storing the timestamps, unfortunately LUA has no build-in support for sqlite, so we need to dump that to CSV for the VLC-Plugin. 
The whole flow

1. extract a audio intro sequence. Watch the video, find the timestamps, then do something like
```shell
ffmpeg -i ~/video/my-fav-series/s01e42.mkv -ss 00:07:45 -t 00:00:35 -q:a 0 -map 0:1 intro-sequences/my-fav-series-season-01.wav
```
2. Now that we have the WAV, lets fire it against the whole series:
```shell
bash scan-dir.sh ~/video/my-fav-series/ intro-sequences/my-fav-series-season-01.wav
```
This will iterate over the files and try to find the audio sequence in it. 
3. Dump to csv and install the plugin
```shell
python3 vlc-plugin/export_db_cache.py intro_timestamps.db

```
