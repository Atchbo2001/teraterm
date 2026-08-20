# Modern Session UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modernize Tera Term's connection/session UX so failed or closed connections keep the terminal alive, expose clear recovery actions, preserve scrollback, and produce real Windows x64 build artifacts from the fork.

**Architecture:** Keep the existing VT renderer, comms layer, TTSSH, macro engine, and plugin ABI. Add a small window-owned session-state abstraction and route disconnect/reconnect behavior through it; modernize UI incrementally using native Win32 resources/controls so upstream rebases stay practical. Use the existing GitHub Actions Windows/MSBuild pipeline for compile verification and packaged artifacts.

**Tech Stack:** C/C++, Win32/MFC-style window code, RC resources, existing Tera Term config/TTSSH interfaces, GitHub Actions, Visual Studio 2022.

**Spec:** `docs/superpowers/specs/2026-08-20-modern-session-ui-design.md`

## Global Constraints

- Do not rewrite the terminal emulator, TTSSH protocol implementation, macro engine, serial transport, or plugin ABI.
- Do not store passwords in plaintext profiles.
- Preserve the existing BSD-style license and attribution.
- Preserve compatibility-sensitive internal executable/plugin identifiers unless a later dedicated compatibility review approves renaming.
- Unexpected TCP/SSH disconnects and authentication failures must leave the VT window open with scrollback intact.
- File > Disconnect must be treated as intentional and must not nag the user to reconnect.
- Windows x64 is the primary iteration target; existing x86/ARM64 build compatibility should not be intentionally broken.

---

### Task 1: Add a testable session-state policy

**Files:**
- Create: `teraterm/teraterm/session_state.h`
- Create: `teraterm/teraterm/session_state.cpp`
- Create: `teraterm/teraterm/session_state_test.cpp`
- Modify: `teraterm/teraterm/CMakeLists.txt` or the existing project file only if required to compile the new unit under an existing test target.

**Interfaces:**
- Produces: `enum class SessionState { Idle, Connecting, Connected, Disconnecting, Disconnected, Failed }`
- Produces: `enum class DisconnectOrigin { None, UserRequested, RemoteOrNetwork, Authentication }`
- Produces: `SessionTransition HandleDisconnect(SessionState current, DisconnectOrigin origin)` returning `{SessionState next, bool show_recovery, bool close_window}`.

- [ ] **Step 1: Write a failing unit test** covering remote/network disconnect, user-requested disconnect, and authentication cancellation. The expected contract is `close_window == false` in every case; recovery is shown for unexpected/auth failures but not for user-requested disconnect.
- [ ] **Step 2: Run the test in Windows CI and verify RED** because `session_state.*` does not exist yet.
- [ ] **Step 3: Implement the minimal state-policy files** with no Win32 dependencies.
- [ ] **Step 4: Re-run the test and verify GREEN.**
- [ ] **Step 5: Commit only the new policy/test/build-registration files.**

### Task 2: Route VT-window disconnect behavior through the policy

**Files:**
- Modify: `teraterm/teraterm/vtwin.h`
- Modify: `teraterm/teraterm/vtwin.cpp`
- Test: extend `session_state_test.cpp` for every new policy rule before integration changes.

**Interfaces:**
- Consumes: `SessionState`, `DisconnectOrigin`, `HandleDisconnect()`.
- Produces in `CVTWindow`: fields tracking current session state and pending intentional disconnect origin.
- Produces helpers: `SetSessionState(...)`, `MarkUserDisconnect()`, `HandleSessionEnded(...)`.

- [ ] **Step 1: Add failing policy tests** for transition `Connecting -> Failed` and `Connected -> Disconnected` on unexpected teardown.
- [ ] **Step 2: Verify RED in CI.**
- [ ] **Step 3: Update `CVTWindow` initialization** so the state starts `Idle`/`Connecting` consistently with existing startup flow.
- [ ] **Step 4: Update the `IdComEndTimer` completion path** so TCP/SSH teardown no longer calls `OnClose()` solely because `AutoWinClose` is enabled; instead it calls `HandleSessionEnded(...)`, keeps the window alive, and preserves scrollback.
- [ ] **Step 5: Ensure `ClearScreenOnCloseConnection` is not triggered for unexpected TCP/SSH disconnect in the fork's default path.** Existing explicit user configuration may remain supported.
- [ ] **Step 6: Run Windows build/tests and verify GREEN.**
- [ ] **Step 7: Commit the integration changes.**

### Task 3: Distinguish intentional disconnect from failure

**Files:**
- Modify: `teraterm/teraterm/vtwin.cpp`
- Modify: `teraterm/teraterm/vtwin.h`
- Test: `teraterm/teraterm/session_state_test.cpp`

