# Anki Add-on to sync flashcards from Rember

## Setup

Copy `.env.example` to `.env` and fill the variables.

Install [Nix](https://nixos.org/).

Run `nix develop -c $SHELL` to start a development shell. This happens automatically if you use [direnv](https://direnv.net/).

## Develop & Publish

Run `make dev` to createa `rember-anki-sync-dev` add-on in Anki, which you can use to test the add-on after making changes.

Run `make zip` to create a `rember-anki-sync.zip` file which can be uploaded to [AnkiWeb](https://ankiweb.net/shared/addons).

## Notes

We use Python 3.9 because that's the version currently used in the Anki repo.

## References

- [Anki GitHub](https://github.com/ankitects/anki/tree/main)
- [Anki Add-ons docs](https://addon-docs.ankiweb.net/intro.html)
