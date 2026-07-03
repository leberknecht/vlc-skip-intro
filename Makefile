.PHONY: create-intro-snippet scan-dir update-plugin update-tmdb-ids update-db help

.DEFAULT_GOAL := help

GREEN  := $(shell tput -Txterm setaf 2)
YELLOW := $(shell tput -Txterm setaf 3)
RESET  := $(shell tput -Txterm sgr0)

help:
	@echo 'Usage:'
	@echo '  ${YELLOW}make${RESET} ${GREEN}<target>${RESET}'
	@echo 'Targets:'
	@awk '/^[a-zA-Z\-_0-9%]+:/ { \
		helpMessage = match(lastLine, /^## (.*)/); \
		if (helpMessage) { \
			helpCommand = substr($$1, 0, index($$1, ":")); \
			helpMessage = substr(lastLine, RSTART + 3, RLENGTH); \
			printf "  ${YELLOW}%-25s${RESET} ${GREEN}%s${RESET}\n", helpCommand, helpMessage; \
		} \
	} \
	{ lastLine = $$0 }' $(MAKEFILE_LIST)

## Extract intro audio snippet from a video file
create-intro-snippet:
	@if [ -z "$(FILENAME)" ] || [ -z "$(START)" ] || [ -z "$(END)" ] || [ -z "$(OUTPUT)" ]; then \
		echo "Usage: make create-intro-snippet FILENAME=<path> START=<offset> END=<offset> OUTPUT=<output.wav>"; \
		echo "Example: make create-intro-snippet FILENAME='/media/nfs-series/star trek voyager/staffel 3/Star Trek - Raumschiff Voyager S03E01.mp4' START=00:03:59 END=00:05:38 OUTPUT=intro-sequences/voyager-season-3.wav"; \
		exit 1; \
	fi
	ffmpeg -i "$(FILENAME)" -ss $(START) -to $(END) -q:a 0 -map 0:1 "$(OUTPUT)"

## Scan a directory for intro timestamps (FORCE=1 to re-process known files, OUTRO_LENGTH=<seconds>)
scan-dir:
	@if [ -z "$(PATHNAME)" ] || [ -z "$(INTRO_SEQUENCE)" ]; then \
		echo "Usage: make scan-dir PATHNAME=<dir> INTRO_SEQUENCE=<intro.wav> [FORCE=1] [OUTRO_LENGTH=<seconds>]"; \
		echo "Example: make scan-dir PATHNAME=/media/local-storage/momentum/voyager-staffel-2/voyager-staffel2 INTRO_SEQUENCE=intro-sequences/voyager-season-2.wav"; \
		exit 1; \
	fi
	bash scan-dir.sh "$(PATHNAME)" "$(INTRO_SEQUENCE)" $(if $(FORCE),--force,) $(if $(OUTRO_LENGTH),--outro-length $(OUTRO_LENGTH),)

## Install VLC plugin to local VLC directory
update-plugin:
	cp vlc-plugin/skip_intro_intf.lua ~/.local/share/vlc/lua/intf/skip_intro.lua

## Update TMDB IDs for entries missing them in the database
update-tmdb-ids:
	cd intro-detection && python tmdb_lookup.py --update-db

## Rebuild and install the VLC plugin JSON cache
update-db:
	cd vlc-plugin && bash update_cache.sh
	cp vlc-plugin/intro_timestamps_cache.json ~/.local/share/vlc/lua/intf/