#!/usr/bin/python3
import subprocess

from lxd_clustering_utils import (
    init_cluster,
    join_cluster,
)

from charmhelpers.core.fetch import (
    apt_update,
    apt_install,
    apt_purge,
)

from charmhelpers.core.hookenv import (
    config,
    Hooks,
    is_leader,
    leader_set,
    log,
    network_get_primary_address,
    related_units,
    relation_set,
    relation_get,
    status_set,
)

from charmhelpers.core.fetch.snap import (
    snap_install,
)

from charmhelpers.contrib.openstack.context import (
    ensure_packages,
)

hooks = Hooks()


@hooks.hook('install')
def install():
    '''Install lxd here'''
    status_set('maintenance', 'Installing charm packages')
    apt_purge('lxd lxd-client')
    apt_update()
    apt_install('zfsutils-linux')
    snap_install('lxd')

    status_set('maintenance', 'Setting up zfs pool')
    log('Creating lxc storage "local" using zpool at {}.'.format(
        config('host-block-device')))
    subprocess.call(['lxc', 'storage', 'create', 'local', 'zfs',
                     'source={}'.format(config('host-block-device'))])
    status_set('active', 'Unit is ready')


@hooks.hook('config-changed',
            'upgrade-charm',)
def config_changed():
    '''Update installed packages, nothing else for now'''
    packages = config('extra-packages')
    ensure_packages(packages)


@hooks.hook('cluster-relation-joined',
            'cluster-relation-changed',)
def cluster_changed(relation_id=None):
    '''Perform LXD clustering operations here'''
    rdata = relation_get(rid=relation_id)['cluster-cert']

    if is_leader() and not rdata:
        leader_set(settings={'cluster-ip': network_get_primary_address()})
        cert = init_cluster()
        for rid in related_units('cluster'):
            relation_set(relation_id=rid,
                         relation_settings={'cluster-cert': cert})
    elif not is_leader() and relation_get(rid=relation_id):
        join_cluster(rdata)


@hooks.hook('cluster-relation-departed')
def cluster_departed():
    '''Remove the unit from the cluster when it's torn down'''
    pass
