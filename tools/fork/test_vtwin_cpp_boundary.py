from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VTWIN_H = ROOT / "teraterm" / "teraterm" / "vtwin.h"
VTWIN_CPP = ROOT / "teraterm" / "teraterm" / "vtwin.cpp"

# Regression guards for C/C++ compatibility and switch scopes introduced by Boooyah session state.
# IdComEndTimer initializes C++ disconnect state, so its switch arm must remain explicitly braced.

def main() -> int:
    header = VTWIN_H.read_text(encoding="utf-8-sig")
    cpp_guard = header.find("#ifdef __cplusplus")
    if cpp_guard < 0:
        raise AssertionError("vtwin.h is missing its C++ compatibility guard")

    for include in ('#include "session_state.h"', '#include "session_bar.h"'):
        position = header.find(include)
        if position < 0:
            raise AssertionError(f"missing required include: {include}")
        if position < cpp_guard:
            raise AssertionError(
                f"{include} must be inside #ifdef __cplusplus because vtwin.h is included by C translation units"
            )

    source = VTWIN_CPP.read_text(encoding="utf-8-sig")
    if "case IdComEndTimer: {" not in source:
        raise AssertionError(
            "IdComEndTimer must use a braced switch scope before initializing disconnect-origin locals"
        )

    print("vtwin C/C++ and switch-scope boundaries are safe")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
