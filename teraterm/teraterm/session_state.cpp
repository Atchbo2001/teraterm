#include "session_state.h"

SessionTransition HandleDisconnect(SessionState current, DisconnectOrigin origin)
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
