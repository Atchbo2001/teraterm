from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]


def read_text_preserve_newlines(path: pathlib.Path) -> str:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return f.read()


def write_text_preserve_newlines(path: pathlib.Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        f.write(text)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count == 0:
        if new in text:
            return text
        raise RuntimeError(f"{label}: expected source text not found")
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def patch_vtwin_header() -> None:
    path = ROOT / "teraterm" / "teraterm" / "vtwin.h"
    text = read_text_preserve_newlines(path)
    nl = "\r\n" if "\r\n" in text else "\n"

    text = replace_once(
        text,
        f'#include "addsetting.h"{nl}',
        f'#include "addsetting.h"{nl}#include "session_state.h"{nl}',
        "vtwin session state include",
    )

    text = replace_once(
        text,
        f'\tBOOL isClosing;\t\t// TRUE=ウィンドウクローズ中(WM_DESTROYを受信した){nl}',
        nl.join([
            "\tBOOL isClosing;\t\t// TRUE=ウィンドウクローズ中(WM_DESTROYを受信した)",
            "\tSessionState session_state_ = SessionState::Idle;",
            "\tDisconnectOrigin pending_disconnect_origin_ = DisconnectOrigin::None;",
            "",
        ]),
        "per-window session fields",
    )

    text = replace_once(
        text,
        f'\tvoid Disconnect(BOOL confirm);{nl}',
        f'\tvoid Disconnect(BOOL confirm, DisconnectOrigin origin = DisconnectOrigin::UserRequested);{nl}',
        "disconnect origin signature",
    )

    write_text_preserve_newlines(path, text)


def patch_vtwin() -> None:
    path = ROOT / "teraterm" / "teraterm" / "vtwin.cpp"
    text = read_text_preserve_newlines(path)
    nl = "\r\n" if "\r\n" in text else "\n"

    include_anchor = f'#include "ttdup.h"{nl}'
    include_new = f'#include "ttdup.h"{nl}#include "session_state.h"{nl}'
    text = replace_once(text, include_anchor, include_new, "session_state include")

    stock_pattern = re.compile(
        r'''\t\t\tif \(\(PortType==IdTCPIP\) &&\r?\n'''
        r'''\t\t\t\t\(ts\.AutoWinClose>0\) &&\r?\n'''
        r'''\t\t\t\t::IsWindowEnabled\(HVTWin\) &&\r?\n'''
        r'''\t\t\t\t\(\(HTEKWin==NULL\) \|\| ::IsWindowEnabled\(HTEKWin\)\) \) \{\r?\n'''
        r'''\t\t\t\tOnClose\(\);\r?\n'''
        r'''\t\t\t\}\r?\n'''
        r'''\t\t\telse \{\r?\n'''
        r'''\t\t\t\tChangeTitle\(\);\r?\n'''
        r'''\t\t\t\tif \(ts\.ClearScreenOnCloseConnection\) \{\r?\n'''
        r'''\t\t\t\t\tOnEditClearScreen\(\);\r?\n'''
        r'''\t\t\t\t\}\r?\n'''
        r'''\t\t\t\}'''
    )

    bootstrap_replacement = nl.join([
        "\t\t\t// A transport ending must never destroy the terminal window.",
        "\t\t\t// Preserve TCP/SSH scrollback and move into a recoverable disconnected state.",
        "\t\t\tif (PortType == IdTCPIP) {",
        "\t\t\t\tconst SessionTransition transition = HandleDisconnect(",
        "\t\t\t\t\tConnecting ? SessionState::Connecting : SessionState::Connected,",
        "\t\t\t\t\tDisconnectOrigin::RemoteOrNetwork);",
        "\t\t\t\t(void)transition;",
        "\t\t\t}",
        "\t\t\tChangeTitle();",
        "\t\t\tif (PortType != IdTCPIP && ts.ClearScreenOnCloseConnection) {",
        "\t\t\t\tOnEditClearScreen();",
        "\t\t\t}",
    ])

    if "A transport ending must never destroy the terminal window." not in text:
        text, count = stock_pattern.subn(lambda _m: bootstrap_replacement, text, count=1)
        if count != 1:
            raise RuntimeError(f"disconnect close block: expected one match, found {count}")

    old_transition = nl.join([
        "\t\t\tif (PortType == IdTCPIP) {",
        "\t\t\t\tconst SessionTransition transition = HandleDisconnect(",
        "\t\t\t\t\tConnecting ? SessionState::Connecting : SessionState::Connected,",
        "\t\t\t\t\tDisconnectOrigin::RemoteOrNetwork);",
        "\t\t\t\t(void)transition;",
        "\t\t\t}",
    ])
    new_transition = nl.join([
        "\t\t\tconst DisconnectOrigin origin = ConsumeDisconnectOrigin(",
        "\t\t\t\t&pending_disconnect_origin_, DisconnectOrigin::RemoteOrNetwork);",
        "\t\t\tconst SessionTransition transition = HandleDisconnect(session_state_, origin);",
        "\t\t\tsession_state_ = transition.next;",
    ])
    text = replace_once(text, old_transition, new_transition, "stored disconnect transition")

    old_open_state = nl.join([
        "\tCommStart(&cv,lParam,&ts);",
        "\tif (ts.PortType == IdTCPIP && cv.RetryWithOtherProtocol == TRUE) {",
        "\t\tConnecting = TRUE;",
        "\t}",
        "\telse {",
        "\t\tConnecting = FALSE;",
        "\t}",
    ])
    new_open_state = nl.join([
        "\tCommStart(&cv,lParam,&ts);",
        "\tif (ts.PortType == IdTCPIP && cv.RetryWithOtherProtocol == TRUE) {",
        "\t\tConnecting = TRUE;",
        "\t\tsession_state_ = SessionState::Connecting;",
        "\t}",
        "\telse {",
        "\t\tConnecting = FALSE;",
        "\t\tsession_state_ = SessionState::Connected;",
        "\t}",
    ])
    text = replace_once(text, old_open_state, new_open_state, "connection state tracking")

    text = replace_once(
        text,
        f'void CVTWindow::Disconnect(BOOL confirm){nl}',
        f'void CVTWindow::Disconnect(BOOL confirm, DisconnectOrigin origin){nl}',
        "disconnect implementation signature",
    )

    post_close = f'\t::PostMessage(HVTWin, WM_USER_COMMNOTIFY, 0, FD_CLOSE);{nl}'
    tracked_close = nl.join([
        "\tpending_disconnect_origin_ = origin;",
        "\tsession_state_ = SessionState::Disconnecting;",
        "\t::PostMessage(HVTWin, WM_USER_COMMNOTIFY, 0, FD_CLOSE);",
        "",
    ])
    text = replace_once(text, post_close, tracked_close, "disconnect origin tracking")

    text = text.replace(
        "vtwin_->Disconnect(TRUE);",
        "vtwin_->Disconnect(TRUE, DisconnectOrigin::RemoteOrNetwork);",
    )

    write_text_preserve_newlines(path, text)


def patch_defaults() -> None:
    path = ROOT / "teraterm" / "ttpset" / "ttset.c"
    text = read_text_preserve_newlines(path)
    old = 'ts->AutoWinClose = GetOnOff(Section, "AutoWinClose", FName, TRUE);'
    new = 'ts->AutoWinClose = GetOnOff(Section, "AutoWinClose", FName, FALSE);'
    text = replace_once(text, old, new, "AutoWinClose default")
    write_text_preserve_newlines(path, text)


def verify() -> None:
    vtwin = read_text_preserve_newlines(ROOT / "teraterm" / "teraterm" / "vtwin.cpp")
    vtwin_h = read_text_preserve_newlines(ROOT / "teraterm" / "teraterm" / "vtwin.h")
    ttset = read_text_preserve_newlines(ROOT / "teraterm" / "ttpset" / "ttset.c")

    checks = [
        ('#include "session_state.h"' in vtwin, "session state header not included"),
        ("A transport ending must never destroy the terminal window." in vtwin, "disconnect path not patched"),
        ("ConsumeDisconnectOrigin(" in vtwin, "disconnect origin is not consumed"),
        ("session_state_ = transition.next" in vtwin, "session transition is not stored"),
        ("Disconnect(BOOL confirm, DisconnectOrigin origin)" in vtwin, "disconnect origin is not accepted"),
        ("Disconnect(TRUE, DisconnectOrigin::RemoteOrNetwork)" in vtwin, "serial transport loss is not distinguished"),
        ("SessionState session_state_ = SessionState::Idle" in vtwin_h, "per-window session state missing"),
        ("DisconnectOrigin pending_disconnect_origin_ = DisconnectOrigin::None" in vtwin_h, "pending origin missing"),
        ("PortType != IdTCPIP && ts.ClearScreenOnCloseConnection" in vtwin, "TCP scrollback can still be cleared"),
        ('GetOnOff(Section, "AutoWinClose", FName, FALSE)' in ttset, "AutoWinClose still defaults on"),
    ]
    failures = [message for ok, message in checks if not ok]
    if failures:
        raise RuntimeError("; ".join(failures))


def main() -> int:
    patch_vtwin_header()
    patch_vtwin()
    patch_defaults()
    verify()
    print("Boooyah session lifecycle patch applied and verified")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise
