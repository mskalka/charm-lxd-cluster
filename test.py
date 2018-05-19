#!/usr/bin/python
from copy import deepcopy

import subprocess
import yaml

PRESEED = yaml.load('''
    'config':
        'core.https_address': '100.72.104.66:8444'
        'core.trust_password': 'cluster'
    'cluster':
        'server_name': 'mskalka'
        'enabled': True
        'cluster_password': ''
    'networks':
      - 'name': 'lxdbr0'
        'type': 'bridge'
        'config':
            'ipv4.address': 'auto'
            'ipv6.address': 'none'
    'storage_pools':
      - 'config': {}
        'description': ''
        'name': 'local'
        'driver': 'zfs'
    'profiles':
      - 'config': {}
        'name': 'default'
        'description': ''
        'devices':
            'eth0':
                'name': 'eth0'
                'nictype': 'bridged'
                'parent': 'lxdbr0'
                'type': 'nic'
            'root':
                'path': '/'
                'pool': 'local'
                'type': 'disk'
    ''')


def main():
    preseed = deepcopy(PRESEED)
    # preseed['cluster']['cluster_certificate'] = get_cluster_certificate()
    cmd = ['lxd', 'init', '--debug', '--preseed']
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    proc.stdin.write(yaml.dump(preseed))
    proc.stdin.close()
    while proc.returncode is None:
        proc.poll()


def get_cluster_certificate():
    cmd = ['lxc', 'info']
    cert = yaml.load(
        subprocess.check_output(cmd))['environment']['certificate']
    return cert


if __name__ == '__main__':
    main()
