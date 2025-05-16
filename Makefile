include .env

PATH_ANKI_ADDON_DEV = $(PATH_ANKI)/addons21/rember-anki-sync-dev

.PHONY: dev zip

dev:
	@echo "Copying source files to $(PATH_ANKI_ADDON_DEV)"
	@mkdir -p "$(PATH_ANKI_ADDON_DEV)"
	@cp -R src/. "$(PATH_ANKI_ADDON_DEV)/"
	@echo "Done."

zip:
	@echo "Creating zip archive: rember-anki-sync.zip"
	@(cd src && zip -r "../rember-anki-sync.zip" .)
	@echo "Done"
