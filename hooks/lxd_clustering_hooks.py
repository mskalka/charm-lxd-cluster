#!/usr/bin/python3
import socket
import subprocess
import yaml

from charmhelpers.core.hookenv import (
    relation_set,
    relation_get,
    config,
    is_leader,
    leader_get,
    leader_set
    status_set,
    Hooks,
    local_unit,
    network_get_primary_address,
)

from charmhelpers.core.fetch import (
    apt_update,
    apt_install,
    apt_purge,
)
from charmhelpers.core.fetch.snap import (
    snap_install,
)

hooks = Hooks()

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
        'networks': [],
        'storage_pools': [
            {'config': {'source': config('host-block-device')},
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
                          'parent': config('host-bridge-interface'),
                          'type': 'nic'},
                 'root': {'path': '/',
                          'pool': 'local',
                          'type': 'disk'}},
                 'name': 'default'}]}


@hooks.hook('install')
def install():
    '''Install lxd here'''
    apt_purge('lxd lxd-client')
    apt_update()
    apt_install('zfsutils-linux')
    snap_install('lxd')


@hooks.hook('config-changed',
            'upgrade-charm',)
def config_changed():
    '''Update installed packages'''
    packages = config('extra-packages')


@hooks.hook('cluster-relation-joined',
            'cluster-relation-changed',)
def cluster_changed(relation_id=None):
    '''Perform LXD clustering operations here'''
    rdata = relation_get(rid=relation_id)

    if is_leader() and not rdata:
        leader_set(settings={'cluster-ip': network_get_primary_address()})
        cmd = ['lxd', 'init', '--preseed', yaml.dump(PRESEED)]
        subprocess.call(cmd)
        for rid in related_units('cluster'):
            relation_set(relation_id=rid,
                         relation_settings={'cluster-cert': cert})
    elif not is_leader() and relation_get(rid=relation_id):
        PRESEED['config']['cluster']['cluster_address'] = \
            leader_get('cluster-ip')
        PRESEED['config']['cluster']['cluster_address'] = \
            rdata['cert']
        cmd = ['lxd', 'init', '--preseed', yaml.dump(PRESEED)]
        subprocess.call(cmd)
