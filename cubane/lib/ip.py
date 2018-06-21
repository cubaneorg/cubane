# coding=UTF-8
from __future__ import unicode_literals
import socket
import ifaddr


LOCAL_IPS = [
    'localhost',
    '127.0.0.1',
    '::1'
]


def get_local_ip_version(family=None, ignore_link_local=True):
    """
    Return the default socket address of the local machine that has a route to
    the internet for the given socket address version/family, e.g.
    - IPv4 (socket.AF_INET) or
    - IPv6 (socket.AF_INET6).
    """
    result_4 = []
    result_6 = []
    adapters = ifaddr.get_adapters()
    for adapter in adapters:
        for ip in adapter.ips:
            if isinstance(ip.ip, tuple):
                if family is None or family == socket.AF_INET6:
                    result_6.append(ip.ip[0])
            else:
                if family is None or family == socket.AF_INET:
                    result_4.append(ip.ip)

    # always deliver IPv4 addresses first and ipv6 addresses last
    result = result_4 + result_6
    return filter(lambda ip: not is_local_ip(ip, ignore_link_local), result)


def get_local_ip(ignore_link_local=True):
    """
    Return the default IPv4 address of the local machine that has a route to the
    internet.
    """
    try:
        return get_local_ip_version(socket.AF_INET, ignore_link_local)[0]
    except IndexError:
        return None


def get_local_ip6(ignore_link_local=True):
    """
    Return the default IPv6 address of the local machine that has a route to the
    internet.
    """
    try:
        return get_local_ip_version(socket.AF_INET6, ignore_link_local)[0]
    except IndexError:
        return None


def is_local_ip(ip, ignore_link_local=True):
    """
    Return True, if the given IP address is a local IPv4 or IPv6 IP address.
    """
    if ignore_link_local:
        return (
            ip in LOCAL_IPS or
            ip.startswith('fe80::') or
            ip.startswith('10.') or
            ip.startswith('127.') or
            ip.startswith('192.168.') or
            ip.startswith('169.254.')
        )
    else:
        return ip in LOCAL_IPS


def get_local_ips(ignore_link_local=True):
    """
    Return a list of default IP addresses (IPv4 and IPv6 if available) of the
    local machine that has a route to the internet.
    """
    return get_local_ip_version(family=None, ignore_link_local=ignore_link_local)