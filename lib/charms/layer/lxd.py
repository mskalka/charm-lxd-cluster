
from copy import deepcopy

import socket
import subprocess
import yaml

from charmhelpers.core.hookenv import (
    config,
    leader_get,
    log,
    unit_private_ip,
)


PRESEED = {
    'config':
        {'core.https_address': unit_private_ip(),
         'core.trust_password': 'cluster'
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
    preseed = preseed_add_defaults()
    log('Initializing LXD cluster')
    cmd = ['lxd', 'init', '--preseed', yaml.dump(preseed)]
    subprocess.call(cmd)
    with open('/var/lib/lxd/server.crt') as cert_file:
        cert = cert_file.read()
    return cert


def join_cluster(cert):
    preseed = preseed_add_defaults(subordinate=True, cert=cert)
    cmd = ['lxd', 'init', '--preseed', yaml.dump(preseed)]
    subprocess.call(cmd)


def preseed_add_defaults(subordinate=False, cert=None):
    preseed = deepcopy(PRESEED)
    if config('maas-oauth') and config('maas-url'):
        preseed['maas.api.key'] = config('maas-oauth')
        preseed['maas.api.url'] = config('maas-url')
    if subordinate:
        preseed['cluster']['cluster_address'] = leader_get('cluster-ip')
        preseed['cluster']['cluster_certificate'] = cert
    return preseed
