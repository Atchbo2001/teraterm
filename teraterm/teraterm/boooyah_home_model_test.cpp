#include "boooyah_home_model.h"

#include <cassert>
#include <string>

static void ssh_requires_host()
{
    QuickConnectRequest request{};
    request.protocol = QuickProtocol::Ssh;
    request.port = 22;
    std::wstring error;
    assert(!ValidateQuickConnect(request, &error));
    assert(!error.empty());
}

static void ssh_accepts_normal_target()
{
    QuickConnectRequest request{};
    request.protocol = QuickProtocol::Ssh;
    request.host = L"server01";
    request.username = L"operator";
    request.port = 22;
    std::wstring error;
    assert(ValidateQuickConnect(request, &error));
    assert(error.empty());
}

static void network_port_must_be_valid()
{
    QuickConnectRequest request{};
    request.protocol = QuickProtocol::RawTcp;
    request.host = L"10.0.0.25";
    request.port = 0;
    std::wstring error;
    assert(!ValidateQuickConnect(request, &error));
}

static void serial_requires_com_port_not_host()
{
    QuickConnectRequest request{};
    request.protocol = QuickProtocol::Serial;
    request.com_port = 7;
    std::wstring error;
    assert(ValidateQuickConnect(request, &error));
}

int main()
{
    ssh_requires_host();
    ssh_accepts_normal_target();
    network_port_must_be_valid();
    serial_requires_com_port_not_host();
    return 0;
}
