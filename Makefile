include .env

PATH_ANKI_ADDON_DEV = $(PATH_ANKI)/addons21/rember-anki-sync-dev

.PHONY: dev package update-app-anki

dev:
	@echo "Copying source files to $(PATH_ANKI_ADDON_DEV)"
	@mkdir -p "$(PATH_ANKI_ADDON_DEV)"
	@rsync -av --exclude='__pycache__' --exclude='*.pyc' --exclude='*.pyo' --exclude='.DS_Store' src/. "$(PATH_ANKI_ADDON_DEV)/"
	@echo "Done."

package:
	@echo "Creating zip archive: rember-anki-sync.zip"
	@(cd src && zip -r "../rember-anki-sync.zip" . -x "*/__pycache__/*" "*.pyc" "*.pyo" ".DS_Store")
	@echo "Done"

update-app-anki:
	@echo "Copying app-anki dist files to src/app-anki"
	@mkdir -p src/app_anki
	@cp ../rember/packages/app-anki/dist/*.umd.cjs src/app_anki/
	@cp ../rember/packages/app-anki/dist/*.css src/app_anki/
	@echo "Done"
