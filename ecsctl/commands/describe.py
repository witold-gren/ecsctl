import pytz
import click
import datetime
import humanize
import tabulate
import pprint

from ..alias import AliasedGroup
from .. import wrapboto, display


@click.group(cls=AliasedGroup, short_help='Show details of a specific resource.')
def describe():
    pass


@describe.command(name='cluster')
@click.argument('cluster', required=False)
@click.option('-o', '--output', type=click.Choice(['json', 'yaml']), default='json', show_default=True,
              help="Output format.")
@click.pass_context
def describe_cluster(ctx, cluster, output):
    """
    \b
    # Describe cluster
    cmd::ecsctl describe cluster my-custer

    \b
    # Describe cluster usage yaml output
    cmd::ecsctl describe cluster my-custer -o yaml
    """
    if not cluster:
        cluster = ctx.obj['cluster']
    bw = ctx.obj['bw']
    cluster_resp = bw.describe_cluster(cluster)
    if output == 'yaml':
        cluster_resp = bw.convert_to_yaml(cluster_resp)
    elif output == 'json':
        cluster_resp = display.de_unicode(cluster_resp)
    click.echo(cluster_resp)


@describe.command(name='container-instance')
@click.argument('node', required=True)
@click.option('-o', '--output', type=click.Choice(['json', 'yaml']), default='json', show_default=True,
              help="Output format.")
@click.option('-c', '--cluster',
              help="Specify cluster to execute command. Default usage cluster from context.")
@click.pass_context
def describe_node(ctx, node, output, cluster):
    """
    \b
    # Describe container instance
    cmd::ecsctl describe container-instance 4f58fecf-92a0-4b78-bd3a-4d8e2f35fc14

    \b
    # Describe container instance usage yaml output
    cmd::ecsctl describe container-instance 4f58fecf-92a0-4b78-bd3a-4d8e2f35fc14 -o yaml
    """
    if not cluster:
        cluster = ctx.obj['cluster']
    bw = ctx.obj['bw']
    node_resp, err = bw.describe_container_instance(node, output, cluster=cluster)
    if err:
        node_resp = click.style(node_resp, fg='red')
    else:
        if output == 'yaml':
            node_resp = bw.convert_to_yaml(node_resp)
        elif output == 'json':
            node_resp = display.de_unicode(node_resp)
    click.echo(node_resp)


@describe.command(name='task-definition')
@click.argument('task-definition', required=True)
@click.option('--export', is_flag=True, default=False,
              help="Get data without cluster information.")
@click.option('-o', '--output', type=click.Choice(['json', 'yaml']), default='json', show_default=True,
              help="Output format.")
@click.option('-c', '--cluster',
              help="Specify cluster to execute command. Default usage cluster from context.")
@click.pass_context
def describe_task_definitions(ctx, task_definition, export, output, cluster):
    """
    \b
    # Describe task definition
    cmd::ecsctl describe task-definition my-app:1

    \b
    # Describe container instance usage yaml output
    cmd::ecsctl describe container-instance my-app:1 -o yaml

    \b
    # Describe container instance usage yaml output and without cluster specific data
    cmd::ecsctl describe container-instance my-app:1 -o yaml --export
    """
    if not cluster:
        cluster = ctx.obj['cluster']
    bw = ctx.obj['bw']

    task_definition_resp = bw.describe_task_definition(task_definition, cluster=cluster, tags=export)
    if export:
        task_definition_resp, tags = task_definition_resp
        task_definition_resp = bw.strip_task_def_data(task_definition_resp)
    if output == 'yaml':
        if export:
            task_definition_resp['tags'] = tags
        task_definition_resp = bw.describe_object(task_definition_resp, export, 'TaskDefinition')
        task_definition_resp = bw.convert_to_yaml(task_definition_resp)
    elif output == 'json':
        task_definition_resp = display.de_unicode(task_definition_resp)
    click.echo(task_definition_resp)


@describe.command(name='service')
@click.argument('service', required=True)
@click.option('--events', is_flag=True, default=False,
              help="The event stream for your service.")
@click.option('--export', is_flag=True, default=False,
              help="Get data without cluster information.")
@click.option('-o', '--output', type=click.Choice(['json', 'yaml']), default='json', show_default=True,
              help="Output format.")
@click.option('-c', '--cluster',
              help="Specify cluster to execute command. Default usage cluster from context.")
@click.pass_context
def describe_services(ctx, service, export, events, output, cluster):
    """
    \b
    # Describe service
    cmd::ecsctl describe service my-app

    \b
    # Describe all events from selected service
    cmd::ecsctl describe service my-app --events

    \b
    # Describe service usage yaml output
    cmd::ecsctl describe service my-app -o yaml

    \b
    # Describe service usage yaml output and without cluster specific data
    cmd::ecsctl describe service my-app -o yaml --export
    """
    if not cluster:
        cluster = ctx.obj['cluster']
    bw = ctx.obj['bw']
    service_resp = bw.describe_service(cluster=cluster, service=service)
    if events:
        events = sorted(service_resp.get('events', []), key=lambda k: k.get('createdAt'))
        for event in events:
            _created_at = '\033[93m{}\033[0m '.format(event.get('createdAt').strftime('%Y-%m-%d %H:%M:%S'))
            _message = event.get('message')
            click.echo('{}{}'.format(_created_at, _message))
    else:
        if export:
            service_resp = bw.strip_service_data(service_resp)
        if output == 'yaml':
            service_resp = bw.describe_object(service_resp, export, 'Service')
            service_resp = bw.convert_to_yaml(service_resp)
        elif output == 'json':
            service_resp = display.de_unicode(service_resp)
        click.echo(service_resp)


