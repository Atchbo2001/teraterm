#include "session_state.h"

#include <cassert>

static void test_remote_disconnect_stays_open_and_offers_recovery()
{
    const SessionTransition transition = HandleDisconnect(SessionState::Connected, DisconnectOrigin::RemoteOrNetwork);
    assert(transition.next == SessionState::Disconnected);
    assert(transition.show_recovery);
    assert(!transition.close_window);
}

static void test_user_disconnect_stays_open_without_recovery_nag()
{
    const SessionTransition transition = HandleDisconnect(SessionState::Connected, DisconnectOrigin::UserRequested);
    assert(transition.next == SessionState::Disconnected);
    assert(!transition.show_recovery);
    assert(!transition.close_window);
}

static void test_authentication_failure_stays_open_and_offers_recovery()
{
    const SessionTransition transition = HandleDisconnect(SessionState::Connecting, DisconnectOrigin::Authentication);
    assert(transition.next == SessionState::Failed);
    assert(transition.show_recovery);
    assert(!transition.close_window);
}

int main()
{
    test_remote_disconnect_stays_open_and_offers_recovery();
    test_user_disconnect_stays_open_without_recovery_nag();
    test_authentication_failure_stays_open_and_offers_recovery();
    return 0;
}
