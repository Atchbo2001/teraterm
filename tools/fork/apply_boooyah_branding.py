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


def ensure_include(text: str, anchor: str, include: str) -> str:
    if include in text:
        return text
    if anchor not in text:
        raise RuntimeError(f"include anchor missing: {anchor.strip()}")
    return text.replace(anchor, anchor + include, 1)


def patch_vtwin() -> None:
    path = ROOT / "teraterm" / "teraterm" / "vtwin.cpp"
    text = read_text(path)
    nl = "\r\n" if "\r\n" in text else "\n"
    text = ensure_include(
        text,
        f'#include "session_state.h"{nl}',
        f'#include "boooyah_branding.h"{nl}',
    )
    text = text.replace(
        'CreateW(hInstance, VTClassName, L"Tera Term", Style, rect, NULL, NULL);',
        'CreateW(hInstance, VTClassName, BOOOYAH_PRODUCT_NAME_W, Style, rect, NULL, NULL);',
        1,
    )
    write_text(path, text)


def patch_host_dialog() -> None:
    path = ROOT / "teraterm" / "ttpdlg" / "hostdlg.c"
    text = read_text(path)
    nl = "\r\n" if "\r\n" in text else "\n"
    text = ensure_include(
        text,
        f'#include "ttdlg.h"{nl}',
        f'#include "boooyah_branding.h"{nl}',
    )
    anchor = f'\t\t\tSetDlgTextsW(Dialog, TextInfos, _countof(TextInfos), ts.UILanguageFileW);{nl}'
    branded = anchor + f'\t\t\tSetWindowTextW(Dialog, L"Boooyah: Quick Connect");{nl}'
    if 'SetWindowTextW(Dialog, L"Boooyah: Quick Connect")' not in text:
        if anchor not in text:
            raise RuntimeError("host dialog localization anchor missing")
        text = text.replace(anchor, branded, 1)
    write_text(path, text)


def patch_about_dialog() -> None:
    path = ROOT / "teraterm" / "ttpdlg" / "aboutdlg.c"
    text = read_text(path)
    nl = "\r\n" if "\r\n" in text else "\n"
    text = ensure_include(
        text,
        f'#include "ttdlg.h"{nl}',
        f'#include "boooyah_branding.h"{nl}',
    )
    anchor = f'\t\t\tSetDlgTextsW(Dialog, TextInfos, _countof(TextInfos), ts.UILanguageFileW);{nl}'
    branded = anchor + nl.join([
        '\t\t\tSetWindowTextW(Dialog, L"About Boooyah");',
        '\t\t\tSetDlgItemTextW(Dialog, IDC_TT_PRO, BOOOYAH_PRODUCT_NAME_W);',
        '',
    ])
    if 'SetWindowTextW(Dialog, L"About Boooyah")' not in text:
        if anchor not in text:
            raise RuntimeError("about dialog localization anchor missing")
        text = text.replace(anchor, branded, 1)
    write_text(path, text)


def patch_resources() -> None:
    for rel in [
        ("teraterm", "ttpdlg", "ttpdlg.rc"),
        ("teraterm", "teraterm", "ttermpro.rc"),
        ("teraterm", "teraterm", "filesys_log.rc"),
    ]:
        path = ROOT.joinpath(*rel)
        text = read_text(path)
        text = text.replace('CAPTION "Tera Term:', 'CAPTION "Boooyah:')
        text = text.replace('CAPTION "About Tera Term"', 'CAPTION "About Boooyah"')
        text = text.replace('CONTROL         "Tera Term",IDC_TT_PRO', 'CONTROL         "Boooyah",IDC_TT_PRO')
        write_text(path, text)


def patch_cmake() -> None:
    path = ROOT / "teraterm" / "teraterm" / "CMakeLists.txt"
    text = read_text(path)
    nl = "\r\n" if "\r\n" in text else "\n"
    entry = f'  boooyah_branding.h{nl}'
    if entry not in text:
        anchor = f'  broadcast.h{nl}'
        if anchor not in text:
            raise RuntimeError("CMake source anchor missing")
        text = text.replace(anchor, anchor + entry, 1)
    write_text(path, text)


def verify() -> None:
    vtwin = read_text(ROOT / "teraterm" / "teraterm" / "vtwin.cpp")
    host = read_text(ROOT / "teraterm" / "ttpdlg" / "hostdlg.c")
    about = read_text(ROOT / "teraterm" / "ttpdlg" / "aboutdlg.c")
    rc = read_text(ROOT / "teraterm" / "ttpdlg" / "ttpdlg.rc")
    cmake = read_text(ROOT / "teraterm" / "teraterm" / "CMakeLists.txt")
    checks = [
        ('#include "boooyah_branding.h"' in vtwin, "VT window branding include missing"),
        ("BOOOYAH_PRODUCT_NAME_W" in vtwin, "main window still uses hard-coded product name"),
        ('L"Boooyah: Quick Connect"' in host, "Quick Connect title missing"),
        ('L"About Boooyah"' in about, "About title missing"),
        ('CAPTION "Boooyah: New connection"' in rc or 'CAPTION "Boooyah: Quick Connect"' in rc, "resource Quick Connect caption missing"),
        ('CAPTION "About Boooyah"' in rc, "About resource caption missing"),
        ("boooyah_branding.h" in cmake, "branding header not registered"),
    ]
    failures = [message for ok, message in checks if not ok]
    if failures:
        raise RuntimeError("; ".join(failures))


def main() -> int:
    patch_vtwin()
    patch_host_dialog()
    patch_about_dialog()
    patch_resources()
    patch_cmake()
    verify()
    print("Boooyah user-facing branding applied and verified")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise
