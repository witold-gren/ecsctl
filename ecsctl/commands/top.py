import pytz
import click
import datetime
import tabulate

from ..alias import AliasedGroup


@click.group(cls=AliasedGroup, short_help='Display Resource (CPU/Memory) usage.')
def top():
    pass


@top.command(name='cluster')
@click.option('--start-time', type=click.DateTime(formats=None),
              help="Select start time when you need to check usage resources.")
@click.option('--end-time', type=click.DateTime(formats=None),
              help="Select end time when you need to check usage resources.")
@click.option('-c', '--cluster',
              help="Specify cluster to execute command. Default usage cluster from context.")
@click.pass_context
def top_cluster(ctx, cluster, start_time=None, end_time=None):
    """
    \b
    # Show avaraged usage resource from last 30m
    cmd::ecsctl top cluster

    \b
    # Show avaraged usage resource from last 1h (Current we have 20 September 2019 12:35)
    cmd::ecsctl top cluster --start-time 2019-09-20T12:35:00

    \b
    # Show avaraged usage resource from last 1d
    cmd::ecsctl top cluster --start-time 2019-09-20T12:35:00 --end-time 2019-09-19T12:35:00
    """
    if not cluster:
        cluster = ctx.obj['cluster']
    if not end_time:
        end_time = datetime.datetime.now(pytz.utc)
    if not start_time:
        start_time = end_time - datetime.timedelta(minutes=30)
    if start_time > end_time:
        return click.echo(click.style('Start date parameter must be set before end date.', fg='red'))

    bw = ctx.obj['bw']
    out, err = bw.get_cluster_metric_data(cluster, start_time, end_time)
    if err:
        return click.echo(click.style(out, fg='red'))

    headers = ['CLUSTER', 'CPU(percent)', 'MEMORY(percent)']
    output = tabulate.tabulate(out, headers=headers, tablefmt='plain')
    return click.echo(output)


@top.command(name='service')
@click.option('--start-time', type=click.DateTime(formats=None),
              help="Select start time when you need to check usage resources.")
@click.option('--end-time', type=click.DateTime(formats=None),
              help="Select end time when you need to check usage resources.")
@click.option('-c', '--cluster',
              help="Specify cluster to execute command. Default usage cluster from context.")
@click.pass_context
def top_service(ctx, cluster, start_time=None, end_time=None):
    """
    \b
    # Show avaraged usage resource from last 30m
    cmd::ecsctl top service

    \b
    # Show avaraged usage resource from last 1h (Current we have 20 September 2019 12:35)
    cmd::ecsctl top service --start-time 2019-09-20T12:35:00

    \b
    # Show avaraged usage resource from last 1d
    cmd::ecsctl top service --start-time 2019-09-20T12:35:00 --end-time 2019-09-19T12:35:00
    """
    if not cluster:
        cluster = ctx.obj['cluster']
    if not end_time:
        end_time = datetime.datetime.now(pytz.utc)
    if not start_time:
        start_time = end_time - datetime.timedelta(minutes=30)
    if start_time > end_time:
        return click.echo(click.style('Start date parameter must be set before end date.', fg='red'))

    bw = ctx.obj['bw']
    out, err = bw.get_service_metric_data(cluster, start_time, end_time)
    if err:
        return click.echo(click.style(out, fg='red'))

    headers = ['SERVICE', 'CPU(percent)', 'MEMORY(percent)']
    output = tabulate.tabulate(out, headers=headers, tablefmt='plain')
    return click.echo(output)


@top.command(name='container-instance')
@click.option('--start-time', type=click.DateTime(formats=None),
              help="Select start time when you need to check usage resources.")
@click.option('--end-time', type=click.DateTime(formats=None),
              help="Select end time when you need to check usage resources.")
@click.option('-c', '--cluster',
              help="Specify cluster to execute command. Default usage cluster from context.")
@click.pass_context
def top_container_instance(ctx, cluster, start_time=None, end_time=None):
    """
    \b
    # Show avaraged usage resource from last 30m
    cmd::ecsctl top container-instance

    \b
    # Show avaraged usage resource from last 1h (Current we have 20 September 2019 12:35)
    cmd::ecsctl top container-instance --start-time 2019-09-20T12:35:00

    \b
    # Show avaraged usage resource from last 1d
    cmd::ecsctl top container-instance --start-time 2019-09-20T12:35:00 --end-time 2019-09-19T12:35:00
    """
    if not cluster:
        cluster = ctx.obj['cluster']
    if not end_time:
        end_time = datetime.datetime.now(pytz.utc)
    if not start_time:
        start_time = end_time - datetime.timedelta(minutes=5)
    if start_time > end_time:
        return click.echo(click.style('Start date parameter must be set before end date.', fg='red'))

    bw = ctx.obj['bw']
    out, err = bw.get_container_instance_metric_data(cluster, start_time, end_time)
    if err:
        return click.echo(click.style(out, fg='red'))

    headers = ['INSTANCE ID', 'EC2 INSTANCE ID', 'CPU(percent)', 'MEMORY(percent)', 'DISK(percent)', 'SWAP(percent)']
    output = tabulate.tabulate(out, headers=headers, tablefmt='plain')
    return click.echo(output)
