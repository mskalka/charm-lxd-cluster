#!/usr/bin/env python3

from base64 import (
    b64encode,
    b64decode
)
import subprocess

from lxd_clustering_utils import (
    init_cluster,
    join_cluster,
)

from charmhelpers.fetch import (
    apt_update,
    apt_install,
    apt_purge,
)

from charmhelpers.fetch.snap import (
    snap_install,
)

from charmhelpers.core.hookenv import (
    Hooks,
    config,
    is_leader,
    leader_set,
    log,
    related_units,
    relation_set,
    relation_get,
    status_set,
    unit_private_ip,
)

from charmhelpers.contrib.openstack.context import (
    ensure_packages,
)

hooks = Hooks()


@hooks.hook('install.real')
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
    c_cert = b64decode(relation_get(rid=relation_id).get('cluster-cert', ''))

    if is_leader() and len(c_cert):
        leader_set(settings={'cluster-ip': unit_private_ip()})
        n_cert = b64encode(init_cluster())
        for rid in related_units('cluster'):
            relation_set(relation_id=rid,
                         relation_settings={'cluster-cert': n_cert})
    elif not is_leader() and len(c_cert):
        join_cluster(c_cert)


@hooks.hook('cluster-relation-departed')
def cluster_departed():
    '''Remove the unit from the cluster when it's torn down'''
    pass
