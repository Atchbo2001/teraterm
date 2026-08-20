#pragma once

enum class SessionState {
    Idle,
    Connecting,
    Connected,
    Disconnecting,
    Disconnected,
    Failed,
};

enum class DisconnectOrigin {
    None,
    UserRequested,
    RemoteOrNetwork,
    Authentication,
};

struct SessionTransition {
    SessionState next;
    bool show_recovery;
    bool close_window;
};

inline SessionTransition HandleDisconnect(SessionState current, DisconnectOrigin origin)
{
    SessionTransition transition{};
    transition.close_window = false;

    switch (origin) {
    case DisconnectOrigin::UserRequested:
        transition.next = SessionState::Disconnected;
        transition.show_recovery = false;
        break;

    case DisconnectOrigin::Authentication:
        transition.next = current == SessionState::Connecting ? SessionState::Failed : SessionState::Disconnected;
        transition.show_recovery = true;
        break;

    case DisconnectOrigin::RemoteOrNetwork:
    case DisconnectOrigin::None:
    default:
        transition.next = SessionState::Disconnected;
        transition.show_recovery = true;
        break;
    }

    return transition;
}

inline DisconnectOrigin ConsumeDisconnectOrigin(DisconnectOrigin *pending, DisconnectOrigin fallback)
{
    const DisconnectOrigin origin = *pending == DisconnectOrigin::None ? fallback : *pending;
    *pending = DisconnectOrigin::None;
    return origin;
}
