include .env

PATH_ANKI_ADDON_DEV = $(PATH_ANKI)/addons21/rember-anki-sync-dev

FILES_SOURCE = src/__init__.py src/auth.py
FILENAME_ZIP = rember-anki-sync.zip

.PHONY: dev zip

dev:
	@echo "Copying source files to $(PATH_ANKI_ADDON_DEV)"
	@mkdir -p "$(PATH_ANKI_ADDON_DEV)"
	@cp $(FILES_SOURCE) "$(PATH_ANKI_ADDON_DEV)/"
	@echo "Done."

zip:
	@echo "Creating zip archive: rember-anki-sync.zip"
	@zip "rember-anki-sync.zip" $(FILES_SOURCE)
	@echo "Done"
