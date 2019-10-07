import pytz
import click
import pprint
import tabulate
import datetime
import humanize
from jsonpath_ng import parse

from ..alias import AliasedGroup
from .. import wrapboto, display


TASK_DEFINITION_STATUS = ['ACTIVE', 'INACTIVE', 'ALL']
TASK_STATUS = ['RUNNING', 'PENDING', 'STOPPED']


@click.group(cls=AliasedGroup, short_help='Display one or many resources.')
def get():
    pass


@get.command(name='cluster', short_help="List cluster from your account.")
@click.option('--quiet', is_flag=True,
              help="Only display name of cluster.")
@click.option('--sort-by',
              help="Sort list types using this field specification. The field specification is expressed"
                   "as a JSONPath expression (e.g. 'settings[*].disabled')")
@click.pass_context
def get_clusters(ctx, quiet, sort_by):
    """
    \b
    # Get list cluster configured with your AWS account
    cmd::ecsctl get cluster

    \b
    # Get list cluster and sort by name
    cmd::ecsctl get cluster --sort-by "settings[0].name"

    \b
    # Show only name od cluster
    cmd::ecsctl get cluster --quiet
    """
    bw = ctx.obj['bw']
    records = bw.get_clusters()
    if sort_by:
        records.sort(key=lambda r: parse(sort_by).find(r)[0].value)
    out = []
    for r in records:
        status = r['status']
        name = r['clusterName']
        running_count = r['runningTasksCount']
        pending_count = r['pendingTasksCount']
        instance_count = r['registeredContainerInstancesCount']
        row = (name,)
        if not quiet:
            row = (name, status, running_count, pending_count, instance_count)
        out.append(row)

    headers = []
    if not quiet:
        headers = ['NAME', 'STATUS', 'RUNNING', 'PENDING', 'INSTANCE COUNT']

    output = tabulate.tabulate(out, headers=headers, tablefmt='plain')
    click.echo(output)


@get.command(name='service', short_help="List services from your cluster.")
@click.option('--quiet', is_flag=True,
              help="Only display name of service.")
@click.option('--sort-by',
              help="Sort list types using this field specification. The field specification is expressed"
                   "as a JSONPath expression (e.g. 'deployments[*].status')")
@click.option('-c', '--cluster',
              help="Specify cluster to execute command. Default usage cluster from context.")
@click.pass_context
def get_services(ctx, quiet, sort_by, cluster):
    """
    \b
    # Get list of services provision in default cluster
    cmd::ecsctl get service

    \b
    # Get only names of services list
    cmd::ecsctl get service --quiet

    \b
    # Get list of services and sort by deployment status
    cmd::ecsctl get service --sort-by "deployments[*].status"

    \b
    # Get list of services and sort by creation date
    cmd::ecsctl get service --sort-by "createdAt"

    \b
    # Get list of services and sort by numbers of running task
    cmd::ecsctl get service --sort-by "runningCount"
    """
    if not cluster:
        cluster = ctx.obj['cluster']
    bw = ctx.obj['bw']
    records = bw.get_services(cluster=cluster)
    if sort_by:
        records.sort(key=lambda r: parse(sort_by).find(r)[0].value)
    out = []
    now = datetime.datetime.now(pytz.utc)
    for r in records:
        service_name = r['serviceName']
        task_def = display.simple_task_definition(r['taskDefinition'])
        status = r['status']
        created_at = r['createdAt']
        desired_count = r['desiredCount']
        running_count = r['runningCount']
        age = humanize.naturaltime(now - created_at)
        row = (service_name,)
        if not quiet:
            row = (service_name, task_def, desired_count, running_count, status, age)
        out.append(row)
    headers = []
    if not quiet:
        headers = ['NAME', 'TASK DEFINITION', 'DESIRED', 'RUNNING', 'STATUS', 'AGE']
    output = tabulate.tabulate(out, headers=headers, tablefmt='plain')
    click.echo(output)


