# VLC Skip Intro

The goal of this vibe-coded ball-of-mud is to enable VLC to skip intro sequences. For that we need a database with start- and end-offset of the intro. Unfortunately there doesnt seem to be usable source of that information available, so we/you have to build that on your own :/ (There is https://introdb.app/ though, but atm it only has ~4k entries in it... i guess i will add a script to fire your local records to their API at some point). For creating, i use a audio-sample of the intro-sequence. Which means you have to provide this :/ We then scan through a video file to find a good match of the intro audio sequence to identify the offsets. You can also add information how long the outro is, so the VLC plugin can skip-to-next.

## Create new entry on your local intro-DB
The crap-code uses a simple sqlite DB for storing the timestamps, unfortunately LUA has no build-in support for sqlite, so we need to dump that to CSV for the VLC-Plugin. 
The whole flow

1. extract an audio intro sequence. Watch the video, find the timestamps, then do something like
```shell
make create-intro-snippet FILENAME=<path to one episode> START=02:23 END=04:42 OUTPUT=intro-sequences/my-series-season1.wav
```
2. Now that we have the WAV, lets fire it against the whole series:
```shell
make scan-dir PATHNAME=/media/nfs-series/voyager-season-1/ INTRO_SEQUENCE=intro-sequences/my-series-season1.wav
```
This will iterate over the files and try to find the audio sequence in it. 
3. Dump to csv and install the plugin
```shell
make update-plugin
make update-db
```

I'm not quite sure if there is more what you need to do, as claude also created a `bash vlc-plugin/enable_permanent.sh` script, which apparently adds these to lines to `~/.config/vlc/vlcrc`
```
extraintf=luaintf
lua-intf=skip_intro
```

..but hey, whatever, worksonmymachine :shrug:
