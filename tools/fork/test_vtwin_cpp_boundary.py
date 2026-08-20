from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VTWIN_H = ROOT / "teraterm" / "teraterm" / "vtwin.h"
VTWIN_CPP = ROOT / "teraterm" / "teraterm" / "vtwin.cpp"
PROJECT_DIR = ROOT / "teraterm" / "teraterm"

# Regression guards for C/C++ compatibility and switch scopes introduced by Boooyah session state.
# IdComEndTimer initializes C++ disconnect state, so its switch arm must remain explicitly braced.
# The native Windows projects must also compile session_bar.cpp or vtwin.cpp links with unresolved SessionBar symbols.

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

    for version in ("v16", "v17", "v18"):
        project = PROJECT_DIR / f"ttermpro.{version}.vcxproj"
        project_text = project.read_text(encoding="utf-8-sig")
        if '<ClCompile Include="session_bar.cpp" />' not in project_text:
            raise AssertionError(f"{project.name} must compile session_bar.cpp")

    print("vtwin C/C++ boundaries, timer scope, and Windows project membership are safe")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
