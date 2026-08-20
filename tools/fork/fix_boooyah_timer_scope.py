from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VTWIN = ROOT / "teraterm" / "teraterm" / "vtwin.cpp"

# Keep C++ locals in IdComEndTimer inside an explicit switch-arm scope.


def main() -> int:
    with VTWIN.open("r", encoding="utf-8-sig", newline="") as f:
        text = f.read()
    nl = "\r\n" if "\r\n" in text else "\n"

    if "case IdComEndTimer: {" not in text:
        old = f"\t\tcase IdComEndTimer:{nl}"
        if text.count(old) != 1:
            raise RuntimeError(f"expected one IdComEndTimer case, found {text.count(old)}")
        text = text.replace(old, f"\t\tcase IdComEndTimer: {{{nl}", 1)

    close_old = nl.join([
        "\t\t\tif (PortType != IdTCPIP && ts.ClearScreenOnCloseConnection) {",
        "\t\t\t\tOnEditClearScreen();",
        "\t\t\t}",
        "\t\t\tbreak;",
        "\t\tcase IdPrnStartTimer:",
    ])
    close_new = nl.join([
        "\t\t\tif (PortType != IdTCPIP && ts.ClearScreenOnCloseConnection) {",
        "\t\t\t\tOnEditClearScreen();",
        "\t\t\t}",
        "\t\t\tbreak;",
        "\t\t}",
        "\t\tcase IdPrnStartTimer:",
    ])
    if close_new not in text:
        if text.count(close_old) != 1:
            raise RuntimeError(f"expected one IdComEndTimer closing anchor, found {text.count(close_old)}")
        text = text.replace(close_old, close_new, 1)

    with VTWIN.open("w", encoding="utf-8", newline="") as f:
        f.write(text)

    if "case IdComEndTimer: {" not in text or close_new not in text:
        raise RuntimeError("IdComEndTimer switch scope was not applied")

    print("Boooyah IdComEndTimer switch scope fixed and verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
