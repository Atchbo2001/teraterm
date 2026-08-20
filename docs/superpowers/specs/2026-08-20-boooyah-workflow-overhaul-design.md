# Boooyah Workflow Overhaul Design

Date: 2026-08-20
Status: Approved direction; implementation pending
Branch: `feature/modern-session-ui`

## Product identity

The fork's user-facing product name is **Boooyah**.

Boooyah keeps the proven Tera Term terminal engine, TTSSH implementation, macro engine, serial support, transfer protocols, and compatibility-sensitive internals. User-facing branding may change, but executable/plugin identifiers and other compatibility-sensitive names are not renamed unless a separate compatibility review proves it safe.

The visual identity should feel modern, practical, and technical rather than decorative: dark charcoal native Windows surfaces, restrained electric/cyan accent, consistent spacing, cleaner icons, and strong keyboard focus states. The terminal content area remains visually quiet and fast.

## Product goal

Make the common SSH/serial workflow fast and forgiving for an average Windows user without turning Tera Term into a different application framework.

The target daily loop is:

1. Open Boooyah.
2. Pick a favorite/recent host or detected serial port.
3. Connect with minimal prompts.
4. Work with clear connection state, logging, search, and transfer controls.
5. Recover from dropped connections in-place without losing scrollback.
6. Switch targets or profiles without restarting or editing INI files.

## Non-negotiable behavior

- Network/auth/transport failure never closes the terminal window.
- Scrollback is preserved after TCP/SSH failure.
- Intentional disconnect is quiet and does not nag.
- Authentication cancel/failure returns to a usable window.
- No plaintext password storage.
- Passwords are never placed on command lines.
- Existing TTSSH security fixes remain intact.
- Macro, serial, and plugin compatibility are preserved where practical.
- BSD license and upstream attribution remain intact.

## 1. Disconnected home

When Boooyah is not connected, the main terminal window becomes a useful home surface instead of an empty terminal plus a modal connection dialog.

Primary sections:

- **Quick Connect**: host, username, protocol, port, and Connect button.
- **Favorites**: named profiles pinned by the user.
- **Recent Connections**: recent SSH/Telnet/raw TCP destinations.
- **Serial Ports**: currently detected COM ports with friendly device labels when available.

The surface is non-modal and keyboard navigable. Advanced/legacy settings do not clutter the first screen.

## 2. Session status and recovery bar

A compact native session bar sits above or below the terminal viewport without consuming significant space.

Connected state example:

`SSH • server01 • Connected` with actions for Disconnect, Reconnect, Logging, and overflow actions.

Failure/disconnected state example:

`Disconnected • server01` with actions for Reconnect, Change Server, Profiles, and Close.

The recovery bar is non-modal. It must never cover terminal output or require a mouse.

Session state is explicit:

- Idle
- Connecting
- Connected
- Disconnecting
- Disconnected
- Failed

Disconnect origin is tracked separately so user-requested disconnects differ from network/auth failures.

## 3. Quick Connect and New Connection redesign

The existing New Connection workflow is simplified around normal tasks.

Primary fields:

- Host
- Username
- Protocol: SSH / Telnet / Raw TCP / Serial
- Port
- Favorite/profile selector

Advanced options remain available under an expandable **Advanced** section.

Behavior:

- Remember recent hosts and the last practical connection choices.
- SSH is the obvious network default when appropriate.
- Serial remains first-class and does not require saving an INI before switching ports.
- Changing server from a disconnected session reuses the same window.
- Keyboard focus must always land on a useful control.

## 4. Profiles

Boooyah adds named connection profiles layered over the existing configuration system.

A profile can contain:

- display name
- host
- port
- protocol
- username
- SSH key reference/path
- encoding
- terminal dimensions/behavior
- visual theme
- logging preference
- transfer defaults
- optional macro reference

Profiles never contain plaintext passwords.

Profiles support Favorite and Recent presentation, duplication, rename, export/import where practical, and quick switching from the disconnected home.

## 5. Serial workflow

Serial use is treated as a normal daily workflow rather than a configuration edge case.

Requirements:

- Detect available COM ports each time the connection chooser/home surface opens.
- Allow switching COM ports without editing/saving TERATERM.INI first.
- Show friendly device information when Windows exposes it.
- If a USB serial device disappears, keep the window and scrollback open.
- Reconnect automatically or offer a non-modal retry when the same device returns.
- Avoid blocking "Cannot open COMx" message boxes during expected unplug/replug cycles.
- Preserve normal manual disconnect semantics.

## 6. Logging

Logging becomes visible and easy to understand.

Requirements:

- Clear Start Logging / Stop Logging action.
- Visible recording indicator while logging.
- Remember the previous log directory.
- Optional automatic filename pattern using profile/host and timestamp, for example `server01_2026-08-20_1341.log`.
- Logging state visible from the session bar.
- Preserve existing advanced logging formats/options under Advanced settings.

## 7. File send and transfer workflow

File transfer should preserve user context between repeated operations.

Requirements:

- Remember last-used folder per transfer workflow where practical.
- Remember common transfer options such as sequential read when safe.
- Keep XMODEM/YMODEM/ZMODEM/Kermit/SCP-related existing functionality intact.
- Reduce repeated navigation and checkbox re-entry.
- Surface transfer errors in the terminal/session status area where possible instead of unnecessary blocking dialogs.

