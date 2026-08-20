from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT_DIR = ROOT / "teraterm" / "teraterm"


def patch_project(path: Path) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        text = f.read()

    nl = "\r\n" if "\r\n" in text else "\n"
    compile_entry = '    <ClCompile Include="session_bar.cpp" />'
    anchor = '    <ClCompile Include="vtwin.cpp" />'

    if compile_entry not in text:
        if text.count(anchor) != 1:
            raise RuntimeError(f"{path.name}: expected one vtwin.cpp compile entry, found {text.count(anchor)}")
        text = text.replace(anchor, compile_entry + nl + anchor, 1)

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        f.write(text)

    if text.count(compile_entry) != 1:
        raise RuntimeError(f"{path.name}: session_bar.cpp compile entry is missing or duplicated")


def main() -> int:
    for version in ("v16", "v17", "v18"):
        patch_project(PROJECT_DIR / f"ttermpro.{version}.vcxproj")

    print("Boooyah session_bar.cpp added to all supported Visual Studio projects")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
