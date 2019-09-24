import click
from .. import wrapboto
from ..config import read_config, update_config, update_context, get_clusters, get_default_context
from ..colorize import HelpColorsGroup


@click.group(cls=HelpColorsGroup, short_help='Manage config file.')
def config():
    pass


@config.command(name='set')
@click.argument('name', required=True)
@click.option('--cluster-name', required=True)
@click.option('--docker-port')
@click.option('--docker-api-version')
@click.option('--aws-access-key-id')
@click.option('--aws-secret-access-key')
@click.option('--aws-region')
@click.option('--aws-session-token')
@click.option('--aws-profile')
@click.pass_context
def config_set(ctx, name, cluster_name, **kwargs):
    """
    \b
    # Create configuration for new cluster usage aws profile
    cmd::ecsctl config set my-own-config-name --cluster-name my-cluster --aws-profile my-aws-profile

    \b
    # Create configuration for new cluster usage access-key and secret-access
    cmd::ecsctl config set my-own-config-name --cluster-name my-cluster --aws-access-key-id XXX --aws-secret-access-key YYY --aws-region ZZZ

    \b
    # Set docker port for existing cluster
    cmd::ecsctl config set my-own-config-name --docker-port 64646

    \b
    # Set docker api version for existing cluster
    cmd::ecsctl config set my-own-config-name --docker-api-version 1.30
    """
    out = update_config(name, cluster_name, **kwargs)
    click.echo(out)


@config.command(name='context')
@click.argument('name', required=True, type=click.Choice(get_clusters()))
@click.pass_context
def context_set(ctx, name, **kwargs):
    """
    \b
    # Change default cluster to another
    cmd::ecsctl config context my-own-config-name-2
    """
    out = update_context(name, **kwargs)
    click.echo(out)


@config.command(name='show')
@click.option('--show-path', default=None, is_flag=True)
@click.option('--show-all', default=None, is_flag=True)
def config_show(show_path, show_all=None):
    """
    \b
    # Show configuration for default cluster
    cmd::ecsctl config show

    \b
    # Show configuration for all configured clusters
    cmd::ecsctl config show --show-all

    \b
    # Show path for config file
    cmd::ecsctl config show --show-path
    """
    config = read_config(show_path, show_all)
    if config and not show_all:
        output = ['[{}]'.format(get_default_context())]
        for k, v in config.items():
            output.append('{} = {}'.format(k, v))
    elif config and show_all:
        output = []
        for name, params in config.items():
            output.append('[{}]'.format(name))
            for k, v in params.items():
                output.append('{} = {}'.format(k, v))
            output.append('')
        if output:
            output = output[:-1]
    click.echo('\n'.join(output))
