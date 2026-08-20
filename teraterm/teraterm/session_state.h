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

SessionTransition HandleDisconnect(SessionState current, DisconnectOrigin origin);
