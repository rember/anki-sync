# Anki Add-on to sync flashcards from Rember

## Setup

- Clone the repo.

- Copy `.env.example` to `.env` and fill the variables.

- Install [Nix](https://nixos.org/).

- Run `nix develop -c $SHELL` to start a development shell. This happens automatically if you use [direnv](https://direnv.net/).

## Tasks

Run `make dev` to createa `rember-anki-sync-dev` add-on in Anki, which you can use to test the add-on after making changes.

Run `make zip` to create a `rember-anki-sync.zip` file which can be uploaded to [AnkiWeb](https://ankiweb.net/shared/addons).

Run `make update-app-anki` to update the `src/app_anki` folder, it assumes that the private `rember` repo lives next to the project folder.

## Notes

We use Python 3.9 because that's the version currently used in the Anki repo.

We install packages with `uv` only for type checking, the code is currently only executed by Anki.

Users sign up with their Rember account following the best practices described in [RFC 8252 - OAuth 2.0 for Native Apps](https://datatracker.ietf.org/doc/html/rfc8252): we use the authorization code grant with PKCE in an external browser and use the loopback interface to receive the OAuth redirect. Once we obtain auth tokens, we store them in the user profile. Anki stores AnkiWeb and AnkiHub auth tokens in the user profile as plain text, see for example [`sync_login`](https://github.com/ankitects/anki/blob/d3d6bd8ce006f178e2271fd8d317fdc8832095df/qt/aqt/sync.py#L320-L321).

The `src/app_anki` folder contains the bundle for the `@rember/app-anki` package in the private `rember` repository. It's included in this repository using Git LFS and is used in the Rember note templates.

## References

- [Anki GitHub](https://github.com/ankitects/anki/tree/main)
- [Anki Add-ons docs](https://addon-docs.ankiweb.net/intro.html)
- [RFC 8252 - OAuth 2.0 for Native Apps](https://datatracker.ietf.org/doc/html/rfc8252)