@get.command(name='container-instance', short_help="List container instances from your cluster.")
@click.option('--quiet', is_flag=True, help="Only display ID of container instance.")
@click.option('--sort-by',
              help="Sort list types using this field specification. The field specification is expressed"
                   "as a JSONPath expression (e.g. 'deployments[*].status')")
@click.option('-o', '--output', type=click.Choice(['wide']),
              help="Output format.")
@click.option('-c', '--cluster',
              help="Specify cluster to execute command. Default usage cluster from context.")
@click.pass_context
def get_container_instance(ctx, cluster, quiet, sort_by, output):
    """
    \b
    # Get list of container instances
    cmd::ecsctl get container-instance --quiet

    \b
    # Get list of container instances with extended information
    cmd::ecsctl get container-instance -o wide

    \b
    # Get list of container instances and sort by agent version
    cmd::ecsctl get container-instance --sort-by "versionInfo.agentVersion"

    \b
    # Get list of container instances and sort by running tasks count
    cmd::ecsctl get container-instance --sort-by "runningTasksCount"

    \b
    # Get list of container instances and sort by type instance
    cmd::ecsctl get container-instance --sort-by "ec2_data.InstanceLifecycle"

    \b
    # Get list of container instances and sort by registered CPU
    cmd::ecsctl get container-instance --sort-by "registeredResources[0].integerValue"

    \b
    # Get list of container instances and sort by registered MEMORY
    cmd::ecsctl get container-instance --sort-by "registeredResources[1].integerValue"
    """
    if not cluster:
        cluster = ctx.obj['cluster']
    bw = ctx.obj['bw']
    records = bw.get_container_instances(cluster=cluster)
    if sort_by:
        records.sort(key=lambda r: parse(sort_by).find(r)[0].value)
    out = []
    for r in records:
        status = r['status']
        ec2_instance_id = r['ec2InstanceId']
        container_instance_arn = r['containerInstanceArn']
        instance_id = display.simple_container_instance(container_instance_arn)
        running_count = r['runningTasksCount']
        private_ip = r['ec2_data']['PrivateIpAddress']
        row = (instance_id,)
        if not quiet:
            row = [instance_id, ec2_instance_id, status, private_ip, running_count]
            if output == 'wide':
                row.append(r['ec2_data'].get('PublicIpAddress', 'none'))
        out.append(row)

    headers = []
    if not quiet:
        headers = ['INSTANCE ID', 'EC2 INSTANCE ID', 'STATUS', 'PRIVATE IP', 'RUNNING COUNT']
        if output == 'wide':
            headers.append('PUBLIC IP')
    output = tabulate.tabulate(out, headers=headers, tablefmt='plain')
    click.echo(output)


@get.command(name='task', short_help="List task from your cluster.")
@click.option('--status', type=click.Choice(TASK_STATUS), default='RUNNING',
              help="Filter task usage status.")
@click.option('--items', type=int,
              help="Set numbers of items to display.")
@click.option('--quiet', is_flag=True,
              help="Only display numeric IDs")
@click.option('--sort-by',
              help="Sort list types using this field specification. The field specification is expressed"
                   "as a JSONPath expression (e.g. 'deployments[*].status')")
@click.option('--jsonpath', 'json_path', multiple=True,
              help="Filter data from json response and create new column.")
@click.option('-o', '--output', type=click.Choice(['wide']),
              help="Output format.")
@click.option('-c', '--cluster',
              help="Specify cluster to execute command. Default usage cluster from context.")