## 8. Scrollback search

Add a standard terminal search experience.

- `Ctrl+F` opens an in-window search strip.
- Search current scrollback without modifying terminal contents.
- Next/Previous controls and keyboard navigation.
- Highlight all visible matches and emphasize the active match.
- Escape closes the search strip and returns focus to the terminal.

## 9. Paste safety

Normal single-line paste remains immediate.

Potentially dangerous paste content receives extra handling:

- Multiline paste can show a concise confirmation with line count.
- Control characters are identified before send.
- A user preference can relax/disable warnings.
- Bracketed paste behavior remains compatible with remote shell expectations.

The goal is preventing accidental command floods without making ordinary paste annoying.

## 10. Settings cleanup

Move toward one searchable Settings window while preserving old menu entry points for compatibility/discoverability.

Proposed categories:

- Connection
- Terminal
- Appearance
- Keyboard
- Logging
- Transfers
- Serial
- SSH
- Encoding
- Advanced

Legacy Setup menu items may open the unified Settings window on the corresponding category.

Changes made through normal settings controls persist automatically according to existing Tera Term conventions. Expert/rare settings remain available without dominating the normal workflow.

## 11. Keyboard-first workflow

Target shortcuts:

- `Ctrl+N` — Quick Connect / New Connection
- `Ctrl+R` — Reconnect current/last target
- `Ctrl+F` — Search scrollback
- `Ctrl+,` — Settings
- `Ctrl+Shift+L` — Toggle logging
- `Ctrl+K` — command launcher for common Boooyah actions

All dialogs and non-modal surfaces must have predictable Tab order, visible focus, Escape behavior, and access keys where native Windows conventions support them.

## 12. Command launcher

`Ctrl+K` opens a lightweight command launcher for common application actions, not shell commands.

Examples:

- Connect to profile
- Reconnect
- Disconnect
- Start/Stop Logging
- Send File
- Open Settings
- Change Serial Port
- Duplicate Session
- Run Macro

This is an acceleration layer over existing commands, not a replacement for menus.

## 13. Visual refresh

The refresh stays native and incremental rather than rewriting the application in Electron/WinUI.

Changes:

- Boooyah branding in title/about/start surfaces.
- New Boooyah application icon.
- Cleaner menu labels and grouping.
- Consistent button sizing and dialog spacing.
- Better high-DPI layout.
- Strong focus rectangles and keyboard accessibility.
- Compact status/recovery surfaces.
- Dark charcoal default UI shell with restrained accent where technically safe.

Terminal color themes remain user-controlled and independent from application chrome.

## 14. Error handling principles

Blocking message boxes are reserved for decisions the user must make immediately.

Recoverable operational errors should use non-modal state surfaces:

- connection lost
- host unreachable
- authentication failed/cancelled
- serial device missing
- reconnect failed
- transfer failed

Each error should explain what happened and offer the next useful action.

## 15. Compatibility boundaries

Do not casually rename or replace:

- `ttermpro.exe`
- TTSSH DLL/plugin contracts
- macro command behavior
- INI keys relied on by existing deployments
- serial protocol behavior
- transfer protocol implementations

User-facing product strings can say Boooyah while compatibility-sensitive technical identifiers remain stable unless tested migration support is added.

## 16. Implementation order

Implementation is intentionally staged so each stage can produce a testable Windows build.

1. Complete session-state/origin handling and intentional-disconnect distinction.
2. Add recovery/session bar and reconnect/change-server commands.
3. Add Boooyah branding strings/icon/title surfaces.
4. Build disconnected home + Quick Connect.
5. Add profiles/favorites/recents storage.
6. Fix serial switch/reconnect workflow.
7. Improve logging visibility and remembered log directory/default names.
8. Restore file-send remembered folder/options.
9. Add scrollback search.
10. Add paste safety.
11. Unify settings navigation/search.
12. Add keyboard shortcuts and command launcher.
13. Final DPI/accessibility/menu/dialog cleanup.
14. Run Windows x64 build, regression tests, and artifact verification after each meaningful slice.

## 17. Validation

Every functional slice must be validated through the existing Windows VS2022 build pipeline.

Required behavioral checks include:

- failed SSH auth leaves Boooyah open with scrollback intact
- cancelled SSH auth returns to a usable window
- remote SSH disconnect leaves Boooyah open
- intentional Disconnect remains quiet
- Reconnect works from the same window
- Change Server works from the same window
- serial unplug/replug does not destroy the terminal window
- profiles contain no password field
- logging retains directory and produces expected filename
- file send retains intended folder/options
- `Ctrl+F`, `Ctrl+R`, `Ctrl+N`, `Ctrl+,`, and `Ctrl+K` work without stealing terminal input unexpectedly
- x64 portable ZIP and installer artifacts are produced from the exact tested commit

## Out of scope for this overhaul

- Electron/Chromium rewrite
- embedded AI assistant
- Docker/Kubernetes dashboard
- full SFTP file-manager UI
- multi-pane IDE workspace
- replacing the Tera Term terminal engine

Those can be reconsidered only after the daily SSH/serial workflow is materially better and stable.
