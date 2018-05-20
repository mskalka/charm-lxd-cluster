
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


PRESEED = yaml.load("""
    config:
      core.https_address: ''
      core.trust_password: 'ubuntu'
    cluster:
      server_name: ''
      enabled: True
      cluster_password: 'ubuntu'
      cluster_address: ''
      cluster_certificate: ''
    networks:
    storage_pools:
    - config:
        source: ''
      description: ''
      name: local
      driver: zfs
    profiles:
    - config: {}
      description: ''
      devices:
        eth0:
          name: eth0
          nictype: bridged
          parent: lxdbr0
          type: nic
        root:
          path: '/'
          pool: local
          type: disk
      name: default
    """)


def init_cluster():
    log('Initializing LXD cluster')
    preseed = _preseed_add_defaults(subordinate=False)
    _lxd_init(preseed)
    if is_unit_clustered():
        log('LXD cluster initialized.')
    else:
        raise('Unit failed to initialize LXD')


def join_cluster(cert):
    preseed = _preseed_add_defaults(subordinate=True, cert=cert)
    _lxd_init(preseed)
    if is_unit_clustered():
        log('LXD cluster initialized.')
    else:
        raise('Unit failed to join the LXD cluster.')


def is_unit_clustered():
    cmd = ['sudo', 'lxc', 'info']
    out = yaml.load(subprocess.check_output(cmd).decode('utf-8'))
    return out['environment']['server_clustered']


def get_cluster_certificate():
    cmd = ['sudo', 'lxc', 'info']
    cert = yaml.load(subprocess.check_output(cmd).decode('utf-8'))
    return cert['environment']['certificate']


def _lxd_init(preseed):
    cmd = ['sudo', 'lxd', 'init', '--preseed']
    subprocess.check_output(cmd, input=preseed.encode('utf-8'))


def _preseed_add_defaults(subordinate=False, cert=None):
    preseed = deepcopy(PRESEED)
    if config('maas-oauth') and config('maas-url'):
        preseed['maas.api.key'] = config('maas-oauth')
        preseed['maas.api.url'] = config('maas-url')
    if subordinate:
        preseed['cluster']['cluster_address'] = '{}:8443'.format(
            leader_get('cluster-ip'))
        if cert:
            preseed['cluster']['cluster_certificate'] = cert
    preseed['config']['core.https_address'] = '{}:8443'.format(
        unit_private_ip())
    preseed['cluster']['server_name'] = socket.gethostname()
    preseed['storage_pools'][0]['config']['source'] = config(
        'host-block-device')
    return yaml.dump(preseed)
