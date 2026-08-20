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


def replace_if_present(text: str, old: str, new: str) -> str:
    if old in text:
        return text.replace(old, new, 1)
    return text


def patch_vtwin_header() -> None:
    path = ROOT / "teraterm" / "teraterm" / "vtwin.h"
    text = read_text(path)
    nl = "\r\n" if "\r\n" in text else "\n"

    include = f'#include "session_state.h"{nl}'
    if include not in text:
        anchor = f'#include "addsetting.h"{nl}'
        if anchor not in text:
            raise RuntimeError("vtwin.h include anchor missing")
        text = text.replace(anchor, anchor + include, 1)

    fields = nl.join([
        "\tSessionState session_state_ = SessionState::Idle;",
        "\tDisconnectOrigin pending_disconnect_origin_ = DisconnectOrigin::None;",
    ])
    if fields not in text:
        anchor = f'\tBOOL isClosing;\t\t// TRUE=ウィンドウクローズ中(WM_DESTROYを受信した){nl}'
        if anchor not in text:
            raise RuntimeError("vtwin.h state anchor missing")
        text = text.replace(anchor, anchor + fields + nl, 1)

    text = replace_if_present(
        text,
        f'\tvoid Disconnect(BOOL confirm);{nl}',
        f'\tvoid Disconnect(BOOL confirm, DisconnectOrigin origin = DisconnectOrigin::UserRequested);{nl}',
    )
    write_text(path, text)


def patch_vtwin() -> None:
    path = ROOT / "teraterm" / "teraterm" / "vtwin.cpp"
    text = read_text(path)
    nl = "\r\n" if "\r\n" in text else "\n"

    include = f'#include "session_state.h"{nl}'
    while include + include in text:
        text = text.replace(include + include, include, 1)
    if include not in text:
        anchor = f'#include "ttdup.h"{nl}'
        if anchor not in text:
            raise RuntimeError("vtwin.cpp include anchor missing")
        text = text.replace(anchor, anchor + include, 1)

    text = text.replace(
        "vtwin_->Disconnect(TRUE);",
        "vtwin_->Disconnect(TRUE, DisconnectOrigin::RemoteOrNetwork);",
    )
    text = replace_if_present(
        text,
        f'void CVTWindow::Disconnect(BOOL confirm){nl}',
        f'void CVTWindow::Disconnect(BOOL confirm, DisconnectOrigin origin){nl}',
    )

    required = [
        "ConsumeDisconnectOrigin(",
        "session_state_ = transition.next;",
        "pending_disconnect_origin_ = origin;",
        "session_state_ = SessionState::Disconnecting;",
        "session_state_ = SessionState::Connected;",
        "Disconnect(TRUE, DisconnectOrigin::RemoteOrNetwork)",
        "PortType != IdTCPIP && ts.ClearScreenOnCloseConnection",
    ]
    missing = [item for item in required if item not in text]
    if missing:
        raise RuntimeError("vtwin.cpp lifecycle integration missing: " + ", ".join(missing))

    write_text(path, text)


def verify() -> None:
    vtwin = read_text(ROOT / "teraterm" / "teraterm" / "vtwin.cpp")
    vtwin_h = read_text(ROOT / "teraterm" / "teraterm" / "vtwin.h")
    ttset = read_text(ROOT / "teraterm" / "ttpset" / "ttset.c")

    checks = [
        (vtwin.count('#include "session_state.h"') == 1, "session_state include must appear exactly once"),
        ("ConsumeDisconnectOrigin(" in vtwin, "disconnect origin is not consumed"),
        ("session_state_ = transition.next" in vtwin, "session transition is not stored"),
        ("Disconnect(BOOL confirm, DisconnectOrigin origin)" in vtwin, "disconnect origin is not accepted"),
        ("Disconnect(TRUE, DisconnectOrigin::RemoteOrNetwork)" in vtwin, "serial transport loss is not distinguished"),
        ("SessionState session_state_ = SessionState::Idle" in vtwin_h, "per-window session state missing"),
        ("DisconnectOrigin pending_disconnect_origin_ = DisconnectOrigin::None" in vtwin_h, "pending origin missing"),
        ("PortType != IdTCPIP && ts.ClearScreenOnCloseConnection" in vtwin, "TCP scrollback can still be cleared"),
        ('GetOnOff(Section, "AutoWinClose", FName, FALSE)' in ttset, "AutoWinClose still defaults off"),
    ]
    failures = [message for ok, message in checks if not ok]
    if failures:
        raise RuntimeError("; ".join(failures))


def main() -> int:
    patch_vtwin_header()
    patch_vtwin()
    verify()
    print("Boooyah session lifecycle source is idempotent and verified")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise
