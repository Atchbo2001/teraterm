#pragma once

#include <windows.h>
#include <string>

#include "session_bar_model.h"

struct SessionBarModel {
    SessionState state = SessionState::Idle;
    DisconnectOrigin origin = DisconnectOrigin::None;
    std::wstring target;
    bool logging = false;
};

class SessionBar {
public:
    SessionBar() = default;
    ~SessionBar();

    bool Create(HWND parent);
    void Destroy();
    void Layout(int client_width, int client_height, UINT dpi);
    void Update(const SessionBarModel &model);
    int HeightForDpi(UINT dpi) const;
    bool IsVisible() const;

private:
    HWND parent_ = nullptr;
    HWND status_ = nullptr;
    HWND reconnect_ = nullptr;
    HWND change_server_ = nullptr;
    HWND profiles_ = nullptr;
    HWND disconnect_ = nullptr;
    HWND logging_ = nullptr;
    bool visible_ = false;
    UINT dpi_ = 96;
};
