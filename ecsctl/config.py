import os

from configparser import RawConfigParser
from os.path import expanduser

__all__ = ['read_config', 'update_config', 'default_config']


SECTION = 'ecsctl'
CONTEXT = 'context'
APP_DIR = os.path.join(expanduser("~"), '.ecsctl')
CONFIG_FILE = os.path.join(APP_DIR, 'config')

default_config = {
    'cluster': os.environ.get('AWS_ECS_CLUSTER_NAME', 'default'),
    'aws_access_key_id': None,
    'aws_secret_access_key': None,
    'aws_role_arn': None,
    'aws_mfa_serial': None,
    'aws_region': None,
    'aws_session_token': None,
    'aws_profile': None,
    'ssh_user': os.environ.get('AWS_ECS_SSH_USER', 'ec2-user'),
    'ssh_bastion_user': os.environ.get('AWS_ECS_SSH_BASTION_USER', 'ec2-user'),
    'ssh_bastion_ip': os.environ.get('AWS_ECS_SSH_BASTION_IP', None),
    'ssh_key_location': os.environ.get('AWS_ECS_SSH_KEY_LOCATION', "~/.ssh/id_rsa"),
    '_aws_expiration': None,
    '_aws_session_token': None,
    '_aws_access_key_id': None,
    '_aws_secret_access_key': None
}


def get_config_parser():
    parser = RawConfigParser()
    if os.path.isfile(CONFIG_FILE):
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
    default = None
    parser = get_config_parser()
    if parser.has_section(SECTION):
        default = parser.get(SECTION, CONTEXT)
    return default


def read_config(show_file_path=None, show_all=None, show_temporary=None):
    context = get_default_context()
    parser = get_config_parser()
    rv, pars = {}, {}
    if show_file_path:
        print(CONFIG_FILE)
    if context:
        pars = parser.items(context)
    if show_all:
        for section in parser.sections():
            parse = {}
            for key, value in parser.items(section):
                if not key.startswith('_aws'):
                    parse[key] = value
                if show_temporary and key.startswith('_aws'):
                    parse[key] = value
            rv[section] = parse
    else:
        for key, value in pars:
            if not key.startswith('_aws'):
                rv[key] = value
            if show_temporary and key.startswith('_aws'):
                rv[key] = value
    return rv


def update_config(name, cluster_name, **kwargs):
    update_context(name)
    parser = get_config_parser()
    if not parser.has_section(name):
        parser.add_section(name)
    if cluster_name:
        parser.set(name, 'cluster', cluster_name)
    else:
        cluster_name = parser.get(name, 'cluster')
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
