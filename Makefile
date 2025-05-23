include .env

PATH_ANKI_ADDON_DEV = $(PATH_ANKI)/addons21/rember-anki-sync-dev

.PHONY: dev package update-app-anki

dev:
	@echo "Copying source files to $(PATH_ANKI_ADDON_DEV)"
	@mkdir -p "$(PATH_ANKI_ADDON_DEV)"
	@rsync -av --exclude='__pycache__' --exclude='*.pyc' --exclude='*.pyo' src/. "$(PATH_ANKI_ADDON_DEV)/"
	@echo "Done."

package:
	@echo "Creating zip archive: rember-anki-sync.zip"
	@(cd src && zip -r "../rember-anki-sync.zip" . -x "*/__pycache__/*" "*.pyc" "*.pyo")
	@echo "Done"

update-app-anki:
	@echo "Copying app-anki dist files to src/app-anki"
	@cp -R ../rember/packages/app-anki/dist/. src/app_anki/
	@echo "Done"
