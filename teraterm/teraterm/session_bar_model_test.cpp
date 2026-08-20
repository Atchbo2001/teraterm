#include "session_bar_model.h"

#include <cassert>

static void connected_has_work_actions()
{
    const SessionBarPresentation p = BuildSessionBarPresentation(SessionState::Connected, DisconnectOrigin::None, false);
    assert(p.visible);
    assert(p.show_disconnect);
    assert(p.show_logging);
    assert(!p.show_reconnect);
}

static void remote_disconnect_has_recovery_actions()
{
    const SessionBarPresentation p = BuildSessionBarPresentation(SessionState::Disconnected, DisconnectOrigin::RemoteOrNetwork, false);
    assert(p.visible);
    assert(p.show_reconnect);
    assert(p.show_change_server);
    assert(p.show_profiles);
    assert(!p.show_disconnect);
}

static void intentional_disconnect_is_quiet()
{
    const SessionBarPresentation p = BuildSessionBarPresentation(SessionState::Disconnected, DisconnectOrigin::UserRequested, false);
    assert(p.visible);
    assert(!p.show_reconnect);
    assert(p.show_change_server);
    assert(p.show_profiles);
}

int main()
{
    connected_has_work_actions();
    remote_disconnect_has_recovery_actions();
    intentional_disconnect_is_quiet();
    return 0;
}