**Interfaces:**
- Consumes: `DisconnectOrigin::UserRequested`.
- Produces: File > Disconnect marks the pending origin before invoking existing transport shutdown.

- [ ] **Step 1: Add a failing test** proving `UserRequested` teardown yields `Disconnected`, `show_recovery == false`, `close_window == false`.
- [ ] **Step 2: Verify RED if the rule is not yet represented by the integration helper.**
- [ ] **Step 3: Mark the disconnect origin in the existing File > Disconnect command path.**
- [ ] **Step 4: Clear the origin after teardown completes so later remote drops are not misclassified.**
- [ ] **Step 5: Run Windows build/tests and verify GREEN.**
- [ ] **Step 6: Commit.**

### Task 4: Add first-pass recovery commands

**Files:**
- Modify: `teraterm/teraterm/vtwin.h`
- Modify: `teraterm/teraterm/vtwin.cpp`
- Modify: `teraterm/teraterm/tt_res.h`
- Modify: relevant `.rc` menu/resource files under `teraterm/teraterm/`.

**Interfaces:**
- Produces commands: `Reconnect`, `Change Server`, `Profiles` placeholder/entry point.
- `Reconnect` reuses the last successful/requested TCP host/port settings and existing New Connection machinery in the same VT window.
- `Change Server` calls the existing `OnFileNewConnection()` while disconnected, prefilled from current settings/history.

- [ ] **Step 1: Add a failing state-policy test** proving reconnect is only offered when the last transport was TCP/IP and a host is known.
- [ ] **Step 2: Verify RED.**
- [ ] **Step 3: Add command IDs/resources and message routing.**
- [ ] **Step 4: Implement `Reconnect` by reusing existing connection setup rather than spawning a new terminal process.**
- [ ] **Step 5: Implement `Change Server` as an explicit command into the existing New Connection flow.**
- [ ] **Step 6: Add a non-destructive Profiles menu entry that can land before the profile manager itself.**
- [ ] **Step 7: Run Windows build/tests and verify GREEN.**
- [ ] **Step 8: Commit.**

### Task 5: Make safer fork defaults

**Files:**
- Modify: `teraterm/ttpset/ttset.c`
- Modify: shipped default INI/template files containing `AutoWinClose` or `ClearScreenOnCloseConnection`.

**Interfaces:**
- Existing config keys remain readable/writeable.
- Default `AutoWinClose` becomes off when no explicit value is present.
- Default `ClearScreenOnCloseConnection` remains off.

- [ ] **Step 1: Add a focused config/default check** in an existing suitable test or CI grep/assert script that fails while `AutoWinClose` defaults on.
- [ ] **Step 2: Verify RED.**
- [ ] **Step 3: Change only the default behavior, not the key name or parser compatibility.**
- [ ] **Step 4: Verify GREEN and build.**
- [ ] **Step 5: Commit.**

### Task 6: Add a native non-modal disconnected recovery bar

**Files:**
- Create: `teraterm/teraterm/session_bar.h`
- Create: `teraterm/teraterm/session_bar.cpp`
- Modify: `teraterm/teraterm/vtwin.h`
- Modify: `teraterm/teraterm/vtwin.cpp`
- Modify: project/CMake registration files as required.

**Interfaces:**
- Produces `SessionBar` owned by `CVTWindow` with `Show(state, host, port)`, `Hide()`, and command callbacks for reconnect/change-server/profiles/close.
- Uses Win32 child controls and existing theme/DPI helpers; it must not own transport state.

- [ ] **Step 1: Add unit-level tests for the presentation model** (text/buttons visible by state) without Win32 window creation.
- [ ] **Step 2: Verify RED.**
- [ ] **Step 3: Implement the presentation model.**
- [ ] **Step 4: Implement the Win32 bar wrapper and integrate resize/DPI handling.**
- [ ] **Step 5: Show on `Failed`/unexpected `Disconnected`; hide on `Connecting`/`Connected`; keep hidden after intentional disconnect until the user invokes a connection action.**
- [ ] **Step 6: Run x64 Windows build and DPI smoke checks via manual artifact testing.**
- [ ] **Step 7: Commit.**

### Task 7: Modernize the New Connection dialog incrementally

**Files:**
- Modify: `teraterm/ttpdlg/ttpdlg.rc`
- Modify: associated dialog implementation/source files in `teraterm/ttpdlg/` discovered from the dialog resource IDs.
- Modify: relevant resource header(s).

**Interfaces:**
- Preserve the existing connection-setting structures consumed by the rest of Tera Term.
- Add clearer grouping, explicit protocol/port labels, recent-host selection, and room for profile selection without changing transport ABI.

