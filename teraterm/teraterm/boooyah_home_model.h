#pragma once

#include <string>

enum class QuickProtocol {
    Ssh,
    Telnet,
    RawTcp,
    Serial,
};

struct QuickConnectRequest {
    std::wstring host;
    std::wstring username;
    int port = 0;
    QuickProtocol protocol = QuickProtocol::Ssh;
    int com_port = 0;
};

inline bool ValidateQuickConnect(const QuickConnectRequest &request, std::wstring *error)
{
    if (error != nullptr) {
        error->clear();
    }

    if (request.protocol == QuickProtocol::Serial) {
        if (request.com_port <= 0) {
            if (error != nullptr) {
                *error = L"Choose a serial port.";
            }
            return false;
        }
        return true;
    }

    if (request.host.empty()) {
        if (error != nullptr) {
            *error = L"Enter a host name or address.";
        }
        return false;
    }

    if (request.port <= 0 || request.port > 65535) {
        if (error != nullptr) {
            *error = L"Port must be between 1 and 65535.";
        }
        return false;
    }

    return true;
}
