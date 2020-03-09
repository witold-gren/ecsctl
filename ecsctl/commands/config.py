import click
from .. import wrapboto
from ..config import read_config, update_config, update_context, get_clusters, get_default_context
from ..colorize import HelpColorsGroup


@click.group(cls=HelpColorsGroup, short_help='Manage config file.')
def config():
    pass


@config.command(name='set')
@click.argument('name', required=True)
@click.option('--cluster-name')
@click.option('--aws-access-key-id')
@click.option('--aws-secret-access-key')
@click.option('--aws-region')
@click.option('--aws-role-arn')
@click.option('--aws-mfa-serial')
@click.option('--aws-session-token')
@click.option('--aws-profile')
@click.option('--ssh-user', default="ec2-user", show_default=True)
@click.option('--ssh-bastion-user', default="ec2-user", show_default=True)
@click.option('--ssh-bastion-ip')
@click.option('--ssh-key-location', default="~/.ssh/id_rsa", show_default=True)
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
    # Set bastion host IP and ssh key
    cmd::ecsctl config set my-own-config-name --ssh-bastion-ip 1.2.3.4 --ssh-key-location ~/.ssh/my_extra_key

    \b
    # Set bastion host IP and ssh key
    cmd::ecsctl config set my-own-config-name --cluster-name my-cluster --aws-profile XXX --aws-region ZZZ --aws-role-arn XXX --aws-mfa-serial XXX
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
@click.option('-p', '--path', default=False, is_flag=True)
@click.option('-a', '--all', default=False, is_flag=True)
@click.option('-t', '--temporary', default=False, is_flag=True)
def config_show(path=None, all=None, temporary=None):
    """
    \b
    # Show configuration for default cluster
    cmd::ecsctl config show

    \b
    # Show configuration for all configured clusters
    cmd::ecsctl config show --all

    \b
    # Show path for config file
    cmd::ecsctl config show --path

    \b
    # Show cached AWS credentials in config file
    cmd::ecsctl config show --temporary
    """
    config = read_config(path, all, temporary)
    if config and not all:
        output = ['[{}]'.format(get_default_context())]
        for k, v in config.items():
            output.append('{} = {}'.format(k, v))
    elif config and all:
        output = []
        for name, params in config.items():
            output.append('[{}]'.format(name))
            for k, v in params.items():
                output.append('{} = {}'.format(k, v))
            output.append('')
        if output:
            output = output[:-1]
    click.echo('\n'.join(output))
