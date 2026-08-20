# Modern Session UI Design

## Goal

Turn the Tera Term fork into a modern, resilient Windows terminal experience without destabilizing the mature terminal emulator, TTSSH transport, macro engine, serial support, or plugin ABI.

## Product principles

- A failed connection must never destroy the terminal window.
- Authentication cancellation is navigation, not application exit.
- Scrollback and error output remain visible after disconnect.
- Recovery actions are explicit: reconnect, change server, profiles, or stay disconnected.
- Intentional disconnect is quiet; unexpected disconnect is actionable.
- Preserve upstream-compatible internals where possible so future rebases remain practical.
- Keep attribution and license text intact.

## Session lifecycle

Introduce a small explicit session-state model around the existing communication lifecycle:

- `Idle`
- `Connecting`
- `Connected`
- `Disconnecting`
- `Disconnected`
- `Failed`

The existing socket/serial code remains responsible for transport. The window layer owns the user-facing state and decides what recovery affordances to show.

TCP/SSH teardown must no longer call the window close path merely because `AutoWinClose` is enabled. The fork will default `AutoWinClose` to off while preserving command-line/config compatibility for users who explicitly set it.

## Disconnect behavior

Unexpected TCP/SSH loss, connection refusal, timeout, authentication failure, and canceled authentication all leave the VT window alive. Existing scrollback is preserved.

File > Disconnect sets an intentional-disconnect flag before transport teardown. When teardown completes, the application moves to `Disconnected` without showing an error/reconnect nag.

Unexpected teardown moves to `Failed` or `Disconnected` with recovery UI visible.

## Recovery UI

The first implementation uses native Win32 controls integrated into the VT window rather than introducing a new UI framework. A non-modal recovery surface presents:

- connection state text
- last host and port when available
- Reconnect
- Change Server
- Profiles
- Close

The terminal remains usable for copying/scrolling while disconnected.

If the full persistent bar proves too invasive for the first compile-safe slice, the implementation may land the state model and commands first, then add the bar in the next commit on the same branch. Modal Yes/No/Cancel recovery dialogs are not the desired end state.

## Connection dialog

Modernize the existing New Connection dialog incrementally using the current resource/dialog system:

- clearer host and port grouping
- protocol shown explicitly
- username field available for SSH workflows
- recent hosts
- saved profile selector
- Advanced section for less-common options
- reconnect/change-server paths prefill the previous host and settings

Serial and Telnet remain available.

## Authentication UX

TTSSH authentication dialogs must return cleanly to the disconnected/connection state when canceled. Wrong credentials should allow retry without destroying the terminal window. Error text should distinguish authentication rejection from network failure where the existing TTSSH callbacks expose that distinction.

Passwords are never written to plain-text profile storage.

## Profiles

Add a small profile layer backed by the existing configuration conventions. A profile stores:

- display name
- host
- port
- protocol
- username
- preferred SSH key path/reference
- terminal/encoding overrides when explicitly set
- optional startup macro

Secrets are excluded.

## Main-window cleanup

Keep the classic terminal rendering area. Improve the chrome around it:

- explicit connection-state indicator
- clearer connection actions
- reorganized high-frequency menu items
- fewer destructive/legacy defaults
- DPI-safe layout
- keyboard-accessible controls
- theme-aware drawing where practical with the existing theme helpers

## Settings behavior

The fork defaults to preserving screen contents on disconnect and keeping windows open. Ordinary UI preferences should save predictably. Existing INI compatibility remains supported.

## Branding

Visible branding will be centralized so the final product name/icon can be changed without renaming `ttermpro.exe`, TTSSH DLL/plugin identifiers, protocol strings, or other compatibility-sensitive internals.

The original BSD-style license and attribution remain in source and binary documentation.

## Build and delivery

Use the existing Windows Server 2022 / Visual Studio 2022 GitHub Actions build pipeline. The fork should publish unsigned x64 test artifacts on feature-branch pushes. x86/ARM64 can remain in the upstream matrix, but x64 is the primary iteration target.

A one-shot source-application workflow may be used to bootstrap changes into the fork because the current ChatGPT runtime cannot clone GitHub from its shell. That workflow must commit the actual modified C/C++/resource files back to the feature branch; it is not the delivered product architecture.

## Validation matrix

At minimum verify:

- successful SSH password login
- wrong SSH password
- cancel password dialog
- successful public-key login
- cancel public-key/auth dialog
- DNS failure
- connection refused
- connection timeout
- remote server closes session
- local network loss
- File > Disconnect
- reconnect same host
- change server in same window
- scrollback remains after disconnect
- New Connection still works when already disconnected
- serial connection regression check
- Telnet regression check
- 100%, 125%, 150%, and 200% DPI smoke checks
- Windows x64 GitHub Actions build and portable ZIP artifact
