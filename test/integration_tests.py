#!/usr/bin/env python
import dns.resolver
import dns.reversename
import pytest
import random
import requests
import socket
import string
import struct
import subprocess


@pytest.fixture
def resolver():
    """
    Return a resolver object against the configured powerdns server
    """
    resolver = dns.resolver.Resolver(configure=False)
    resolver.nameservers = ['127.0.0.1']
    resolver.port = 5300

    return resolver


@pytest.fixture
def smart_proxy_url():
    return 'http://localhost:8000/'


@pytest.fixture
def fqdn():
    return ''.join(random.sample(string.lowercase, 10)) + '.' + 'example.com'


@pytest.fixture
def ip():
    return socket.inet_ntoa(struct.pack("!I", random.randint(1, 2 ** 32)))


def purge_cache(name):
    subprocess.check_output(['sudo', 'pdns_control', 'purge', name])


def test_forward_dns(resolver, smart_proxy_url, fqdn, ip):
    response = requests.post(smart_proxy_url + 'dns/',
                             data={'fqdn': fqdn, 'value': ip, 'type': 'A'})
    response.raise_for_status()

    answer = resolver.query(fqdn, 'A')
    assert len(answer.rrset.items) == 1
    assert answer.rrset.items[0].address == ip

    response = requests.delete(smart_proxy_url + 'dns/' + fqdn)
    response.raise_for_status()

    purge_cache(fqdn)

    with pytest.raises(dns.resolver.NXDOMAIN):
        resolver.query(fqdn, 'A')


def test_reverse_dns(resolver, smart_proxy_url, fqdn, ip):
    response = requests.post(smart_proxy_url + 'dns/',
                             data={'fqdn': fqdn, 'value': ip, 'type': 'PTR'})
    response.raise_for_status()

    name = dns.reversename.from_address(ip)

    answer = resolver.query(name, 'PTR')
    assert len(answer.rrset.items) == 1
    assert answer.rrset.items[0].target.to_text() == fqdn + '.'

    response = requests.delete(smart_proxy_url + 'dns/' + name.to_text().rstrip('.'))
    response.raise_for_status()

    purge_cache(name.to_text())

    with pytest.raises(dns.resolver.NXDOMAIN):
        resolver.query(name, 'PTR')
