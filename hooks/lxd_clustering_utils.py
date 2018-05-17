#!/usr/bin/python3

from copy import deepcopy
import socket
import subprocess
import yaml

from charmhelpers.core.hookenv import (
    config,
    leader_get,
    log,
    network_get_primary_address,
)


PRESEED = {
    'config':
        {'core.https_address': network_get_primary_address(),
         'core.trust_password': 'cluster',
         'maas.api.key': config('maas-oauth'),
         'maas.api.url': config('maas-url')
         },
        'cluster': {'server_name': socket.gethostname(),
                    'enabled': True,
                    'cluster_address': '',
                    'cluster_certificate': '',
                    'cluster_password': ''},
        'networks': [{'name': 'lxdbr0',
                      'type': 'bridge',
                      'config': {'ipv4.address': 'auto',
                                 'ipv6.address': 'none'}
                      }],
        'storage_pools': [
            {'config': {},
             'description': '',
             'name': 'local',
             'driver': 'zfs'}],
        'profiles': [
            {'config': {},
             'description': '',
             'devices':
                {'eth0': {'maas.subnet.ipv4': config('cluster-cidr'),
                          'name': 'eth0',
                          'nictype': 'bridged',
                          'parent': 'lxdbr0',
                          'type': 'nic'},
                 'root': {'path': '/',
                          'pool': 'local',
                          'type': 'disk'}},
                 'name': 'default'}]}


def init_cluster():
    preseed = deepcopy(PRESEED)
    log('Initializing LXD cluster')
    cmd = ['lxd', 'init', '--preseed', yaml.dump(preseed)]
    subprocess.call(cmd)
    with open('/var/lib/lxd/server.crt') as cert_file:
        cert = cert_file.read()
    return cert


def join_cluster(cert):
    preseed = deepcopy(PRESEED)
    preseed['config']['cluster']['cluster_address'] = leader_get('cluster-ip')
    preseed['config']['cluster']['cluster_address'] = cert
    cmd = ['lxd', 'init', '--preseed', yaml.dump(preseed)]
    subprocess.call(cmd)
