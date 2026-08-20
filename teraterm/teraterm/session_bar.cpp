#include "session_bar.h"

#include "../common/tt_res.h"

#include <algorithm>

namespace {

HWND CreateBarControl(HWND parent, const wchar_t *klass, const wchar_t *text, DWORD style, int id)
{
    return CreateWindowExW(
        0,
        klass,
        text,
        WS_CHILD | style,
        0, 0, 0, 0,
        parent,
        reinterpret_cast<HMENU>(static_cast<INT_PTR>(id)),
        GetModuleHandleW(nullptr),
        nullptr);
}

void ShowControl(HWND hwnd, bool show)
{
    if (hwnd != nullptr) {
        ShowWindow(hwnd, show ? SW_SHOWNA : SW_HIDE);
    }
}

} // namespace

SessionBar::~SessionBar()
{
    Destroy();
}

bool SessionBar::Create(HWND parent)
{
    if (parent == nullptr) {
        return false;
    }
    if (parent_ != nullptr) {
        return true;
    }

    parent_ = parent;
    status_ = CreateBarControl(parent, L"STATIC", L"Boooyah", SS_LEFT | SS_CENTERIMAGE, 0);
    reconnect_ = CreateBarControl(parent, L"BUTTON", L"Reconnect", BS_PUSHBUTTON | WS_TABSTOP, ID_FILE_RECONNECT);
    change_server_ = CreateBarControl(parent, L"BUTTON", L"Change Server", BS_PUSHBUTTON | WS_TABSTOP, ID_FILE_CHANGESERVER);
    profiles_ = CreateBarControl(parent, L"BUTTON", L"Profiles", BS_PUSHBUTTON | WS_TABSTOP, ID_FILE_PROFILES);
    disconnect_ = CreateBarControl(parent, L"BUTTON", L"Disconnect", BS_PUSHBUTTON | WS_TABSTOP, ID_FILE_DISCONNECT);
    logging_ = CreateBarControl(parent, L"BUTTON", L"Logging", BS_PUSHBUTTON | WS_TABSTOP, ID_FILE_LOG);

    if (status_ == nullptr || reconnect_ == nullptr || change_server_ == nullptr || profiles_ == nullptr ||
        disconnect_ == nullptr || logging_ == nullptr) {
        Destroy();
        return false;
    }

    Update(SessionBarModel{});
    return true;
}

void SessionBar::Destroy()
{
    HWND controls[] = { status_, reconnect_, change_server_, profiles_, disconnect_, logging_ };
    for (HWND hwnd : controls) {
        if (hwnd != nullptr && IsWindow(hwnd)) {
            DestroyWindow(hwnd);
        }
    }
    status_ = nullptr;
    reconnect_ = nullptr;
    change_server_ = nullptr;
    profiles_ = nullptr;
    disconnect_ = nullptr;
    logging_ = nullptr;
    parent_ = nullptr;
    visible_ = false;
}

int SessionBar::HeightForDpi(UINT dpi) const
{
    return MulDiv(30, static_cast<int>(dpi == 0 ? 96 : dpi), 96);
}

bool SessionBar::IsVisible() const
{
    return visible_;
}

void SessionBar::Update(const SessionBarModel &model)
{
    const SessionBarPresentation presentation = BuildSessionBarPresentation(model.state, model.origin, model.logging);
    visible_ = presentation.visible;

    std::wstring status = L"Boooyah";
    if (!model.target.empty()) {
        status += L"  •  ";
        status += model.target;
    }

    switch (model.state) {
    case SessionState::Connecting:
        status += L"  •  Connecting";
        break;
    case SessionState::Connected:
        status += L"  •  Connected";
        break;
    case SessionState::Disconnecting:
        status += L"  •  Disconnecting";
        break;
    case SessionState::Disconnected:
        status += L"  •  Disconnected";
        break;
    case SessionState::Failed:
        status += L"  •  Connection failed";
        break;
    case SessionState::Idle:
    default:
        break;
    }
    if (model.logging) {
        status += L"  •  REC";
    }

    if (status_ != nullptr) {
        SetWindowTextW(status_, status.c_str());
    }

    ShowControl(status_, presentation.visible);
    ShowControl(reconnect_, presentation.visible && presentation.show_reconnect);
    ShowControl(change_server_, presentation.visible && presentation.show_change_server);
    ShowControl(profiles_, presentation.visible && presentation.show_profiles);
    ShowControl(disconnect_, presentation.visible && presentation.show_disconnect);
    ShowControl(logging_, presentation.visible && presentation.show_logging);
}

void SessionBar::Layout(int client_width, int client_height, UINT dpi)
{
    dpi_ = dpi == 0 ? 96 : dpi;
    if (!visible_ || status_ == nullptr) {
        return;
    }

    const int height = HeightForDpi(dpi_);
    const int y = std::max(0, client_height - height);
    const int pad = MulDiv(6, static_cast<int>(dpi_), 96);
    const int gap = MulDiv(4, static_cast<int>(dpi_), 96);
    const int button_height = std::max(MulDiv(22, static_cast<int>(dpi_), 96), 20);
    const int button_y = y + (height - button_height) / 2;

    struct ButtonLayout { HWND hwnd; int width96; };
    ButtonLayout buttons[] = {
        { logging_, 64 },
        { disconnect_, 72 },
        { profiles_, 60 },
        { change_server_, 92 },
        { reconnect_, 72 },
    };

    int x = client_width - pad;
    for (const ButtonLayout &button : buttons) {
        if (button.hwnd == nullptr || !IsWindowVisible(button.hwnd)) {
            continue;
        }
        const int width = MulDiv(button.width96, static_cast<int>(dpi_), 96);
        x -= width;
        MoveWindow(button.hwnd, x, button_y, width, button_height, TRUE);
        x -= gap;
    }

    const int status_width = std::max(0, x - pad);
    MoveWindow(status_, pad, y, status_width, height, TRUE);
}
