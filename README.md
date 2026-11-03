# galaxy-integration-gw2

Guild Wars 2 integration for GOG Galaxy 2.1+ (64-bit, Windows)

Features:
* Import of the owned game and expansions (Heart of Thorns, Path of Fire, ...)
* Detection of installed and running game, launch, install and uninstall
* Import of game time and achievements

## Requirements

* GOG Galaxy 2.1 or newer (64-bit). The older 32-bit GOG Galaxy 2.0 client is not supported anymore, use version 0.5.2 for it.
* A Guild Wars 2 API key with the `account` and `progression` permissions, created at https://account.arena.net/applications.

## Installation

1. Close GOG Galaxy.
2. Unpack the latest archive from https://github.com/Gorasa/galaxy-integration-gw2/releases to `%localappdata%\GOG.com\Galaxy\plugins\installed\gw2\` (replace an existing older version completely).
3. Start GOG Galaxy and connect the Guild Wars 2 integration with your API key.

## Building from source

GOG Galaxy 2.1+ runs plugins with a bundled 64-bit Python 3.13, so the third-party dependencies must be downloaded for that runtime. This requires a local Python 3.13 installation (`py -3.13` on Windows, `python3.13` elsewhere).

1. Run `download_deps.cmd` (Windows) or `download_deps.sh` (Linux/macOS). This fills `3rdparty_windows/` with the packages from `requirements.txt`.
2. Copy the repository content (without `.git`) to `%localappdata%\GOG.com\Galaxy\plugins\installed\gw2\`.

## Creating a release

The `Release` GitHub workflow builds the plugin archive (including the `3rdparty_windows` dependencies) and publishes it as a GitHub release:

1. Increase `version` in `manifest.json` and add a `### <version>` section to the changelog below, merge to `main`.
2. On GitHub open Actions -> "Release" -> "Run workflow". This creates the tag `v<version>` and the release with the archive and the changelog section as description.

Alternatively push a tag `v<version>` matching `manifest.json`.

## Achievement names

`gw2/db/achievements.json` contains the names of all achievements known when it was generated. Names of newer achievements are requested from the API at runtime. To update the file run `python tools/update_achievements_db.py`. The `Update achievements DB` GitHub workflow does this monthly (or manually via "Run workflow") and opens a pull request if the file changed.

## Logs

Plugin logs are written to `%programdata%\GOG.com\Galaxy\logs\` (file name starting with `plugin-gw2-`).

## Changelog

### 0.6.0

* Support for GOG Galaxy 2.1+ (64-bit, Python 3.13): updated `galaxy.plugin.api` to 0.71 and `aiohttp` to 3.14
* Removed Sentry crash reporting, no data is sent to third-party servers anymore
* Removed macOS support
* TLS certificates of the Guild Wars 2 API are verified again
* Fixed newly unlocked achievements not being pushed to GOG Galaxy
* Fixed achievements added to the game after 2020 not being imported: names missing in the offline DB are requested from the API
* Fixed achievements not showing up in GOG Galaxy (0%) for accounts with many achievements: GOG Galaxy fails to upload large lists to its backend and uploads only after its own achievements import (e.g. at its start). So the plugin adds 200 achievements per import, after the first connection it takes several GOG Galaxy restarts until all achievements are shown. Newly unlocked achievements are reported right away.
* Fixed every API request being sent 5 times, errors are retried with a delay now
* Fixed wrong pages shown after login

Older versions: https://github.com/Mixaill/galaxy-integration-gw2/releases

## Additional info

* Original plugin by Mikhail Paulyshka: https://github.com/Mixaill/galaxy-integration-gw2
* GOG Galaxy Integrations API: https://github.com/gogcom/galaxy-integrations-python-api
* Guild Wars 2 API: https://wiki.guildwars2.com/wiki/API:Main
