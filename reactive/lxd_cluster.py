#!/usr/bin/env python3

from charms.reactive import (
    hook,
    set_state,
    remove_state,
    when,
    when_not,
)

from charms.layer.lxd import (
    get_cluster_certificate,
    init_cluster,
    is_unit_clustered,
    join_cluster,
)

from charmhelpers.fetch import (
    apt_install,
    apt_purge,
)

from charms.layer import snap

from charmhelpers.core.hookenv import (
    config,
    is_leader,
    leader_get,
    leader_set,
    log,
    network_get_primary_address,
    status_set,
)

from charmhelpers.contrib.openstack.context import (
    ensure_packages,
)


@when_not('lxd.machine.ready')
def prepare_machine():
    '''Install lxd here'''
    status_set('maintenance', 'Preparing machine')
    apt_purge(['lxc', 'lxd', 'lxd-client'])
    apt_install('criu')
    set_state('lxd.machine.ready')


@when('lxd.machine.ready')
@when_not('snap.installed.lxd')
def install_snap():
    channel = config('channel')
    # Grab the snap channel from config
    snap.install('lxd', channel=channel)


@when('config.changed.extra-packages')
def config_changed():
    '''Update installed packages, more to come'''
    if config('extra-packages'):
        ensure_packages(config('extra-packages').split(','))


@hook('leader-elected')
def set_cluster_ip():
    if is_leader():
        leader_set(settings={
            'cluster-ip': network_get_primary_address('cluster')})
    else:
        log('Not the leader, passing')


@when('cluster.joined',
      'snap.installed.lxd')
@when_not('lxd-cluster-joined')
def initialize_cluster():
    if not leader_get('cluster-ip'):
        log('Cluster IP not set, waiting to initialize.')
        return
    if is_leader() and not is_unit_clustered():
        init_cluster()
        cert = get_cluster_certificate()
        cluster_ip =  network_get_primary_address('cluster')
        leader_set(settings={'cluster-ip': cluster_ip,
                             'cluster-cert': cert})
        set_state('lxd-cluster-joined')
        status_set('active', 'Unit is ready and clustered')
    else:
        log('Not the leader, waiting for leader to initialize cluster.')


@when('cluster.joined')
@when_not('lxd-cluster-joined')
def connect_cluster():
    if is_leader() or is_unit_clustered():
        return
    if leader_get('cluster-started'):
        status_set('waiting', 'Waiting for leader to init cluster')
        log('Waiting for leader to start cluster, passing.')
        return
    cert = leader_get('cluster-cert')
    if cert:
        log('Certificate found, joining the cluster')
        join_cluster(cert)
        set_state('lxd-cluster-joined')
        status_set('active', 'Unit is ready and clustered')
    else:
        log('Certificate not set, passing until available.')
        return
