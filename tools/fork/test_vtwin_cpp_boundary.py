from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VTWIN = ROOT / "teraterm" / "teraterm" / "vtwin.h"


def main() -> int:
    text = VTWIN.read_text(encoding="utf-8-sig")
    cpp_guard = text.find("#ifdef __cplusplus")
    if cpp_guard < 0:
        raise AssertionError("vtwin.h is missing its C++ compatibility guard")

    for include in ('#include "session_state.h"', '#include "session_bar.h"'):
        position = text.find(include)
        if position < 0:
            raise AssertionError(f"missing required include: {include}")
        if position < cpp_guard:
            raise AssertionError(
                f"{include} must be inside #ifdef __cplusplus because vtwin.h is included by C translation units"
            )

    print("vtwin C/C++ boundary is safe")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
