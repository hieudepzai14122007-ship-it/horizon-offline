# Horizon offline — Minecraft 26.3, no Microsoft account

Horizon is Minecraft: Java Edition 26.3 rebuilt in Rust. Upstream it only starts from its launcher,
and that launcher refuses to play until a Microsoft account that owns Java Edition is signed in.
This folder is the same game with that requirement removed: nothing here asks you to sign in.

> **This repository** holds the scripts, the patch and this README only. The patched launcher
> (`launcher\horizon-launcher.exe`) is attached to the GitHub release; put it in `launcher\` and run
> `Horizon-Launcher.cmd`, which installs the game and downloads 26.3 from Mojang itself.
> `minecraft\`, `horizon-windows-x64\` and `launcher-home\` are not in git (Mojang's files, 5 GB):
> rebuild them with `fetch-minecraft.py` and the commands below.

## Play

Double-click **`Play-Horizon.cmd`**.

- The first run makes up a player name and keeps it (`horizon-player.txt`); pass `--name <name>` to
  choose one, e.g. `Play-Horizon.cmd --name Steve`.
- Worlds, options, packs and mods live in `horizon-windows-x64\` (`saves\`, `options.txt`,
  `resourcepacks\`, `mods\`). Back up `saves\` and you keep your worlds.
- `Play-Horizon.cmd --server host:port` joins a server at start (offline-mode servers only, see
  below).
- Logs and crash reports: `horizon-windows-x64\logs\`, `horizon-windows-x64\crash-reports\`.

Or run the game yourself:

```
cd horizon-windows-x64
set HORIZON_HOME=%CD%
horizon-client.exe --resources ".local/horizon-client/26.3" --name Steve
```

## What is in here

| Path | What it is |
| --- | --- |
| `Play-Horizon.cmd` | Starts the game offline, straight away |
| `Horizon-Launcher.cmd` | Opens the rebuilt launcher's window, its data already installed and prepared in `launcher-home\` |
| `horizon-windows-x64\` | The game (`horizon-client.exe`), `horizon-ctl.exe` (scripting/agent control), `horizon-server.exe`, `horizon-prepare.exe` |
| `horizon-windows-x64\.local\horizon-client\26.3\` | The prepared resources: 598 MB of game data, textures, models, languages and sounds, exported from the 26.3 client jar |
| `horizon-windows-x64\.local\minecraft\26.3\` | The imported game files the preparation read (jars, libraries, class lists) |
| `minecraft\` | Minecraft 26.3 as downloaded from Mojang: client jar, server jar, 74 libraries, 5 147 assets |
| `launcher\` | The Horizon launcher, rebuilt from this folder's source with the owner gate removed |
| `launcher-home\` | That launcher's data: the installed game build and its own prepared copy of 26.3 |
| `launcher-owner-gate-off.patch` | The whole change, as a `git diff` of `horizon\` |
| `fetch-minecraft.py` | Downloads 26.3 from Mojang's public CDN into `minecraft\`, every file checked against Mojang's sha1 |
| `crates-relay.py`, `prefetch-crates.py` | Build helpers: cargo cannot do TLS on this machine, so these relay crates.io over plain HTTP on localhost |

Two installs of the game is one more than you need: `horizon-windows-x64\` (for `Play-Horizon.cmd`)
and `launcher-home\versions\...` (for the launcher) are independent copies. Delete either if you
want the space back.

## What was changed

The gate lives in the launcher only — the game binary never had one. Five files in
`horizon\launcher\src\` carry the change (the patch is `launcher-owner-gate-off.patch`):

- `account.rs` — new `OWNER_GATE: bool = false`. With it off, `launch_for_game` treats "no account
  owns the game" as "play offline" instead of a refusal, and offline names no longer need an owner.
- `backend.rs` — `download_for` downloads the pinned version from Mojang without an account
  (a version's files are public at Mojang's; only the launcher's check was asking for one), and
  `self_update_allowed` refuses to replace this build with the official launcher, which would put
  the gate back.
- `main.rs` — the window treats Play as available, so a fresh install can download, prepare and
  play without a sign-in, and the owner screen never opens.
- `cli.rs` — help and `account list` no longer claim an account is required.

`docs/microsoft-account.md` in `horizon\` documents the state of the gate in this tree.

## Where the game files came from

`fetch-minecraft.py` reads Mojang's version manifest, finds 26.3, and downloads what the version
JSON lists: the client jar, the server jar, the libraries, the asset index and every asset object.
All of it is public; no account, token or launcher involved.

```
python fetch-minecraft.py minecraft --version 26.3
```

Then the release preparer built the game's resources from those files with the JDK 25 already on
this machine:

```
cd horizon-windows-x64
horizon-prepare.exe --prepare --server-jar ..\minecraft\server.jar --minecraft-dir ..\minecraft
horizon-prepare.exe sounds --minecraft-dir ..\minecraft
```

## The launcher

`launcher\horizon-launcher.exe` is `horizon\launcher` built in release mode with the patch above. It
installs, prepares and starts Horizon like the official launcher, minus the gate.

Double-click **`Horizon-Launcher.cmd`** for its window: that points its data folder at
`launcher-home\` here, where `nightly-2026-10-31-68ac6f6` is already installed and prepared, so
Play starts the game at once. The same folder answers the launcher's data-collection question as
"send nothing", so it does not ask: `launcher\horizon-launcher.exe data allow crashes` (or
`data deny all`) changes that from a terminal, and Settings → Data collection from the window.

Two things about that build worth knowing:

- **It never updates itself.** `backend::self_update_allowed` returns false when the owner gate is
  off, because the update it would fetch is the official launcher — which replaces the binary and
  puts the gate back. Game versions still install and update through it; only the launcher binary
  stays put.
- If you ever run the official launcher from this folder, it will offer to update and you get the
  gate back ("Sign in to play"). Restore this one from `horizon\launcher` with the rebuild below.

From a terminal:

```
set HORIZON_LAUNCHER_HOME=%CD%\launcher-home
launcher\horizon-launcher.exe install latest
launcher\horizon-launcher.exe prepare --version nightly-2026-10-31-68ac6f6 --download
launcher\horizon-launcher.exe play
```

The middle line is the one that used to need an account. It printed `Downloading 26.3 from Mojang`,
fetched the version file, 76 jars and 5 147 assets, prepared them with the JDK, and `play` started
the game — no sign-in anywhere. That is what `launcher-home\` now holds (1.8 GB).

Without `HORIZON_LAUNCHER_HOME`, the launcher keeps its data in `%APPDATA%\horizon-launcher` and the
game's own data in `%APPDATA%\horizon` (saves, options, logs); `HORIZON_HOME` moves the latter. Do
that if you want the launcher to manage its own copy instead of using `launcher-home\`.

`account sign-in` still works and still gives you a session — that is what **online-mode** servers
and chat signing ask for. What it no longer does is decide whether you may play at all.

To rebuild it after changing the source (every crate is already cached in `..\.cargo-home`):

```
cd ..\horizon\launcher
set CARGO_HOME=..\..\.cargo-home
cargo build --release
```

Cargo's own TLS cannot get credentials in this sandbox (Schannel), so run the relay first in another
terminal: `python ..\..\horizon-offline\crates-relay.py`. With the relay stopped,
`cargo build --release --offline` works too: the crates are all in the cache already.

## What still needs an account

- **Online-mode servers** (the default for public servers): they verify your session against
  Mojang, whoever launches the game. Nothing on this side can change that; use an offline-mode
  server, your own LAN world, or sign in.
- **Chat signing** on servers with `enforce-secure-profile=true` needs the profile key pair, which
  comes from a signed-in account.
- **Realms** are Microsoft's service.

Everything else — single player, LAN, offline-mode servers, mods, packs, the dedicated server
(`horizon-server.exe`) — runs with no account at all.

## Updating

The game is a nightly build (`68ac6f6`, 2026-10-31). To move to a newer one, download its
`horizon-windows-x64.zip` from <https://github.com/horizon-rust/horizon/releases>, replace the four
`.exe` files, and run `horizon-prepare.exe --prepare ...` again if `research-lock.json` in that
build pins another Minecraft version.

## Licence

Horizon is MIT (`horizon\LICENSE`); this folder holds no Mojang code, textures or sounds other than
what `horizon-prepare` extracted from the 26.3 client jar for this machine. Minecraft is a
trademark of Mojang Synergies AB; its code and assets belong to Mojang and Microsoft under the
Minecraft EULA.
