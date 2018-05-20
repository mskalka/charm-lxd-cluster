#!/usr/bin/env python3

from charms.reactive import (
    hook,
    set_state,
    remove_state,
    when,
    when_not,
)

from charms.layer.lxd import (
    init_cluster,
    init_storage,
    join_cluster,
)

from charmhelpers.fetch import (
    apt_purge,
)

from charms.layer import snap

from charmhelpers.core.hookenv import (
    config,
    is_leader,
    leader_get,
    leader_set,
    log,
    status_set,
    unit_private_ip,
)

from charmhelpers.contrib.openstack.context import (
    ensure_packages,
)


@when_not('lxd.machine.ready')
def prepare_machine():
    '''Install lxd here'''
    status_set('maintenance', 'Preparing machine')
    apt_purge(['lxc', 'lxd', 'lxd-client'])
    set_state('lxd.machine.ready')


@when('lxd.machine.ready')
@when_not('snap.installed.lxd')
def install_snap():
    channel = config('channel')
    # Grab the snap channel from config
    snap.install('lxd', channel=channel)


@when('snap.installed.lxd')
@when_not('lxd.ready')
def install():
    status_set('maintenance', 'Setting up zfs pool')
    init_storage()
    status_set('active', 'Unit is ready')
    set_state('lxd.ready')


@when('config.changed.extra-packages')
def config_changed():
    '''Update installed packages, more to come'''
    if config('extra-packages'):
        ensure_packages(config('extra-packages').split(','))


@hook('upgrade-charm')
def remove_states():
    # stale state cleanup (pre rev6)
    remove_state('lxd.installed')


@hook('leader-elected')
def set_cluster_ip():
    if is_leader():
        leader_set(settings={'cluster-ip': unit_private_ip()})
    else:
        log('Not the leader, passing')


@when('lxd-cluster.connected')
def initialize_cluster():
    if is_leader():
        leader_set(settings={'cluster-ip': unit_private_ip(),
                             'cluster-cert': init_cluster()})
        set_state('cluster-initialized')
    else:
        log('Not the leader, waiting for leader to initialize cluster.')


@when('lxd-cluster.connected',
      'cluster-initialized')
def connect_cluster():
    if is_leader():
        return
    cert = leader_get('cluster-cert')
    if cert:
        join_cluster(cert)
    else:
        log('Something went wrong here; certificate not set, '
            'passing until available.')