- [ ] **Step 1: Add parser/model tests for recent-host/profile selection where non-UI logic can be isolated.**
- [ ] **Step 2: Verify RED.**
- [ ] **Step 3: Refactor dialog data preparation into a testable model if needed.**
- [ ] **Step 4: Update RC layout with DPI-safe spacing and keyboard tab order.**
- [ ] **Step 5: Ensure reconnect/change-server prefill the prior host and port.**
- [ ] **Step 6: Build x64 and manually inspect screenshots/artifact on 100/125/150/200% DPI.**
- [ ] **Step 7: Commit.**

### Task 8: Improve TTSSH authentication cancellation/failure navigation

**Files:**
- Modify: exact TTSSH authentication dialog/callback files under `ttssh2/ttxssh/` discovered by tracing dialog cancel and authentication failure callbacks.
- Test: add focused non-UI state tests where callbacks can be isolated.

**Interfaces:**
- Cancellation returns control to the existing VT window/disconnected state.
- Authentication rejection reports failure without closing the VT window.
- No plaintext password persistence.

- [ ] **Step 1: Add a failing test around the extracted auth-result mapping.**
- [ ] **Step 2: Verify RED.**
- [ ] **Step 3: Extract/implement auth-result mapping and feed the window/session layer an authentication-origin failure.**
- [ ] **Step 4: Preserve retry semantics where TTSSH already supports them.**
- [ ] **Step 5: Build and manually test password, public-key, keyboard-interactive, and cancel paths.**
- [ ] **Step 6: Commit.**

### Task 9: Add profile storage without secrets

**Files:**
- Create: `teraterm/common/connection_profile.h`
- Create: `teraterm/common/connection_profile.cpp`
- Create: tests under the repository's existing test pattern.
- Modify: config-loading/writing code under `teraterm/ttpset/` only through a small profile API.

**Interfaces:**
- Produces `ConnectionProfile` with name, host, port, protocol, username, key reference/path, optional encoding/terminal overrides, optional startup macro.
- Produces load/save/list/delete functions.
- Explicitly excludes passwords/secrets.

- [ ] **Step 1: Write failing round-trip tests including Unicode names/hosts and proof that no password field exists or is serialized.**
- [ ] **Step 2: Verify RED.**
- [ ] **Step 3: Implement minimal storage in an INI-compatible dedicated section/file.**
- [ ] **Step 4: Verify GREEN.**
- [ ] **Step 5: Connect the Profiles command and New Connection selector to this API.**
- [ ] **Step 6: Build/test.**
- [ ] **Step 7: Commit.**

### Task 10: Fork-focused x64 artifact workflow

**Files:**
- Create: `.github/workflows/fork-x64-build.yml`

**Interfaces:**
- Reuses upstream `installer/release.bat`/Visual Studio 2022 build conventions.
- Uploads unsigned x64 portable ZIP and installer artifacts on pushes to `feature/**` and manual dispatch.

- [ ] **Step 1: Add workflow with x64-only build and artifact upload.**
- [ ] **Step 2: Push and observe workflow.**
- [ ] **Step 3: If red, inspect job logs and fix workflow/build issues without weakening compiler errors.**
- [ ] **Step 4: Verify the x64 ZIP artifact exists and contains `ttermpro.exe` plus TTSSH/runtime files.**
- [ ] **Step 5: Commit workflow fixes.**

### Task 11: UI/UX cleanup review after the recovery flow is stable

**Files:**
- Modify only files directly supporting findings from the review; no blanket refactor.
- Document findings in `docs/fork/ux-review.md`.

**Interfaces:**
- No new framework dependency.
- Findings prioritized by user impact and merge risk.

- [ ] **Step 1: Review menus, toolbars, setup dialogs, logging/file transfer entry points, settings persistence, accessibility, keyboard shortcuts, error messages, and DPI behavior.**
- [ ] **Step 2: Write the prioritized review with `P0/P1/P2` findings and exact source locations.**
- [ ] **Step 3: Implement P0/P1 items that are low-to-medium merge risk using test-first changes.**
- [ ] **Step 4: Build/test after each independent item and commit separately.**

### Task 12: Final verification and draft PR

**Files:**
- No new production files unless verification exposes a bug; any bug fix starts with a failing regression test.

- [ ] **Step 1: Run/inspect all relevant Windows x64 build checks.**
- [ ] **Step 2: Download the x64 artifact and verify expected binaries/config files are present.**
- [ ] **Step 3: Compare `main...feature/modern-session-ui` and review every changed file for accidental branding/license/internal-ID damage.**
- [ ] **Step 4: Create a draft PR from `feature/modern-session-ui` to `main` with test matrix and artifact instructions.**
- [ ] **Step 5: Do not merge without explicit user authorization.**
