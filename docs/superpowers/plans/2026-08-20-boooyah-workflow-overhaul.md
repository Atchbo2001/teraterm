# Boooyah Workflow Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing Tera Term fork into the user-facing **Boooyah** terminal with a faster SSH/serial daily workflow, resilient in-window recovery, profiles, visible logging, remembered transfer state, scrollback search, paste safety, unified settings navigation, keyboard shortcuts, and a native Windows visual refresh.

**Architecture:** Keep the existing terminal engine, TTSSH, macros, serial stack, transfer protocols, and compatibility-sensitive executable/plugin identifiers intact. Put new Boooyah behavior into small C/C++ policy/storage/view modules, then integrate those modules through `CVTWindow`, the existing host dialog, existing logging/transfer/clipboard code, and existing property-sheet settings. Every functional slice gets a focused policy/unit test where logic can be isolated, followed by the full Windows VS2022 build before moving on.

**Tech Stack:** Win32/MFC-compatible native C/C++, existing Tera Term `tmfc` wrappers, `.rc` resources, INI persistence, CMake/VS2022, GitHub Actions Windows Server 2022.

**Spec:** `docs/superpowers/specs/2026-08-20-boooyah-workflow-overhaul-design.md`

## Global Constraints

- User-facing product name is **Boooyah**.
- Network/auth/transport failure never closes the terminal window.
- Scrollback is preserved after TCP/SSH failure.
- Intentional disconnect is quiet and does not nag.
- Authentication cancel/failure returns to a usable window.
- No plaintext password storage.
- Passwords are never placed on command lines.
- Existing TTSSH security fixes remain intact.
- Preserve macro, serial, and plugin compatibility where practical.
- Preserve BSD license and upstream attribution.
- Keep `ttermpro.exe`, TTSSH DLL/plugin contracts, macro command behavior, and existing compatibility-sensitive INI keys stable.
- Do not rewrite the application in Electron, WinUI, or another framework.
- Every meaningful slice must build in the existing VS2022 Windows pipeline before the next slice is considered complete.

---

## File structure and ownership

New Boooyah-specific units:

- `teraterm/teraterm/boooyah_branding.h` — centralized user-facing product strings only.
- `teraterm/teraterm/session_state.h` — session-state/origin policy; extend existing file instead of creating a competing state machine.
- `teraterm/teraterm/session_state_test.cpp` — pure policy tests.
- `teraterm/teraterm/session_bar.h/.cpp` — compact native status/recovery bar owned by the VT window.
- `teraterm/teraterm/boooyah_home.h/.cpp` — disconnected home / Quick Connect model and Win32 child controls.
- `teraterm/teraterm/boooyah_profiles.h/.cpp` — named profile/favorite/recent serialization with no password field.
- `teraterm/teraterm/boooyah_profiles_test.cpp` — profile round-trip and no-password tests.
- `teraterm/teraterm/paste_policy.h/.cpp` — pure multiline/control-character paste classification.
- `teraterm/teraterm/paste_policy_test.cpp` — paste safety tests.
- `teraterm/teraterm/search_state.h/.cpp` — scrollback-search query/navigation state independent of drawing.
- `teraterm/teraterm/search_state_test.cpp` — search navigation tests.
- `teraterm/teraterm/command_launcher.h/.cpp` — native modeless command launcher over existing application commands.

Primary integration points:

- `teraterm/teraterm/vtwin.h/.cpp` — per-window session state, disconnect origin, recovery commands, child-view layout, shortcuts, logging/search/home integration.
- `teraterm/teraterm/teraterm.cpp` / `teraterml.h` — modeless-window registration where needed.
- `teraterm/teraterm/CMakeLists.txt` — register new Boooyah source files.
- `teraterm/common/tt_res.h` and `teraterm/teraterm/ttermpro.rc` — command IDs, menu/accelerator entries, Boooyah resources.
- `teraterm/ttpdlg/hostdlg.c`, `teraterm/ttpdlg/ttpdlg.rc`, `teraterm/ttpdlg/dlg_res.h` — simplified Quick Connect/New Connection surface and focus behavior.
- `teraterm/ttpdlg/aboutdlg.c` — Boooyah About surface while retaining upstream attribution.
- `teraterm/teraterm/addsetting.h/.cpp` — unified settings entry/category navigation.
- `teraterm/ttpset/ttset.c` — Boooyah INI defaults and persistence keys that do not break legacy keys.
- `teraterm/teraterm/filesys_log.cpp/.h` and `logdlg.cpp` — logging status/default-name integration.
- `teraterm/teraterm/sendfiledlg.cpp/.h` — remembered transfer directory/options.
- `teraterm/teraterm/clipboar.c` — paste-policy integration.
- `teraterm/teraterm/buffer.c/.h`, `vtdisp.c`, `vtdraw.cpp` — read-only scrollback search and match highlighting.

