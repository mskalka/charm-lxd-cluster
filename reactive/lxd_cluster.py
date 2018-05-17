#!/usr/bin/env python3

from base64 import (
    b64encode,
    b64decode
)

import subprocess

from charms.reactive import when
from charms.reactive import when_any
from charms.reactive import when_not
from charms.reactive import set_state
from charms.reactive import remove_state

from charms.layer.lxd import (
    init_cluster,
    join_cluster,
)

from charmhelpers.fetch import (
    apt_update,
    apt_install,
    apt_purge,
)

from charms.layer import snap

from charmhelpers.core import hookenv

from charmhelpers.contrib.openstack.context import (
    ensure_packages,
)


@when_not('lxd.machine.ready')
def prepare_machine():
    '''Install lxd here'''
    status_set('maintenance', 'Preparing machine')
    apt_purge('lxd lxd-client')

    set_state('lxd.machine.ready')


@when('lxd.machine.ready')
@when_not('snap.installed.lxd')
def install_snap():
    channel = hookenv.config('channel')
    # Grab the snap channel from config
    snap.install('lxd', channel=channel)


@when('snap.installed.lxd')
@when_not('lxd.ready')
def install():

    status_set('maintenance', 'Setting up zfs pool')
    log('Creating lxc storage "local" using zpool at {}.'.format(
        config('host-block-device')))
    subprocess.call(['lxc', 'storage', 'create', 'local', 'zfs',
                     'source={}'.format(config('host-block-device'))])
    status_set('active', 'Unit is ready')
    set_state('lxd.ready')


@when('config.changed.extra-packages')
def config_changed():
    '''Update installed packages, nothing else for now'''
    packages = config('extra-packages')
    ensure_packages(packages)


@hook('upgrade-charm')
def remove_states():
    # stale state cleanup (pre rev6)
    remove_state('lxd.installed')


# TODO: Oh no, need to create interface
@hooks.hook('cluster-relation-joined',
            'cluster-relation-changed',)
def cluster_changed(relation_id=None):
    '''Perform LXD clustering operations here'''

    if is_leader():
        # Check if we have certs already
        if not certs:
            #init this shitttt
            # Generate them
            leader_set(certs)

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