#@click.option('--filter', 'filter_val', multiple=True)
@click.pass_context
def get_task(ctx, cluster, sort_by, status, items, quiet, json_path, output):  # filter_val=None
    """
    \b
    # Show all running tasks.
    cmd::ecsctl get task

    \b
    # Show all running tasks with extra information.
    cmd::ecsctl get task --o wide

    \b
    # Show only ID of running tasks.
    cmd::ecsctl get task --quiet

    \b
    # Show task with status stopped and order by stopped time.
    cmd::ecsctl get task --status STOPPED --sort-by "stoppedAt"

    \b
    # Show last 10 task with status stopped and order by stopped time.
    cmd::ecsctl get task --status STOPPED --sort-by "stoppedAt" --items 10

    \b
    # Get all running task and create custom clumn: taks name and memory reservation.
    cmd::ecsctl get task --jsonpath "[*].containers[0].name" --jsonpath "[*].cpu" --jsonpath "[*].memory"
    """
    # TODO: ecsctl get po --filter "TASK_ID=~'.*'" --filter "STATUS=ACTIVE"
    #  =   : Select labels that are exactly equal to the provided string.
    #  !=  : Select labels that are not equal to the provided string.
    #  =~  : Select labels that regex-match the provided string.
    #  ~   : Select labels that do not regex-match the provided string.
    #  eg:
    #  environment=~"staging|testing|development"
    #  job=~".*"

    headers, out, instances = [], [], {}
    if not cluster:
        cluster = ctx.obj['cluster']
    bw = ctx.obj['bw']
    records = bw.get_tasks(cluster=cluster, status=status)
    if sort_by and records:
        records.sort(key=lambda r: parse(sort_by).find(r)[0].value)
    if json_path:
        for _jp in json_path:
            h = None
            jsonpath_expr = parse(_jp)
            for x, match in enumerate(jsonpath_expr.find(records)):
                try:
                    out[x].append(match.value)
                except IndexError:
                    out.append([match.value])
                h = str(match.path)
            headers.append(h)
        # if filter_val:
        #     raise ValueError
    else:
        now = datetime.datetime.now(pytz.utc)
        for inst in bw.get_container_instances(cluster=cluster):
            instances[inst['containerInstanceArn']] = inst
        for x, r in enumerate(records):
            status = r['lastStatus']
            created_at = r['createdAt']
            task_id = display.simple_task(r['taskArn'])
            task_def = display.simple_task_definition(r['taskDefinitionArn'])
            age = humanize.naturaltime(now - created_at)
            instance = instances[r['containerInstanceArn']]['ec2_data']['PrivateIpAddress']
            containers = ' | '.join([x['name'] for x in r['containers']])
            ports = []
            for c in r.get('containers', []):
                for port in c.get('networkBindings', []):
                    p = '{}{}->{}/{}'.format(
                        ':{}'.format(port.get('bindIP')) if not port.get('bindIP') == '0.0.0.0' else '0:',
                        port.get('hostPort'),
                        port.get('containerPort'),
                        port.get('protocol'))
                    ports.append(p)
            if output:
                info = bw.describe_task_definition(r['taskDefinitionArn'], cluster=cluster)
                c, l = [], []

                for td in info['containerDefinitions']:
                    c.append(td['name'])
                    log_config = td.get('logConfiguration', {})
                    if log_config.get('logDriver', {}) == 'awslogs':
                        options = log_config.get('options')
                        if options.get('awslogs-group') and \
                                options.get('awslogs-region') and \
                                options.get('awslogs-stream-prefix'):
                            l.append('awslogs')
                        else:
                            l.append('none')
                    else:
                        l.append('none')
                logs, containers = ' | '.join(l), ' | '.join(c)

            row = [task_id, status, containers, '\n'.join(ports), task_def, age, instance]
            if output:
                row.append(logs)
            # if filter_val:
            #     raise ValueError
            if quiet:
                row = [row[0]]
            out.append(row)

        if items:
            out = out[-items:]

        if not quiet:
            headers = ['TASK ID', 'STATUS', 'CONTAINERS', 'PORTS', 'TASK DEFINITION', 'AGE', 'EC2 PRIVATE IP', 'LOGS']
    output = tabulate.tabulate(out, headers=headers, tablefmt='plain')
    click.echo(output)