---

### Task 1: Finish explicit session/origin handling

**Files:**
- Modify: `teraterm/teraterm/session_state.h`
- Modify: `teraterm/teraterm/session_state_test.cpp`
- Modify: `teraterm/teraterm/vtwin.h`
- Modify: `teraterm/teraterm/vtwin.cpp`
- Modify: `.github/workflows/fork-session-policy-test.yml`

**Interfaces:**
- Produces: `SessionState`, `DisconnectOrigin`, `SessionTransition HandleDisconnect(SessionState, DisconnectOrigin)`.
- Produces per-window members: `SessionState session_state_` and `DisconnectOrigin pending_disconnect_origin_`.
- Produces: `void CVTWindow::SetSessionState(SessionState state)` and `void CVTWindow::MarkDisconnectOrigin(DisconnectOrigin origin)`.

- [ ] **Step 1: Extend the failing policy tests**

Add cases proving intentional disconnect is quiet and authentication cancellation/failure remains recoverable:

```cpp
assert(HandleDisconnect(SessionState::Connected, DisconnectOrigin::UserRequested).show_recovery == false);
assert(HandleDisconnect(SessionState::Connected, DisconnectOrigin::UserRequested).close_window == false);
assert(HandleDisconnect(SessionState::Connecting, DisconnectOrigin::Authentication).next == SessionState::Failed);
assert(HandleDisconnect(SessionState::Connecting, DisconnectOrigin::Authentication).show_recovery == true);
assert(HandleDisconnect(SessionState::Connected, DisconnectOrigin::RemoteOrNetwork).next == SessionState::Disconnected);
```

- [ ] **Step 2: Run the policy test and confirm the new assertions fail before integration is complete**

Run on Windows CI:

```cmd
cl /nologo /std:c++17 /EHsc /W4 /WX teraterm\teraterm\session_state_test.cpp teraterm\teraterm\session_state.cpp /Fe:session_state_test.exe
session_state_test.exe
```

Expected before implementation: at least one new origin/state assertion fails or integration members are absent from compilation.

- [ ] **Step 3: Add per-window state/origin fields and transitions**

Initialize `session_state_ = SessionState::Idle` and `pending_disconnect_origin_ = DisconnectOrigin::None` in `CVTWindow`. Set UserRequested immediately before `OnFileDisconnect()` posts the close notification. Network close uses RemoteOrNetwork only when no explicit origin is pending. Reset origin to `None` after the transport-end timer consumes it.

- [ ] **Step 4: Remove the current throwaway transition variable**

Replace the current `const SessionTransition transition ...; (void)transition;` path with state storage and recovery visibility decisions. Preserve the already-landed invariant that transport teardown never calls `OnClose()`.

- [ ] **Step 5: Run policy tests and full Windows build**

Expected: policy test exits 0; `Build installer` succeeds for x64.

- [ ] **Step 6: Commit**

```bash
git add -- teraterm/teraterm/session_state.h teraterm/teraterm/session_state_test.cpp teraterm/teraterm/vtwin.h teraterm/teraterm/vtwin.cpp .github/workflows/fork-session-policy-test.yml
git commit -m "feat: track Boooyah session state and disconnect origin"
```

---

### Task 2: Add Boooyah branding without breaking compatibility identifiers

**Files:**
- Create: `teraterm/teraterm/boooyah_branding.h`
- Modify: `teraterm/teraterm/CMakeLists.txt`
- Modify: `teraterm/teraterm/vtwin.cpp`
- Modify: `teraterm/ttpdlg/hostdlg.c`
- Modify: `teraterm/ttpdlg/aboutdlg.c`
- Modify: `teraterm/ttpdlg/ttpdlg.rc`
- Modify: `teraterm/teraterm/ttermpro.rc`