@describe.command(name='task')
@click.argument('task', required=True)
@click.option('--stopped-reason', is_flag=True, default=False,
              help="The reason that the task was stopped.")
@click.option('--export', is_flag=True, default=False,
              help="Get data without cluster information.")
@click.option('-o', '--output', type=click.Choice(['json', 'yaml']), default='json', show_default=True,
              help="Output format.")
@click.option('-c', '--cluster',
              help="Specify cluster to execute command. Default usage cluster from context.")
@click.pass_context
def describe_tasks(ctx, task, export, output, stopped_reason, cluster):
    """
    \b
    # Describe running task
    cmd::ecsctl describe task e67dbf9d-5f04-4ae0-894c-2eb2a7be5e19

    \b
    # Get stopped reason from stopped task
    cmd::ecsctl describe task e67dbf9d-5f04-4ae0-894c-2eb2a7be5e19 --stopped-reason

    \b
    # Describe task usage yaml output
    cmd::ecsctl describe task e67dbf9d-5f04-4ae0-894c-2eb2a7be5e19 -o yaml

    \b
    # Describe task usage yaml output and without cluster specific data
    cmd::ecsctl describe task e67dbf9d-5f04-4ae0-894c-2eb2a7be5e19 -o yaml --export
    """
    if not cluster:
        cluster = ctx.obj['cluster']
    bw = ctx.obj['bw']
    task_resp = bw.describe_task(task, cluster=cluster, simple=export)
    if stopped_reason:
        if task_resp.get('desiredStatus') == 'STOPPED':
            click.echo(click.style(task_resp.get('stoppedReason'), fg="red"))
            for c in task_resp.get('containers', []):
                if c.get('exitCode') is not None:
                    click.echo(click.style('Container `{}` had exit code: {}'.format(
                        c.get('name'), c.get('exitCode')), fg="red"))
                if c.get('reason'):
                    click.echo(click.style('Container `{}` stopped reason: {}'.format(
                        c.get('name'), c.get('reason')), fg="red"))
            click.echo(click.style(
                'More details: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/stopped-task-errors.html',
                fg="black"))
    else:
        if export:
            task_resp = bw.strip_task_data(task_resp)
        if output == 'yaml':
            task_resp = bw.describe_object(task_resp, export, 'Task')
            task_resp = bw.convert_to_yaml(task_resp)
        elif output == 'json':
            task_resp = display.de_unicode(task_resp)
        click.echo(task_resp)


@describe.command(name='secret')
@click.argument('task-definition-family', required=True)
@click.option('--export', is_flag=True, default=False,
              help="Get data without cluster information.")
@click.option('-o', '--output', type=click.Choice(['json', 'yaml']), default='json', show_default=True,
              help="Output format.")
@click.option('-c', '--cluster',
              help="Specify cluster to execute command. Default usage cluster from context.")
@click.pass_context
def describe_tasks(ctx, task_definition_family, export, output, cluster):
    """
    \b
    # Describe secret from task definition family
    cmd::ecsctl describe secret my-app

    \b
    # Describe secret from task definition family -o yaml
    cmd::ecsctl describe secret my-app -o yaml

    \b
    # Describe secret from task definition family -o yaml
    cmd::ecsctl describe secret my-app -o yaml --export
    """
    if not cluster:
        cluster = ctx.obj['cluster']
    bw = ctx.obj['bw']
    task_resp = bw.describe_secret(task_definition_family, cluster=cluster, simple=export)
    if export:
        task_resp = bw.strip_task_data(task_resp)
    if output == 'yaml':
        task_resp = bw.describe_object(task_resp, export, 'Secret')
        task_resp = bw.convert_to_yaml(task_resp)
    elif output == 'json':
        task_resp = display.de_unicode(task_resp)
    click.echo(task_resp)


@describe.command(name='service-discovery', help="Show services from service discovery namespace")
@click.argument('service-discovery', required=True)
@click.option('-o', '--output', type=click.Choice(['json', 'tab']), default='tab', show_default=True,
              help="Output format.")
@click.pass_context
def describe_service_discovery(ctx, service_discovery, output):
    """
    \b
    # Show count of variables in all task definitions.
    cmd::ecsctl get service-discovery
    """
    bw = ctx.obj['bw']
    now = datetime.datetime.now(pytz.utc)
    records = bw.describe_service_discovery(service_discovery)
    out = []
    if output == 'json':
        resp = display.de_unicode(records)
    elif output == 'tab':
        for service in records:
            dns = []
            for x in service.get('DnsConfig').get('DnsRecords'):
                dns.append(x.get('Type'))
            out.append([
                service.get('Id'),
                service.get('Name'),
                service.get('DnsConfig').get('RoutingPolicy'),
                ','.join(dns),
                humanize.naturaltime(now - service.get('CreateDate'))
            ])
        headers = ['ID', 'NAME', 'ROUTING POLICY', 'DNS RECORDS TYPE', 'AGE']
        resp = tabulate.tabulate(out, headers=headers, tablefmt='plain')
    click.echo(resp)
