# Play Horizon offline, from this link alone

Horizon is Minecraft: Java Edition 26.3 rewritten in Rust. Its launcher normally refuses to start
the game until a Microsoft account that owns Java Edition is signed in; this build has that check
removed, so it plays without an account.

You need: Windows 10/11 (64-bit), a graphics card with Vulkan or DirectX 12 (any discrete GPU or
recent integrated one), about 3 GB free, and internet for the first run (about 700 MB).

## Steps

1. **Download this repository.** Green **Code** button → **Download ZIP**.
2. **Extract it** somewhere you can write, e.g. `C:\Users\you\Horizon`. Not in `Program Files`.
3. **Run `Setup.cmd`** (double-click). It fetches the patched launcher, then — if Python and
   Java are installed — Minecraft 26.3 and the game itself. Ten minutes, mostly downloading.
4. **Play:**
   - `Play-Horizon.cmd` — starts the game straight away, no account, no window in between.
   - `Horizon-Launcher.cmd` — the launcher window (version picker, mods, servers). Press Play.

No Microsoft sign-in anywhere. If a "Sign in to play" screen ever appears, you are running a
launcher that updated itself to the official one — see Troubleshooting.

## The two ways in

**Direct (`Play-Horizon.cmd`)** — the game only. Needs the folder built by `Setup.cmd`, which needs
Python 3.10+ and Java 25 on this PC.

**Launcher (`Horizon-Launcher.cmd`)** — the full launcher, gate removed. It can do everything the
script does: install a game version, download Minecraft 26.3 and Mojang's Java, prepare the
resources, start the game. If `Setup.cmd` said it had no Python or Java, this is the way: press Play
and wait.

Both keep their data inside this folder (`launcher-home\` for the launcher and its game, `saves\`
inside `horizon-windows-x64\` for the direct one), so deleting the folder removes everything.

## What is in the repository, and what is not

| Tracked here | Downloaded by `Setup.cmd` |
| --- | --- |
| `Setup.cmd`, `Play-Horizon.cmd`, `Horizon-Launcher.cmd`, `fix-fullscreen-crash.ps1` | `horizon-windows-x64\` — Horizon's own release zip, 29 MB |
| `fetch-minecraft.py`, `crates-relay.py`, `prefetch-crates.py` | `minecraft\` — Minecraft 26.3 from Mojang, 650 MB |
| `README.md`, `GUIDE.md`, `launcher-owner-gate-off.patch` | `launcher\horizon-launcher.exe` — 41 MB, from this repo's release |
| | `.local\horizon-client\26.3\` — the prepared game resources, 600 MB |

The game binaries and Mojang's files are not in git on purpose: they are gigabytes, and they are
Mojang's. That is also why the repository ZIP alone is not playable — it is the scripts, not the
game. `Setup.cmd` is the step that turns one into the other.

## Troubleshooting

**`Cannot find "...\horizon-windows-x64\horizon-client.exe"`** — the folder has not been built yet.
Run `Setup.cmd`, or use `Horizon-Launcher.cmd` and press Play.

**`Setup.cmd` says it has no Python 3 or Java 25** — use `Horizon-Launcher.cmd`: it downloads
Mojang's Java itself. Or install [Python](https://www.python.org/downloads/) and
[Java 25](https://adoptium.net/temurin/releases/?version=25), then run `Setup.cmd` again.

**The launcher shows "Sign in to play"** — that is the official launcher, which replaced this one by
updating itself. Download `horizon-launcher.exe` from this repository's release again, overwrite
`launcher\horizon-launcher.exe`, and always start it with `Horizon-Launcher.cmd`, which blocks the
self-update.

**It crashes when fullscreen is turned on (`window.rs:744` in the crash report)** — exclusive
fullscreen, refused by Windows on laptops whose screen runs on the integrated GPU. Both launch
scripts patch the game so it carries on in borderless fullscreen instead; start it with them.
Each patched `horizon-client.exe` keeps its original beside it as `horizon-client.exe.orig`.

**The menus are tiny** — Options → Video Settings → GUI Scale → Auto.

**It runs slowly** — Options → Video Settings: render distance 12–16 rather than 128.

**A server says "Failed to verify username" / "online mode"** — that server verifies accounts with
Mojang; nobody can join it without one. Single player, LAN, offline-mode servers and your own
`horizon-server` are fine.

**Sound is missing** — `Setup.cmd` copies it in its last step; run it again, or
`horizon-windows-x64\horizon-prepare.exe sounds --minecraft-dir minecraft` in this folder.

## Sharing this with someone else

Send them this repository link — that is all they need. They do not need a Microsoft account, a
Minecraft install, Rust, or this folder. First run downloads about 700 MB from Mojang and from
GitHub's release page.

The one thing not to do is commit `horizon-windows-x64\`, `minecraft\`, `launcher-home\` or
`launcher\` to the repository: the first three are gigabytes and hold Mojang's assets, which is
what the repository's `.gitignore` keeps out.