**Interfaces:**
- Produces constants:

```cpp
#define BOOOYAH_PRODUCT_NAME_W L"Boooyah"
#define BOOOYAH_PRODUCT_NAME_A "Boooyah"
#define BOOOYAH_WINDOW_PREFIX_W L"Boooyah"
```

- [ ] **Step 1: Add centralized branding constants**

Only user-visible strings use Boooyah. Do not change `ttermpro.exe`, class names, DLL contracts, or INI section names in this task.

- [ ] **Step 2: Replace visible hard-coded captions in the primary workflow**

Change New Connection, About, file/log dialog prefixing, and main title fallback to Boooyah while retaining “Based on Tera Term / TeraTerm Project” attribution in About.

- [ ] **Step 3: Add a Boooyah icon resource using a new resource ID while retaining legacy IDs for compatibility**

The resource script may alias the existing icon for the first branding build; the final custom artwork can replace only the resource payload later without changing IDs.

- [ ] **Step 4: Build x64 and inspect resource compilation**

Expected: `rc.exe` and link succeed; `ttermpro.exe` remains the output filename.

- [ ] **Step 5: Commit**

```bash
git add -- teraterm/teraterm/boooyah_branding.h teraterm/teraterm/CMakeLists.txt teraterm/teraterm/vtwin.cpp teraterm/ttpdlg/hostdlg.c teraterm/ttpdlg/aboutdlg.c teraterm/ttpdlg/ttpdlg.rc teraterm/teraterm/ttermpro.rc
git commit -m "feat: brand user-facing terminal as Boooyah"
```

---

### Task 3: Build the native session/recovery bar

**Files:**
- Create: `teraterm/teraterm/session_bar.h`
- Create: `teraterm/teraterm/session_bar.cpp`
- Modify: `teraterm/teraterm/CMakeLists.txt`
- Modify: `teraterm/teraterm/vtwin.h`
- Modify: `teraterm/teraterm/vtwin.cpp`
- Modify: `teraterm/common/tt_res.h`
- Modify: `teraterm/teraterm/ttermpro.rc`

**Interfaces:**

```cpp
struct SessionBarModel {
    SessionState state;
    DisconnectOrigin origin;
    std::wstring target;
    bool logging;
};

class SessionBar {
public:
    bool Create(HWND parent);
    void Destroy();
    void Layout(const RECT &client);
    void Update(const SessionBarModel &model);
    int HeightForDpi(UINT dpi) const;
};
```

- [ ] **Step 1: Add command IDs**

Add `ID_FILE_RECONNECT`, `ID_FILE_CHANGESERVER`, and `ID_FILE_PROFILES` adjacent to existing file-menu command IDs without changing existing numeric values.

- [ ] **Step 2: Implement a compact child window with native buttons/static text**

Connected state shows target + state + logging. Failed/disconnected state shows Reconnect / Change Server / Profiles. UserRequested disconnected state may hide recovery actions.

- [ ] **Step 3: Wire commands into existing handlers**

`Reconnect` reuses the last connection record and `CommOpen` flow; `Change Server` calls `OnFileNewConnection()` in the same process/window; `Profiles` initially opens the existing New Connection/profile chooser until Task 5.

- [ ] **Step 4: Adjust `OnSize`/DPI layout so the bar never covers terminal content**

Reserve the bar height before calculating terminal client area. Reflow on DPI changes.

- [ ] **Step 5: Build x64 and manually verify keyboard activation via menu/access keys**

Expected: recovery bar appears after network failure and no terminal output is erased.

- [ ] **Step 6: Commit**

```bash
git add -- teraterm/teraterm/session_bar.h teraterm/teraterm/session_bar.cpp teraterm/teraterm/CMakeLists.txt teraterm/teraterm/vtwin.h teraterm/teraterm/vtwin.cpp teraterm/common/tt_res.h teraterm/teraterm/ttermpro.rc
git commit -m "feat: add Boooyah session recovery bar"
```

---

### Task 4: Disconnected home and Quick Connect

**Files:**
- Create: `teraterm/teraterm/boooyah_home.h`
- Create: `teraterm/teraterm/boooyah_home.cpp`
- Modify: `teraterm/teraterm/CMakeLists.txt`
- Modify: `teraterm/teraterm/vtwin.h`
- Modify: `teraterm/teraterm/vtwin.cpp`
- Modify: `teraterm/ttpdlg/hostdlg.c`
- Modify: `teraterm/ttpdlg/ttpdlg.rc`
- Modify: `teraterm/ttpdlg/dlg_res.h`

