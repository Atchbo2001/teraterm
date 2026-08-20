from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]


def read_text(path: pathlib.Path) -> str:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return f.read()


def write_text(path: pathlib.Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        f.write(text)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def patch_ids() -> None:
    path = ROOT / "teraterm" / "common" / "tt_res.h"
    text = read_text(path)
    nl = "\r\n" if "\r\n" in text else "\n"
    anchor = f'#define ID_FILE_CYGWINCONNECTION        50112{nl}'
    addition = anchor + nl.join([
        '#define ID_FILE_RECONNECT               50113',
        '#define ID_FILE_CHANGESERVER            50114',
        '#define ID_FILE_PROFILES                50115',
        '',
    ])
    text = replace_once(text, anchor, addition, "session bar command ids")
    write_text(path, text)


def patch_cmake() -> None:
    path = ROOT / "teraterm" / "teraterm" / "CMakeLists.txt"
    text = read_text(path)
    nl = "\r\n" if "\r\n" in text else "\n"
    anchor = f'  vtwin.cpp{nl}'
    addition = nl.join([
        '  session_bar.cpp',
        '  session_bar.h',
        '  session_bar_model.h',
        '  vtwin.cpp',
        '',
    ])
    text = replace_once(text, anchor, addition, "session bar CMake files")
    write_text(path, text)


def patch_vtwin_header() -> None:
    path = ROOT / "teraterm" / "teraterm" / "vtwin.h"
    text = read_text(path)
    nl = "\r\n" if "\r\n" in text else "\n"

    cpp_guard = f'#ifdef __cplusplus{nl}'
    cpp_includes = f'#include "session_state.h"{nl}#include "session_bar.h"{nl}'
    if cpp_includes in text and text.find(cpp_includes) < text.find(cpp_guard):
        text = text.replace(cpp_includes, "", 1)
        text = text.replace(cpp_guard, cpp_guard + cpp_includes, 1)
    elif cpp_includes not in text:
        state_include = f'#include "session_state.h"{nl}'
        if state_include in text and text.find(state_include) < text.find(cpp_guard):
            text = text.replace(state_include, "", 1)
        text = text.replace(cpp_guard, cpp_guard + cpp_includes, 1)

    field_anchor = f'\tDisconnectOrigin pending_disconnect_origin_ = DisconnectOrigin::None;{nl}'
    field_new = field_anchor + nl.join([
        '\tDisconnectOrigin last_disconnect_origin_ = DisconnectOrigin::None;',
        '\tSessionBar session_bar_;',
        '',
    ])
    text = replace_once(text, field_anchor, field_new, "session bar fields")

    method_anchor = f'\tvoid Disconnect(BOOL confirm, DisconnectOrigin origin = DisconnectOrigin::UserRequested);{nl}'
    method_new = method_anchor + nl.join([
        '\tvoid UpdateSessionBar();',
        '\tvoid OnFileReconnect();',
        '\tvoid OnFileChangeServer();',
        '\tvoid OnFileProfiles();',
        '',
    ])
    text = replace_once(text, method_anchor, method_new, "session bar methods")
    write_text(path, text)


def patch_vtwin() -> None:
    path = ROOT / "teraterm" / "teraterm" / "vtwin.cpp"
    text = read_text(path)
    nl = "\r\n" if "\r\n" in text else "\n"

    create_anchor = nl.join([
        '\tHVTWin = GetSafeHwnd();',
        '\tif (HVTWin == NULL) return;',
        '\tcv.HWin = HVTWin;',
        '',
    ])
    create_new = nl.join([
        '\tHVTWin = GetSafeHwnd();',
        '\tif (HVTWin == NULL) return;',
        '\tcv.HWin = HVTWin;',
        '\tsession_bar_.Create(HVTWin);',
        '\tUpdateSessionBar();',
        '',
    ])
    text = replace_once(text, create_anchor, create_new, "session bar creation")

    transition_anchor = nl.join([
        '\t\t\tconst SessionTransition transition = HandleDisconnect(session_state_, origin);',
        '\t\t\tsession_state_ = transition.next;',
        '\t\t\tChangeTitle();',
    ])
    transition_new = nl.join([
        '\t\t\tconst SessionTransition transition = HandleDisconnect(session_state_, origin);',
        '\t\t\tsession_state_ = transition.next;',
        '\t\t\tlast_disconnect_origin_ = origin;',
        '\t\t\tChangeTitle();',
        '\t\t\tUpdateSessionBar();',
    ])
    text = replace_once(text, transition_anchor, transition_new, "disconnect bar update")

    open_anchor = nl.join([
        '\telse {',
        '\t\tConnecting = FALSE;',
        '\t\tsession_state_ = SessionState::Connected;',
        '\t}',
        '',
        '\tChangeTitle();',
    ])
    open_new = nl.join([
        '\telse {',
        '\t\tConnecting = FALSE;',
        '\t\tsession_state_ = SessionState::Connected;',
        '\t}',
        '\tlast_disconnect_origin_ = DisconnectOrigin::None;',
        '',
        '\tChangeTitle();',
        '\tUpdateSessionBar();',
    ])
    text = replace_once(text, open_anchor, open_new, "connect bar update")

    size_anchor = nl.join([
        '\tif (nType == SIZE_MAXIMIZED) {',
        '\t\tts.TerminalOldWidth = ts.TerminalWidth;',
        '\t\tts.TerminalOldHeight = ts.TerminalHeight;',
        '\t}',
        '',
        '\t::GetWindowRect(HVTWin,&R);',
    ])
    size_new = nl.join([
        '\tif (nType == SIZE_MAXIMIZED) {',
        '\t\tts.TerminalOldWidth = ts.TerminalWidth;',
        '\t\tts.TerminalOldHeight = ts.TerminalHeight;',
        '\t}',
        '',
        '\tconst UINT boooyah_dpi = GetMonitorDpiFromWindow(HVTWin);',
        '\tsession_bar_.Layout(cx, cy, boooyah_dpi);',
        '\tif (session_bar_.IsVisible()) {',
        '\t\tconst int bar_height = session_bar_.HeightForDpi(boooyah_dpi);',
        '\t\tif (cy > bar_height) {',
        '\t\t\tcy -= bar_height;',
        '\t\t}',
        '\t}',
        '',
        '\t::GetWindowRect(HVTWin,&R);',
    ])
    text = replace_once(text, size_anchor, size_new, "session bar layout")

    command_anchor = nl.join([
        '\t\tcase ID_FILE_NEWCONNECTION: OnFileNewConnection(); break;',
        '\t\tcase ID_FILE_DUPLICATESESSION: OnDuplicateSession(); break;',
    ])
    command_new = nl.join([
        '\t\tcase ID_FILE_NEWCONNECTION: OnFileNewConnection(); break;',
        '\t\tcase ID_FILE_RECONNECT: OnFileReconnect(); break;',
        '\t\tcase ID_FILE_CHANGESERVER: OnFileChangeServer(); break;',
        '\t\tcase ID_FILE_PROFILES: OnFileProfiles(); break;',
        '\t\tcase ID_FILE_DUPLICATESESSION: OnDuplicateSession(); break;',
    ])
    text = replace_once(text, command_anchor, command_new, "session bar commands")

    disconnect_anchor = f'void CVTWindow::Disconnect(BOOL confirm, DisconnectOrigin origin){nl}'
    methods = nl.join([
        'void CVTWindow::UpdateSessionBar()',
        '{',
        '\tSessionBarModel model;',
        '\tmodel.state = session_state_;',
        '\tmodel.origin = last_disconnect_origin_;',
        '\tmodel.logging = FLogIsOpend() != 0;',
        '\tsession_bar_.Update(model);',
        '\tRECT client;',
        '\tif (::GetClientRect(HVTWin, &client)) {',
        '\t\tsession_bar_.Layout(client.right - client.left, client.bottom - client.top, GetMonitorDpiFromWindow(HVTWin));',
        '\t}',
        '}',
        '',
        'void CVTWindow::OnFileReconnect()',
        '{',
        '\tif (Connecting || cv.Ready) {',
        '\t\treturn;',
        '\t}',
        '\tpending_disconnect_origin_ = DisconnectOrigin::None;',
        '\tlast_disconnect_origin_ = DisconnectOrigin::None;',
        '\tsession_state_ = SessionState::Connecting;',
        '\tConnecting = TRUE;',
        '\tChangeTitle();',
        '\tUpdateSessionBar();',
        '\tCommOpen(HVTWin, &ts, &cv);',
        '}',
        '',
        'void CVTWindow::OnFileChangeServer()',
        '{',
        '\tOnFileNewConnection();',
        '}',
        '',
        'void CVTWindow::OnFileProfiles()',
        '{',
        '\tOnFileNewConnection();',
        '}',
        '',
        disconnect_anchor.rstrip('\r\n'),
    ]) + nl
    text = replace_once(text, disconnect_anchor, methods, "session bar handlers")

    write_text(path, text)


def verify() -> None:
    vtwin = read_text(ROOT / "teraterm" / "teraterm" / "vtwin.cpp")
    vtwin_h = read_text(ROOT / "teraterm" / "teraterm" / "vtwin.h")
    ids = read_text(ROOT / "teraterm" / "common" / "tt_res.h")
    cmake = read_text(ROOT / "teraterm" / "teraterm" / "CMakeLists.txt")
    cpp_guard = vtwin_h.find("#ifdef __cplusplus")
    checks = [
        ("ID_FILE_RECONNECT               50113" in ids, "reconnect command id missing"),
        ("SessionBar session_bar_" in vtwin_h, "session bar member missing"),
        (vtwin_h.find('#include "session_state.h"') > cpp_guard >= 0, "session state include leaks into C translation units"),
        (vtwin_h.find('#include "session_bar.h"') > cpp_guard >= 0, "session bar include leaks into C translation units"),
        ("session_bar_.Create(HVTWin)" in vtwin, "session bar not created"),
        ("UpdateSessionBar();" in vtwin, "session bar update missing"),
        ("void CVTWindow::OnFileReconnect()" in vtwin, "reconnect handler missing"),
        ("case ID_FILE_RECONNECT: OnFileReconnect()" in vtwin, "reconnect command not routed"),
        ("session_bar.cpp" in cmake, "session bar source not registered"),
    ]
    failures = [message for ok, message in checks if not ok]
    if failures:
        raise RuntimeError("; ".join(failures))


def main() -> int:
    patch_ids()
    patch_cmake()
    patch_vtwin_header()
    patch_vtwin()
    verify()
    print("Boooyah session bar integration applied and verified")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise
