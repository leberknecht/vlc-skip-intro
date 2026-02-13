.PHONY: create-intro-snippet scan-dir

create-intro-snippet:
	@if [ -z "$(FILENAME)" ] || [ -z "$(START)" ] || [ -z "$(END)" ] || [ -z "$(OUTPUT)" ]; then \
		echo "Usage: make create-intro-snippet FILENAME=<path> START=<offset> END=<offset> OUTPUT=<output.wav>"; \
		echo "Example: make create-intro-snippet FILENAME='/media/nfs-series/star trek voyager/staffel 3/Star Trek - Raumschiff Voyager S03E01.mp4' START=00:03:59 END=00:05:38 OUTPUT=intro-sequences/voyager-season-3.wav"; \
		exit 1; \
	fi
	ffmpeg -i "$(FILENAME)" -ss $(START) -to $(END) -q:a 0 -map 0:1 "$(OUTPUT)"

scan-dir:
	@if [ -z "$(PATHNAME)" ] || [ -z "$(INTRO_SEQUENCE)" ]; then \
		echo "Usage: make scan-dir PATHNAME=<dir> INTRO_SEQUENCE=<intro.wav>"; \
		echo "Example: make scan-dir PATHNAME=/media/local-storage/momentum/voyager-staffel-2/voyager-staffel2 INTRO_SEQUENCE=intro-sequences/voyager-season-2.wav"; \
		exit 1; \
	fi
	bash scan-dir.sh "$(PATHNAME)" "$(INTRO_SEQUENCE)"

update-plugin:
	cp vlc-plugin/skip_intro_intf.lua ~/.local/share/vlc/lua/intf/skip_intro.lua

update-db:
	cd vlc-plugin && bash update_cache.sh
	cp vlc-plugin/intro_timestamps_cache.json ~/.local/share/vlc/lua/intf/