**Interfaces:**

```cpp
struct QuickConnectRequest {
    std::wstring host;
    std::wstring username;
    int port;
    enum class Protocol { Ssh, Telnet, RawTcp, Serial } protocol;
    int com_port;
};
```

`BoooyahHome` emits a `QuickConnectRequest`; `CVTWindow` translates that request into the existing `GetHNRec`/TTSSH path rather than opening a second terminal implementation.

- [ ] **Step 1: Refactor connection-choice data away from raw dialog controls**

Extract conversion helpers from `hostdlg.c` so host/port/protocol/COM selection can be populated from either the modal dialog or the home surface.

- [ ] **Step 2: Implement home child controls**

Show Quick Connect, Favorites placeholder/list, Recent list from existing host history, and detected COM ports from `ComPortInfoGet()` with friendly names.

- [ ] **Step 3: Show home only for Idle/Disconnected/Failed states when no active terminal interaction is required**

Do not destroy scrollback; home overlays only the unused terminal viewport region in a way that can be hidden instantly when the user chooses to inspect old output.

- [ ] **Step 4: Simplify modal New Connection layout**

Primary controls: host, protocol, port, username where TTSSH integration permits; serial chooser stays first-class. Keep legacy IP-version/advanced controls behind an Advanced affordance or secondary group.

- [ ] **Step 5: Build x64 and verify SSH, raw TCP, Telnet, and serial selection still enter existing connection code**

- [ ] **Step 6: Commit**

```bash
git add -- teraterm/teraterm/boooyah_home.h teraterm/teraterm/boooyah_home.cpp teraterm/teraterm/CMakeLists.txt teraterm/teraterm/vtwin.h teraterm/teraterm/vtwin.cpp teraterm/ttpdlg/hostdlg.c teraterm/ttpdlg/ttpdlg.rc teraterm/ttpdlg/dlg_res.h
git commit -m "feat: add Boooyah disconnected home and quick connect"
```

---

### Task 5: Profiles, favorites, and recents

**Files:**
- Create: `teraterm/teraterm/boooyah_profiles.h`
- Create: `teraterm/teraterm/boooyah_profiles.cpp`
- Create: `teraterm/teraterm/boooyah_profiles_test.cpp`
- Modify: `teraterm/teraterm/CMakeLists.txt`
- Modify: `teraterm/teraterm/boooyah_home.cpp`
- Modify: `teraterm/teraterm/vtwin.cpp`
- Modify: `teraterm/ttpset/ttset.c`
- Modify: `.github/workflows/fork-session-policy-test.yml`

**Interfaces:**

```cpp
struct BoooyahProfile {
    std::wstring name;
    std::wstring host;
    int port;
    std::wstring protocol;
    std::wstring username;
    std::wstring key_path;
    std::wstring encoding;
    std::wstring theme;
    std::wstring log_pattern;
    std::wstring macro_path;
    bool favorite;
};

bool LoadBoooyahProfiles(const wchar_t *ini_path, std::vector<BoooyahProfile> *out);
bool SaveBoooyahProfiles(const wchar_t *ini_path, const std::vector<BoooyahProfile> &profiles);
```

- [ ] **Step 1: Write profile round-trip tests before storage implementation**

Tests must prove every allowed field round-trips and that the serialized representation contains no key named `password`, `passwd`, or `secret`.

- [ ] **Step 2: Implement INI-backed profile sections under a Boooyah-specific namespace**

Use new sections such as `[BoooyahProfiles]` and `[BoooyahProfile.<stable-id>]`; never mutate legacy host-history keys while merely reading profiles.

- [ ] **Step 3: Integrate Favorites and Recent Connections into home**

A successful connection updates recent ordering. Favorite is a profile flag, not a password store.

- [ ] **Step 4: Add profile actions**

Connect, duplicate, rename, delete, export/import using text INI fragments that omit credentials.

- [ ] **Step 5: Run profile tests and full x64 build**

- [ ] **Step 6: Commit**

```bash
git add -- teraterm/teraterm/boooyah_profiles.h teraterm/teraterm/boooyah_profiles.cpp teraterm/teraterm/boooyah_profiles_test.cpp teraterm/teraterm/CMakeLists.txt teraterm/teraterm/boooyah_home.cpp teraterm/teraterm/vtwin.cpp teraterm/ttpset/ttset.c .github/workflows/fork-session-policy-test.yml
git commit -m "feat: add Boooyah profiles favorites and recents"
```

---

### Task 6: Fix serial switching and reconnect UX

**Files:**
- Modify: `teraterm/teraterm/vtwin.cpp`
- Modify: `teraterm/teraterm/vtwin.h`
- Modify: `teraterm/ttpdlg/hostdlg.c`
- Modify: `teraterm/ttpdlg/serialdlg.cpp`
- Modify: `teraterm/teraterm/session_bar.cpp`
- Modify: `teraterm/teraterm/boooyah_home.cpp`

**Interfaces:**
- Reuse existing `SerialReconnect` implementation in `vtwin.cpp` rather than create a second device watcher.
- Add `SerialReconnect::RequestedPort()` and a non-modal status callback into `CVTWindow`.

- [ ] **Step 1: Make serial choices always refresh from `ComPortInfoGet()` when opening home/New Connection**

Never require a saved `TERATERM.INI` COM selection before showing a newly detected port.

- [ ] **Step 2: Route expected unplug/open failures into session status instead of blocking message boxes**

Expected states: `Serial device missing`, `Waiting for COM11`, `Reconnecting COM11`, `Reconnect failed`.

- [ ] **Step 3: Keep scrollback/window alive on unplug and reuse the existing reconnect timer**

Do not auto-close or clear buffer.

- [ ] **Step 4: Add Change Serial Port action from disconnected home/recovery bar**

Selecting a different COM port reuses the same window and existing `CommOpen` flow.

- [ ] **Step 5: Build x64 and regression-check network paths remain unchanged**

- [ ] **Step 6: Commit**

```bash
git add -- teraterm/teraterm/vtwin.cpp teraterm/teraterm/vtwin.h teraterm/ttpdlg/hostdlg.c teraterm/ttpdlg/serialdlg.cpp teraterm/teraterm/session_bar.cpp teraterm/teraterm/boooyah_home.cpp
git commit -m "feat: improve Boooyah serial switching and reconnect"
```

---

### Task 7: Make logging and file-send state practical

**Files:**
- Modify: `teraterm/teraterm/filesys_log.cpp`
- Modify: `teraterm/teraterm/filesys_log.h`
- Modify: `teraterm/teraterm/logdlg.cpp`
- Modify: `teraterm/teraterm/sendfiledlg.cpp`
- Modify: `teraterm/teraterm/sendfiledlg.h`
- Modify: `teraterm/teraterm/session_bar.cpp`
- Modify: `teraterm/teraterm/vtwin.cpp`
- Modify: `teraterm/ttpset/ttset.c`

**Interfaces:**

```cpp
bool FLogIsOpend(void); // existing
const wchar_t *FLogGetFilename(void); // existing
void SessionBar::Update(const SessionBarModel &model); // Task 3
```

New persisted Boooyah keys:
- `BoooyahLogDir`
- `BoooyahLogPattern` default `&h_%Y-%m-%d_%H%M%S.log`
- `BoooyahSendFileDir`
- `BoooyahSendSequential`
- `BoooyahSendBinary`

- [ ] **Step 1: Expose logging state in the session bar**

Show a concise recording indicator and filename tooltip when `FLogIsOpend()` is true.

- [ ] **Step 2: Add one-action Start/Stop Logging command**

`Ctrl+Shift+L` starts using remembered/default directory and pattern; if logging is active it stops. Advanced options remain in the existing log dialog.

- [ ] **Step 3: Persist the last successful log directory and safe default pattern**

Reuse existing `ConvertLognameW()` expansion so host/time substitution does not fork another naming engine.

- [ ] **Step 4: Persist send-file directory and common safe options after successful dialog acceptance**

Initialize `sendfiledlgdata.initial_dir`, `binary`, and `sequential_read` from remembered values. Do not silently persist a failed/cancelled selection.

- [ ] **Step 5: Build x64 and verify existing transfer protocols are untouched**

- [ ] **Step 6: Commit**

