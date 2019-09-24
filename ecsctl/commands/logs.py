import click

from ..colorize import HelpColorsGroup


@click.group(cls=HelpColorsGroup, name='logs', short_help='Print the logs for a container usage CloudWatch.', invoke_without_command=True)
@click.argument('task', required=True)
@click.option('--container',
              help="Select one container from selected task.")
@click.option('--start-time', type=click.DateTime(formats=None),
              help="Select start time when you need show logs.")
@click.option('--end-time', type=click.DateTime(formats=None),
              help="Select end time when you need show logs.")
@click.option('--filter',
              help="Filter logs usage AWS filter and pattern syntax. You can find more details in "
                   "https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/FilterAndPatternSyntax.html")
@click.option('--byte-size', type=int, default=1024, show_default=True,
              help="Defind maximum size logs in bytes if you don't specify time.")
@click.option('-c', '--cluster',
              help="Specify cluster to execute command. Default usage cluster from context.")
@click.pass_context
def logs(ctx, task, *args, **kwargs):
    """
    \b
    # Show logs from one selected task
    cmd::ecsctl logs 41ff5a8d-56ed-431f-8d2a-f056826b7cde

    \b
    # Show logs from one selected task between selected time
    cmd::ecsctl logs 41ff5a8d-56ed-431f-8d2a-f056826b7cde --start 2019-09-07T19:00:00 --end 2019-09-07T22:00:00

    \b
    # Show logs from one selected task between selected time and selected container
    cmd::ecsctl logs 41ff5a8d-56ed-431f-8d2a-f056826b7cde -c gunicorn --start 2019-09-07T19:00:00 --end 2019-09-07T22:00:00

    \b
    # Show logs from one selected task between selected time and selected container and filter response
    cmd::ecsctl logs 41ff5a8d-56ed-431f-8d2a-f056826b7cde -c gunicorn --start 2019-09-07T19:00:00 --end 2019-09-07T22:00:00 --filter "ERRORCODE: -1"
    """
    cluster = kwargs.pop('cluster', None)
    if not cluster:
        cluster = ctx.obj['cluster']

    bw = ctx.obj['bw']
    resp, err = bw.logs(task, cluster, *args, **kwargs)

    if err:
        click.echo(click.style(resp, fg='red'))
    else:
        click.echo(resp)
