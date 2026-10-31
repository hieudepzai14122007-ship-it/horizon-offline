# Horizon offline — Minecraft: Java Edition 26.3, no Microsoft account

Horizon is Minecraft 26.3 rewritten from scratch in Rust. Its launcher normally refuses to start the
game until a Microsoft account that owns Java Edition is signed in. This build has that check
removed: it plays without an account.

## Set it up (once)

1. **Download this repository** — green **Code** button → **Download ZIP**.
2. **Extract it** somewhere you can write, e.g. `C:\Users\you\Horizon`. Not in `Program Files`.
3. **Double-click `Setup.cmd`.** It builds the game folder: the patched launcher, Horizon's nightly,
   Minecraft 26.3 from Mojang, then the prepared resources. About 700 MB and ten minutes the first
   time, and it prints each step.

### If `Setup.cmd` says Python or Java is missing

Use **`Horizon-Launcher.cmd`** and press Play. The launcher downloads Mojang's own Java 25 and
Minecraft 26.3 and prepares them itself, so nothing needs installing first. (Or install
[Python 3](https://www.python.org/downloads/) and
[Java 25](https://adoptium.net/temurin/releases/?version=25) and run `Setup.cmd` again for the
direct route.)

### What you need

- Windows 10 or 11, 64-bit
- A GPU with Vulkan or DirectX 12 — any discrete card, or recent integrated graphics
- About 3 GB free; about 700 MB downloaded on the first run
- Internet for that first run only

## Run the game

**Double-click `Play-Horizon.cmd`.** No sign-in, no Minecraft install, no Rust.

- The window opens on the title screen. The first launch asks about the Narrator and accessibility
  settings — press **Continue**.
- **Singleplayer → Create New World** (or select a world and **Play Selected World**). It is vanilla
  world generation: same seeds, same terrain, same mobs.
- Mouse look, **WASD** move, **Space** jump, **Shift** sneak, **Ctrl** sprint, **left click** break,
  **right click** place/use, **1–9** or the wheel for the hotbar, **E** inventory, **Q** drop, **F1**
  hide the HUD, **F3** debug screen, **F2** screenshot, **F11** fullscreen, **Esc** pause.
- **Esc → Save and Quit to Title** writes the world to `horizon-windows-x64\saves\`. Copy that folder
  and you have a backup.
- The player name is made up once and kept in `horizon-windows-x64\horizon-player.txt`;
  `Play-Horizon.cmd --name Steve` chooses your own.
- **Play with a friend on your network:** one of you presses **Esc → Open to LAN**, the other
  **Multiplayer → Direct Connect** with the address shown. To join a server at start:
  `Play-Horizon.cmd --server 192.168.1.20:25565` — offline-mode servers only, see
  [What still needs an account](#what-still-needs-an-account).

Prefer the launcher window — version picker, mods, servers, hosting a dedicated server? Double-click
**`Horizon-Launcher.cmd`** and press **Play**.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `Cannot find "...\horizon-windows-x64\horizon-client.exe"` | The folder is not built yet: run `Setup.cmd`, or `Horizon-Launcher.cmd` → Play |
| Tiny menus | Options → Video Settings → GUI Scale → Auto |
| Low frame rate | Options → Video Settings → render distance 12–16 (the default here can be 128) |
| "Sign in to play" appears | The official launcher replaced this one by self-updating: download `horizon-launcher.exe` from [the release](../../releases/latest) over `launcher\horizon-launcher.exe`, and always start it with `Horizon-Launcher.cmd`, which blocks the update |
| Server says "Failed to verify username" | That server verifies accounts with Mojang; no client-side change can join it |
| No sound | `horizon-windows-x64\horizon-prepare.exe sounds --minecraft-dir minecraft` |

More detail, including what is and is not in git: **[GUIDE.md](GUIDE.md)**.

## What the download contains

| In git (a few KB) | Built by `Setup.cmd` |
| --- | --- |
| `Setup.cmd`, `Play-Horizon.cmd`, `Horizon-Launcher.cmd` | `horizon-windows-x64\` — Horizon's own release zip, 29 MB |
| `fetch-minecraft.py` — downloads 26.3 from Mojang, sha1-checked | `minecraft\` — Minecraft 26.3 from Mojang, 650 MB |
| `crates-relay.py`, `prefetch-crates.py` — build helpers for the Rust side | `launcher\horizon-launcher.exe` — the patched launcher, 41 MB, from [the release](../../releases/latest) |
| `launcher-owner-gate-off.patch`, `README.md`, `GUIDE.md` | `horizon-windows-x64\.local\horizon-client\26.3\` — prepared resources, 600 MB |

The game files are not in git on purpose: they are gigabytes, and they are Mojang's. That is also
why the repository ZIP alone is not playable — it is the scripts, not the game. `Setup.cmd` is the
step that turns one into the other.

## What was changed

The gate lives in the launcher only; the game binary never had one. Five files in
`horizon/launcher/src` carry the change, as `launcher-owner-gate-off.patch` against upstream:

- `account.rs` — a new `OWNER_GATE: bool = false`. With it off, `launch_for_game` treats "no account
  owns the game" as "play offline" instead of a refusal, and offline names no longer need an owner.
- `backend.rs` — `download_for` downloads the pinned version from Mojang for anyone (a version's
  files are public at Mojang's; only the launcher's check was asking for an account), and
  `self_update_allowed` refuses to replace this build with the official launcher, which would put
  the gate back.
- `main.rs` — the window treats Play as available, so a fresh install can download, prepare and play
  without a sign-in, and the owner screen never opens.
- `owner_page.rs` — the "Sign in to play" screen is never shown.
- `cli.rs` — help and `account list` no longer claim an account is required.

Sign-in still works and still gives you a session: it is what online-mode servers and chat signing
ask for. It just no longer decides whether you may play at all.

To rebuild the launcher from upstream's source with the patch:

```
git clone https://github.com/horizon-rust/horizon.git
cd horizon && git apply launcher-owner-gate-off.patch
cd launcher && cargo build --release
```

## Where the game files come from

`fetch-minecraft.py` reads Mojang's version manifest, finds 26.3, and downloads what that version's
JSON lists: the client jar, the server jar, the libraries, the asset index and every asset object,
each checked against Mojang's sha1. All of it is public; no account or token involved.

```
python fetch-minecraft.py minecraft --version 26.3
```

Then `horizon-prepare.exe` exports the game's resources from those files (Java 25 needed):

```
cd horizon-windows-x64
horizon-prepare.exe --prepare --server-jar ..\minecraft\server.jar --minecraft-dir ..\minecraft
horizon-prepare.exe sounds --minecraft-dir ..\minecraft
```

## What still needs an account

- **Online-mode servers** (the default for public servers) verify your session with Mojang, whoever
  launches the game. Nothing on this side can change that: use an offline-mode server, your own LAN
  world, or sign in.
- **Chat signing** on servers with `enforce-secure-profile=true` needs the profile key pair, which
  comes from a signed-in account.
- **Realms** are Microsoft's service.

Everything else — single player, LAN, offline-mode servers, mods, packs, the dedicated server — runs
with no account at all.

## Updating the game

The game is a nightly build (`68ac6f6`, 2026-10-31). To move to a newer one, take
`horizon-windows-x64.zip` from <https://github.com/horizon-rust/horizon/releases>, replace the four
`.exe` files in `horizon-windows-x64\`, and run `horizon-prepare.exe --prepare ...` again if that
build pins another Minecraft version.

## Licence

Horizon is MIT; this repository holds none of its game code. Minecraft is a trademark of Mojang
Synergies AB, and its code and assets belong to Mojang and Microsoft under the Minecraft EULA: none
of them are committed here, and each machine prepares its own from Mojang's public download.