```bash
git add -- teraterm/teraterm/filesys_log.cpp teraterm/teraterm/filesys_log.h teraterm/teraterm/logdlg.cpp teraterm/teraterm/sendfiledlg.cpp teraterm/teraterm/sendfiledlg.h teraterm/teraterm/session_bar.cpp teraterm/teraterm/vtwin.cpp teraterm/ttpset/ttset.c
git commit -m "feat: streamline Boooyah logging and file send"
```

---

### Task 8: Add scrollback search

**Files:**
- Create: `teraterm/teraterm/search_state.h`
- Create: `teraterm/teraterm/search_state.cpp`
- Create: `teraterm/teraterm/search_state_test.cpp`
- Modify: `teraterm/teraterm/CMakeLists.txt`
- Modify: `teraterm/teraterm/buffer.h`
- Modify: `teraterm/teraterm/buffer.c`
- Modify: `teraterm/teraterm/vtwin.h`
- Modify: `teraterm/teraterm/vtwin.cpp`
- Modify: `teraterm/teraterm/vtdraw.cpp`

**Interfaces:**

```cpp
struct SearchMatch { long line; int start; int length; };
class SearchState {
public:
    void SetQuery(std::wstring query);
    void SetMatches(std::vector<SearchMatch> matches);
    const SearchMatch *Next();
    const SearchMatch *Previous();
    const SearchMatch *Active() const;
};
```

- [ ] **Step 1: Write pure next/previous/wrap tests**

Test empty results, one result, multiple results, next wrap, previous wrap, and query reset.

- [ ] **Step 2: Add a read-only buffer enumeration helper**

The helper exposes text for search without modifying buffer contents, cursor, selection, or logging.

- [ ] **Step 3: Add modeless Ctrl+F search strip owned by `CVTWindow`**

Escape closes and restores terminal focus. Enter advances; Shift+Enter goes backward.

- [ ] **Step 4: Highlight visible matches in `vtdraw.cpp`**

Use existing selection/drawing primitives where practical; active match gets a distinct emphasis while respecting terminal foreground/background readability.

- [ ] **Step 5: Run search-state tests and x64 build**

- [ ] **Step 6: Commit**

```bash
git add -- teraterm/teraterm/search_state.h teraterm/teraterm/search_state.cpp teraterm/teraterm/search_state_test.cpp teraterm/teraterm/CMakeLists.txt teraterm/teraterm/buffer.h teraterm/teraterm/buffer.c teraterm/teraterm/vtwin.h teraterm/teraterm/vtwin.cpp teraterm/teraterm/vtdraw.cpp
git commit -m "feat: add Boooyah scrollback search"
```

---

### Task 9: Add paste safety without breaking bracketed paste

**Files:**
- Create: `teraterm/teraterm/paste_policy.h`
- Create: `teraterm/teraterm/paste_policy.cpp`
- Create: `teraterm/teraterm/paste_policy_test.cpp`
- Modify: `teraterm/teraterm/CMakeLists.txt`
- Modify: `teraterm/teraterm/clipboar.c`
- Modify: `teraterm/teraterm/addsetting.cpp`
- Modify: `teraterm/teraterm/ttermpro.rc`
- Modify: `teraterm/ttpset/ttset.c`

**Interfaces:**

```cpp
enum class PasteRisk { SafeSingleLine, Multiline, ControlCharacters };
struct PasteAssessment { PasteRisk risk; size_t line_count; };
PasteAssessment AssessPaste(const wchar_t *text);
```

- [ ] **Step 1: Write pure classification tests**

Examples:

```cpp
assert(AssessPaste(L"show version").risk == PasteRisk::SafeSingleLine);
assert(AssessPaste(L"one\ntwo").risk == PasteRisk::Multiline);
assert(AssessPaste(L"abc\x03def").risk == PasteRisk::ControlCharacters);
```

- [ ] **Step 2: Integrate assessment before current `CheckClipboardContentW` confirmation logic**

Single-line ordinary text stays immediate. Multiline/control-character content can trigger the existing editable confirmation dialog with clearer Boooyah risk text and line count.

- [ ] **Step 3: Preserve current bracketed-paste insertion exactly after confirmation**

Do not strip or reorder `BracketStartW` / `BracketEndW` behavior.

- [ ] **Step 4: Add user preference for multiline warning and control-character warning**

