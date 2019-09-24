import os
import click
from configparser import RawConfigParser
from os.path import expanduser


__all__ = ['read_config', 'update_config', 'default_config']

SECTION = 'ecsctl'
CONTEXT = 'context'
APP_DIR = os.path.join(expanduser("~"), '.ecsctl')
CONFIG_FILE = os.path.join(APP_DIR, 'config')

default_config = {
    'cluster': 'default',
    'docker_port': 2375,
    'docker_api_version': '1.24',
    'aws-access-key-id': None,
    'aws-secret-access-key': None,
    'aws-region': None,
    'aws-session-token': None,
    'aws-profile': None,
}


def get_config_parser():
    parser = RawConfigParser()
    parser.read([CONFIG_FILE])
    return parser


def get_clusters():
    parser = get_config_parser()
    clusters = []
    for name in parser.sections():
        if name != SECTION:
            clusters.append(name)
    return clusters


def get_default_context():
    parser = get_config_parser()
    return parser.get(SECTION, CONTEXT)


def read_config(show_file_path=None, show_all=None):
    context = get_default_context()
    parser = get_config_parser()
    rv = {}
    if show_file_path:
        print(CONFIG_FILE)
    pars = parser.items(context)
    if show_all:
        for section in parser.sections():
            parse = {}
            for key, value in parser.items(section):
                parse[key] = value
            rv[section] = parse
    else:
        for key, value in pars:
            rv[key] = value
    return rv


def update_config(name, cluster_name, **kwargs):
    update_context(name)
    parser = get_config_parser()
    if not parser.has_section(name):
        parser.add_section(name)
    parser.set(name, 'cluster', cluster_name)
    for key, value in kwargs.items():
        if value:
            parser.set(name, key, value)
    if not os.path.exists(APP_DIR):
        os.mkdir(APP_DIR)
    with open(CONFIG_FILE, 'w') as f:
        parser.write(f)
    return 'Cluster "{}" was configured.'.format(cluster_name)


def update_context(cluster_name, **kwargs):
    parser = get_config_parser()
    if not parser.has_section(SECTION):
        parser.add_section(SECTION)
    parser.set(SECTION, CONTEXT, cluster_name)
    if not os.path.exists(APP_DIR):
        os.mkdir(APP_DIR)
    with open(CONFIG_FILE, 'w') as f:
        parser.write(f)
    return 'Active cluster is "{}".'.format(cluster_name)
