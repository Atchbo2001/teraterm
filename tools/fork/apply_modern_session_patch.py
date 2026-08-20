from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]


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
    text = path.read_text(encoding="utf-8-sig", newline="")

    include_anchor = '#include "ttdup.h"\r\n'
    include_new = '#include "ttdup.h"\r\n#include "session_state.h"\r\n'
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

    replacement = (
        "\t\t\t// A transport ending must never destroy the terminal window.\r\n"
        "\t\t\t// Preserve scrollback and move into a recoverable disconnected state.\r\n"
        "\t\t\tif (PortType == IdTCPIP) {\r\n"
        "\t\t\t\tconst SessionTransition transition = HandleDisconnect(\r\n"
        "\t\t\t\t\tConnecting ? SessionState::Connecting : SessionState::Connected,\r\n"
        "\t\t\t\t\tDisconnectOrigin::RemoteOrNetwork);\r\n"
        "\t\t\t\t(void)transition;\r\n"
        "\t\t\t}\r\n"
        "\t\t\tChangeTitle();\r\n"
        "\t\t\tif (ts.ClearScreenOnCloseConnection) {\r\n"
        "\t\t\t\tOnEditClearScreen();\r\n"
        "\t\t\t}"
    )

    if "A transport ending must never destroy the terminal window." not in text:
        text, count = pattern.subn(replacement, text, count=1)
        if count != 1:
            raise RuntimeError(f"disconnect close block: expected one match, found {count}")

    path.write_text(text, encoding="utf-8", newline="")


def patch_defaults() -> None:
    path = ROOT / "teraterm" / "ttpset" / "ttset.c"
    text = path.read_text(encoding="utf-8-sig", newline="")
    old = 'ts->AutoWinClose = GetOnOff(Section, "AutoWinClose", FName, TRUE);'
    new = 'ts->AutoWinClose = GetOnOff(Section, "AutoWinClose", FName, FALSE);'
    text = replace_once(text, old, new, "AutoWinClose default")
    path.write_text(text, encoding="utf-8", newline="")


def verify() -> None:
    vtwin = (ROOT / "teraterm" / "teraterm" / "vtwin.cpp").read_text(encoding="utf-8")
    ttset = (ROOT / "teraterm" / "ttpset" / "ttset.c").read_text(encoding="utf-8")

    checks = [
        ('#include "session_state.h"' in vtwin, "session state header not included"),
        ("A transport ending must never destroy the terminal window." in vtwin, "disconnect path not patched"),
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