@get.command(name='task-definition-family', short_help="List task definition family from your cluster.")
@click.option('--family-prefix', default=None,
              help="Filter task definition family usage prefix name.")
@click.option('--status', type=click.Choice(TASK_DEFINITION_STATUS), default='ACTIVE', show_default=True,
              help="Filter task definition family usage status.")
@click.pass_context
def get_task_definition_family(ctx, status, family_prefix):
    """
    \b
    # Show all active task definition family.
    cmd::ecsctl get task-definition-family

    \b
    # Show all active task defunition family with filter name.
    cmd::ecsctl get task-definition-family --family-prefix my-app

    \b
    # Show all inactive task defunition family.
    cmd::ecsctl get task-definition-family --status INACTIVE
    """
    bw = ctx.obj['bw']
    records = bw.all_task_definition_families(
        family_prefix=family_prefix,
        status=status,
    )
    out = []
    for r in records:
        familly_name = r[0]
        last_task = r[1]
        count = r[2]
        row = (familly_name, count, last_task, status)
        out.append(row)
    headers = ['TASK FAMILLY NAME', 'REVISIONS', 'LAST TASK DEFINITION', 'STATUS', ]
    output = tabulate.tabulate(out, headers=headers, tablefmt='plain')
    click.echo(output)


@get.command(name='task-definition', short_help="List task definition from your cluster.")
@click.option('--family-prefix', default=None,
              help="Filter task definition usage prefix name.")
@click.option('--status', type=click.Choice(TASK_DEFINITION_STATUS), default='ACTIVE', show_default=True,
              help="Filter task definition usage status.")
@click.pass_context
def get_task_definition(ctx, status, family_prefix):
    """
    \b
    # Show all active task defunition.
    cmd::ecsctl get task-definition

    \b
    # Filter all active task definition usage prefix name.
    cmd::ecsctl get task-definition --family-prefix my-app

    \b
    # Show all inactive task definition.
    cmd::ecsctl get task-definition --status INACTIVE
    """
    bw = ctx.obj['bw']
    records = bw.all_task_definitions(
        family_prefix=family_prefix,
        status=status,
    )
    for r in records:
        out = display.simple_task_definition(r)
        click.echo(out)


@get.command(name='secret', short_help="List secret group from your account.")
@click.option('--family-prefix', default=None,
              help="Filter task definition usage prefix name.")
@click.option('--variables', is_flag=True, default=False,
              help="Show variables from one task definition family.")
@click.option('-o', '--output', type=click.Choice(['wide']),
              help="Output format.")
@click.option('-c', '--cluster',
              help="Specify cluster to execute command. Default usage cluster from context.")
@click.pass_context
def get_secret(ctx, family_prefix, variables, output, cluster):
    """
    \b
    # Show count of variables in all task definitions.
    cmd::ecsctl get secret

    \b
    # Count variables for selected task definition family.
    cmd::ecsctl get secret --family-prefix my-app

    \b
    # Show all variables.
    cmd::ecsctl get secret --variables

    \b
    # Show all variables with extra information.
    cmd::ecsctl get secret --variables -o wide
    """
    now = datetime.datetime.now(pytz.utc)
    bw = ctx.obj['bw']
    if not cluster:
        cluster = ctx.obj['cluster']
    records = bw.all_secret(cluster=cluster, family_prefix=family_prefix, variables=variables)
    out = []
    for r in records:
        first_col = r[0]
        second_col = r[1]
        third_col = r[2]
        row = (first_col, second_col, third_col)
        if variables:
            third_col = humanize.naturaltime(now - third_col)
            try:
                _, app, name = first_col.split('.')
            except Exception as e:
                name = first_col
            row = [name, app, second_col, third_col]
            if output:
                row.append(first_col)
        out.append(row)
    headers = ['CLUSTER', 'TASK DEFINITION FAMILLY', 'COUNT']
    if variables:
        headers = ['NAME', 'TASK DEFINITION FAMILY', 'VERSION', 'LAST MODIFIED']
        if output:
            headers.append('PARAMETER STORE NAME')
    output = tabulate.tabulate(out, headers=headers, tablefmt='plain')
    click.echo(output)


@get.command(name='service-discovery', short_help="List service discovery namespace from your account.")
@click.pass_context
def get_service_discovery(ctx):
    """
    \b
    # Show all service-discovery
    cmd::ecsctl get service-discovery
    """
    now = datetime.datetime.now(pytz.utc)
    bw = ctx.obj['bw']
    records = bw.all_service_discovery()
    out = []
    for r in records:
        out.append((r.get('Id'), r.get('Name'), r.get('Type'), humanize.naturaltime(now - r.get('CreateDate'))))
    headers = ['ID SERVICE DISCOVERY', 'NAME', 'TYPE', 'AGE']
    output = tabulate.tabulate(out, headers=headers, tablefmt='plain')
    click.echo(output)


@get.command(name='loadbalancer', short_help="List load balancer from your account.")
@click.option('--arn', is_flag=True, default=False,
              help="Output format.")
@click.pass_context
def get_load_balancer(ctx, arn):
    """
    \b
    # Show all load-balancer
    cmd::ecsctl get loadbalancer

    \b
    # Show all load-balancer arn and canonical hosted zone id
    cmd::ecsctl get loadbalancer --arn
    """
    now = datetime.datetime.now(pytz.utc)
    bw = ctx.obj['bw']
    records = bw.all_load_balancer()
    out = []
    for r in records:
        if arn:
            data = [r.get('LoadBalancerName'), r.get('LoadBalancerArn'), r.get('CanonicalHostedZoneId')]
        else:
            data = [
                r.get('LoadBalancerName'),
                r.get('Scheme'),
                r.get('DNSName'),
                r.get('Type'),
                humanize.naturaltime(now - r.get('CreatedTime'))
            ]
        out.append(data)
    headers = ['NAME', 'SCHEME', 'DNS NAME', 'TYPE', 'AGE']
    if arn:
        headers = ['NAME', 'LOAD BALANCER ARN', 'HOSTED ZONE ID']
    output = tabulate.tabulate(out, headers=headers, tablefmt='plain')
    click.echo(output)


@get.command(name='hosted-zones', short_help="List hosted zones from your account.")
@click.argument('hosted-zone', required=False)
@click.pass_context
def get_zone(ctx, hosted_zone):
    """
    \b
    # Show all hosted-zones
    cmd::ecsctl get hosted-zones

    \b
    # Show all record from dev.example.com
    cmd::ecsctl get hosted-zones /hostedzone/00000000000000000000
    """
    bw = ctx.obj['bw']
    if not hosted_zone:
        headers = ['ID', 'NAME', 'PRIVATE ZONE', 'RECORD COUNT']
        records = bw.all_hosted_zone()
        out = []
        for r in records:
            data = [
                r.get('Id'),
                r.get('Name'),
                r.get('Config').get('PrivateZone'),
                r.get('ResourceRecordSetCount')
            ]
            out.append(data)
        output = tabulate.tabulate(out, headers=headers, tablefmt='plain')
    else:
        headers = ['NAME', 'TYPE', 'TTL', 'RECORDS']
        records = bw.all_resource_record(hosted_zone)
        out = []
        for item in records:
            if item.get('ResourceRecords'):
                r = [x.get('Value') for x in item.get('ResourceRecords')]
            elif item.get('AliasTarget'):
                r = [item.get('AliasTarget').get('DNSName')]
            out.append([item.get('Name'), item.get('Type'), item.get('TTL'), ','.join(r)])
        output = tabulate.tabulate(out, headers=headers, tablefmt='plain')
    click.echo(output)
