# coding=UTF-8
from __future__ import unicode_literals
from cubane.tests.base import CubaneTestCase
from cubane.lib.ip import *
import socket


class LibIPTestCase(CubaneTestCase):
    def test_get_local_ip_should_return_ipv4_address(self):
        ip = get_local_ip(ignore_link_local=False)
        self.assertIP(ip, socket.AF_INET)


    def test_get_local_ip_should_return_ipv4_address_ignoring_local_link(self):
        # since we do not know if the machine that runs the test has
        # a public IP, we only validate if we get an address back
        ip = get_local_ip()
        if ip:
            self.assertIP(ip, socket.AF_INET)


    def test_get_local_ip6_may_return_ipv6_or_none(self):
        ip = get_local_ip6(ignore_link_local=False)

        # since we do not know if the machine that runs the test has IPv6,
        # we only validate if we get an address back
        if ip:
            self.assertIP(ip, socket.AF_INET6)


    def test_get_local_ip6_may_return_ipv6_or_none_ignoring_local_link(self):
        ip = get_local_ip6()

        # since we do not know if the machine that runs the test has a public
        # IPv6, we only validate if we get an address back
        if ip:
            self.assertIP(ip, socket.AF_INET6)


    def test_get_local_ips_should_return_ipv4_and_ipv6_addresses_if_available(self):
        ips = get_local_ips(ignore_link_local=False)

        # since we do not know if the machine that runs the test has IPv6,
        # we expect ipv4 as the first address and (optionally) ipv6 as
        # the second...
        self.assertTrue(len(ips) >= 1)
        self.assertIP(ips[0], socket.AF_INET)
        if len(ips) > 1:
            self.assertIP(ips[1], socket.AF_INET6)


    def test_get_local_ips_should_return_ipv4_and_ipv6_addresses_if_available_ignoring_local_link(self):
        ips = get_local_ips()

        # the machine might not have any public-facig IP addresses, but if we
        # have, assume that the first one is an IPv4...
        if ips:
            self.assertIP(ips[0], socket.AF_INET)
            if len(ips) > 1:
                self.assertIP(ips[1], socket.AF_INET6)


    def assertIP(self, ip, family):
        if not ip.startswith('169.254.'):
            try:
                socket.inet_pton(family, ip)
            except socket.error:
                raise AssertionError('The ip address \'%s\' appears to be invalid.' % ip)