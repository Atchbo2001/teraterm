#pragma once

#include "session_state.h"

struct SessionBarPresentation {
    bool visible;
    bool show_reconnect;
    bool show_change_server;
    bool show_profiles;
    bool show_disconnect;
    bool show_logging;
};

inline SessionBarPresentation BuildSessionBarPresentation(SessionState state, DisconnectOrigin origin, bool logging)
{
    SessionBarPresentation presentation{};
    presentation.visible = state != SessionState::Idle;
    presentation.show_logging = state == SessionState::Connected || logging;

    if (state == SessionState::Connected) {
        presentation.show_disconnect = true;
        return presentation;
    }

    if (state == SessionState::Disconnected || state == SessionState::Failed) {
        presentation.show_change_server = true;
        presentation.show_profiles = true;
        presentation.show_reconnect = origin != DisconnectOrigin::UserRequested;
    }

    return presentation;
}
