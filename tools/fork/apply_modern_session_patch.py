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


def patch_vtwin() -> None:
    path = ROOT / "teraterm" / "teraterm" / "vtwin.cpp"
    text = read_text_preserve_newlines(path)
    nl = "\r\n" if "\r\n" in text else "\n"

    include_anchor = f'#include "ttdup.h"{nl}'
    include_new = f'#include "ttdup.h"{nl}#include "session_state.h"{nl}'
    text = replace_once(text, include_anchor, include_new, "session_state include")

    pattern = re.compile(
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

    replacement = nl.join([
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
        text, count = pattern.subn(lambda _m: replacement, text, count=1)
        if count != 1:
            raise RuntimeError(f"disconnect close block: expected one match, found {count}")

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
    ttset = read_text_preserve_newlines(ROOT / "teraterm" / "ttpset" / "ttset.c")

    checks = [
        ('#include "session_state.h"' in vtwin, "session state header not included"),
        ("A transport ending must never destroy the terminal window." in vtwin, "disconnect path not patched"),
        ("PortType != IdTCPIP && ts.ClearScreenOnCloseConnection" in vtwin, "TCP scrollback can still be cleared"),
        ('GetOnOff(Section, "AutoWinClose", FName, FALSE)' in ttset, "AutoWinClose still defaults on"),
    ]
    failures = [message for ok, message in checks if not ok]
    if failures:
        raise RuntimeError("; ".join(failures))


def main() -> int:
    patch_vtwin()
    patch_defaults()
    verify()
    print("modern session bootstrap patch applied and verified")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise
