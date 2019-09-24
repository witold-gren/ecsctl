import click

from . import wrapboto

from .config import read_config
from .commands import config, cluster, apply, create, update, delete, describe, get, logs, stop, top
from .colorize import HelpColorsGroup


@click.group(cls=HelpColorsGroup)
@click.pass_context
def cli(ctx):
    aws_credentials = {}
    for k, v in read_config().items():
        if k in ctx.obj:
            ctx.obj[k] = v
        if str(k).startswith('aws'):
            aws_credentials[k] = v
    ctx.obj['bw'] = wrapboto.BotoWrapper(**aws_credentials)


cli.add_command(config.config)
cli.add_command(cluster.drain)
cli.add_command(cluster.undrain)
cli.add_command(cluster.run)
cli.add_command(cluster.scale)
cli.add_command(cluster.exec_command)
cli.add_command(create.create)
cli.add_command(apply.apply)
cli.add_command(update.update)
cli.add_command(delete.delete)
cli.add_command(describe.describe)
cli.add_command(get.get)
cli.add_command(logs.logs)
cli.add_command(stop.stop)
cli.add_command(top.top)