Default both on; expert users can disable them under Copy/Paste settings.

- [ ] **Step 5: Run paste tests and x64 build**

- [ ] **Step 6: Commit**

```bash
git add -- teraterm/teraterm/paste_policy.h teraterm/teraterm/paste_policy.cpp teraterm/teraterm/paste_policy_test.cpp teraterm/teraterm/CMakeLists.txt teraterm/teraterm/clipboar.c teraterm/teraterm/addsetting.cpp teraterm/teraterm/ttermpro.rc teraterm/ttpset/ttset.c
git commit -m "feat: add Boooyah paste safety"
```

---

### Task 10: Unified settings entry and keyboard-first commands

**Files:**
- Modify: `teraterm/teraterm/addsetting.h`
- Modify: `teraterm/teraterm/addsetting.cpp`
- Modify: `teraterm/common/tt_res.h`
- Modify: `teraterm/teraterm/ttermpro.rc`
- Modify: `teraterm/teraterm/vtwin.h`
- Modify: `teraterm/teraterm/vtwin.cpp`

**Interfaces:**
- Keep `CAddSettingPropSheetDlg` as the settings backend.
- Add stable page aliases for Connection, Terminal, Appearance, Keyboard, Logging, Transfers, Serial, SSH, Encoding, Advanced where existing pages map cleanly.
- Add commands `ID_BOOOYAH_SETTINGS`, `ID_BOOOYAH_RECONNECT`, `ID_BOOOYAH_SEARCH`, `ID_BOOOYAH_TOGGLE_LOG`, `ID_BOOOYAH_COMMAND_LAUNCHER`.

- [ ] **Step 1: Route all old Setup menu items into the unified property sheet on the correct page**

Do not remove old menu entries; make them shortcuts into one settings system.

- [ ] **Step 2: Add Settings (`Ctrl+,`) and Reconnect (`Ctrl+R`) accelerator handling**

Accelerators must be application commands only when Boooyah owns focus; terminal data paths must not receive the shortcut characters.

- [ ] **Step 3: Add `Ctrl+N`, `Ctrl+F`, and `Ctrl+Shift+L` accelerator mappings**

Map to Quick Connect, Search, and Toggle Logging respectively.

- [ ] **Step 4: Build x64 and keyboard-test every accelerator from connected and disconnected states**

- [ ] **Step 5: Commit**

```bash
git add -- teraterm/teraterm/addsetting.h teraterm/teraterm/addsetting.cpp teraterm/common/tt_res.h teraterm/teraterm/ttermpro.rc teraterm/teraterm/vtwin.h teraterm/teraterm/vtwin.cpp
git commit -m "feat: unify Boooyah settings and shortcuts"
```

---

### Task 11: Add the Ctrl+K command launcher

**Files:**
- Create: `teraterm/teraterm/command_launcher.h`
- Create: `teraterm/teraterm/command_launcher.cpp`
- Modify: `teraterm/teraterm/CMakeLists.txt`
- Modify: `teraterm/common/tt_res.h`
- Modify: `teraterm/teraterm/ttermpro.rc`
- Modify: `teraterm/teraterm/vtwin.h`
- Modify: `teraterm/teraterm/vtwin.cpp`
- Modify: `teraterm/teraterm/teraterm.cpp`

**Interfaces:**

```cpp
struct BoooyahCommand {
    UINT command_id;
    const wchar_t *name;
    const wchar_t *keywords;
};

class CommandLauncher {
public:
    bool Create(HWND parent);
    void Show();
    void Hide();
    bool IsVisible() const;
};
```

- [ ] **Step 1: Implement a modeless edit + filtered list using existing command IDs**

Initial commands: Connect to profile, Reconnect, Disconnect, Start/Stop Logging, Send File, Settings, Change Serial Port, Duplicate Session, Run Macro.

- [ ] **Step 2: Register the launcher with `AddModelessHandle`/`RemoveModelessHandle`**

This preserves tab/escape/dialog keyboard handling through the existing modeless loop.

- [ ] **Step 3: Map Ctrl+K to launcher show/hide**

Enter posts the selected existing command ID to `CVTWindow`; the launcher does not call terminal internals directly.

- [ ] **Step 4: Build x64 and verify launcher never sends typed filter text to the remote host**

- [ ] **Step 5: Commit**

