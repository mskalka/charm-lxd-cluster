
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
                'cluster_password': 'ubuntu'},
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
         'name': 'default',
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
         }]}


def init_storage():
    log('Creating lxc storage "local" using zpool at {}.'.format(
        config('host-block-device')))
    subprocess.call(['lxc', 'storage', 'create', 'local', 'zfs',
                     'source={}'.format(config('host-block-device'))])


def init_cluster():
    log('Initializing LXD cluster')
    preseed = preseed_add_defaults()
    cmd = ['lxd', 'init', '--debug', '--preseed']
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    proc.stdin.write(yaml.dump(preseed))
    proc.stdin.close()
    while proc.returncode is None:
        proc.poll()

    return get_cluster_certificate()


def get_cluster_certificate():
    cmd = ['lxc', 'info']
    cert = yaml.load(
        subprocess.check_output(cmd))['environment']['certificate']
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
        if cert:
            preseed['cluster']['cluster_certificate'] = cert
    return preseed
