import click

from ..alias import AliasedGroup
from .. import wrapboto, display


@click.group(cls=AliasedGroup, short_help='Stop service.')
def stop():
    pass


@stop.command(name='task')
@click.argument('task', required=True)
@click.option('--reason', default='Stopped with ecsctl',
              help="Message why you stop task")
@click.option('--raw-response', default=False, show_default=True,
              help="Raw response after stopped task.")
@click.option('-c', '--cluster',
              help="Specify cluster to execute command. Default usage cluster from context.")
@click.pass_context
def stop_task(ctx, task, cluster, reason, raw_response):
    """
    \b
    # Stop one selected task
    cmd::ecsctl stop 3bbf655e-66db-479b-a05a-b6c434d882dc

    \b
    # Stop one selected task witch save reason why you stop task.
    cmd::ecsctl stop 3bbf655e-66db-479b-a05a-b6c434d882dc --reason "Stopped because we reduce cost"

    \b
    # Stop one selected task with show raw response
    cmd::ecsctl stop 3bbf655e-66db-479b-a05a-b6c434d882dc --raw-response
    """
    if not cluster:
        cluster = ctx.obj['cluster']
    bw = ctx.obj['bw']
    resp = bw.stop_task(task, cluster=cluster, reason=reason)
    if raw_response:
        click.echo(display.de_unicode(resp['task']))
    else:
        click.echo(resp['task']['taskArn'])