```bash
git add -- teraterm/teraterm/command_launcher.h teraterm/teraterm/command_launcher.cpp teraterm/teraterm/CMakeLists.txt teraterm/common/tt_res.h teraterm/teraterm/ttermpro.rc teraterm/teraterm/vtwin.h teraterm/teraterm/vtwin.cpp teraterm/teraterm/teraterm.cpp
git commit -m "feat: add Boooyah command launcher"
```

---

### Task 12: Visual/DPI/accessibility cleanup and final regression build

**Files:**
- Modify: `teraterm/teraterm/ttermpro.rc`
- Modify: `teraterm/ttpdlg/ttpdlg.rc`
- Modify: `teraterm/teraterm/vtwin.cpp`
- Modify: `teraterm/teraterm/session_bar.cpp`
- Modify: `teraterm/teraterm/boooyah_home.cpp`
- Modify: `teraterm/teraterm/addsetting.cpp`
- Modify: `teraterm/ttpdlg/hostdlg.c`
- Modify: `.github/workflows/msbuild.yml` only if an x64-specific verification/artifact naming improvement is needed without changing upstream build semantics.

**Interfaces:**
- No new subsystem. This task applies the established Boooyah controls and existing per-monitor DPI handling consistently.

- [ ] **Step 1: Normalize control spacing, button widths, fonts, focus rectangles, and tab order on Boooyah-owned surfaces**

Use native controls. Default app shell uses dark/charcoal treatment only where Windows theming APIs make it stable; terminal color theme remains independent.

- [ ] **Step 2: Verify every Boooyah modeless surface reflows on `OnDpiChanged`**

Search strip, home, session bar, and command launcher must remain usable at 100%, 125%, 150%, and 200% scaling.

- [ ] **Step 3: Run policy/unit tests**

Compile/run session, profile, paste, and search tests with `/W4 /WX`.

- [ ] **Step 4: Run full Windows VS2022 pipeline and require x64 packaging success**

Required successful x64 steps: common build, architecture build, portable ZIP upload, installer upload, checksum upload.

- [ ] **Step 5: Verify the exact artifact SHA belongs to the final branch head**

Compare workflow `head_sha` to PR `head_sha`; download x64 portable and installer artifacts; verify ZIP extraction and presence of `ttermpro.exe` + `ttxssh.dll`.

- [ ] **Step 6: Behavioral checklist**

Verify:

- failed SSH auth leaves Boooyah open with scrollback intact;
- cancelled SSH auth leaves a usable Boooyah window;
- remote disconnect leaves Boooyah open;
- intentional Disconnect is quiet;
- Reconnect and Change Server reuse the same window;
- serial unplug/replug preserves window/scrollback;
- profiles serialize no password field;
- logging retains directory and sensible filename;
- file send remembers intended folder/options;
- Ctrl+F / Ctrl+R / Ctrl+N / Ctrl+, / Ctrl+K do not leak into terminal input;
- portable ZIP and installer are from the exact tested commit.

- [ ] **Step 7: Commit final polish**

```bash
git add -- teraterm/teraterm/ttermpro.rc teraterm/ttpdlg/ttpdlg.rc teraterm/teraterm/vtwin.cpp teraterm/teraterm/session_bar.cpp teraterm/teraterm/boooyah_home.cpp teraterm/teraterm/addsetting.cpp teraterm/ttpdlg/hostdlg.c
git commit -m "feat: finish Boooyah workflow overhaul"
```

---

## Plan self-review

- Spec coverage: branding, disconnected home, session recovery, Quick Connect, profiles/favorites/recents, serial reconnect, logging, file-send memory, scrollback search, paste safety, unified settings, keyboard shortcuts, command launcher, visual/DPI/accessibility cleanup, compatibility boundaries, and artifact verification are all mapped to explicit tasks.
- Placeholder scan: no TBD/TODO/“implement later” steps are present.
- Type consistency: `SessionState`/`DisconnectOrigin` stay in the existing state module; `SessionBarModel`, `QuickConnectRequest`, `BoooyahProfile`, `SearchState`, `PasteAssessment`, and `BoooyahCommand` each have one owning module and are consumed by named later tasks.
- Scope control: no Electron/WinUI rewrite, AI assistant, SFTP file manager, Docker/Kubernetes dashboard, or multi-pane IDE work is included.
