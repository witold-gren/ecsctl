import click

from ..alias import AliasedGroup


def get_value(found_elements, kind):
    try:
        return found_elements[0].value
    except IndexError:
        raise ValueError('`{}` - this value doesn\'t exist.'.format(kind))


@click.group(cls=AliasedGroup, short_help='Create resources.')
@click.pass_context
def create(ctx, **kwargs):
    pass


@create.command(name='task-definition')
@click.argument('name', required=True)
@click.option('--task-role', default=None, help="eg. `arn:aws:iam::123456789:role/ROLE_NAME`")
@click.option('--task-execution-role', default=None, help="eg. `arn:aws:iam::123456789:role/ROLE_NAME`")
@click.option('--network-mode', default='bridge', show_default=True, type=click.Choice(['bridge', 'host', 'awsvpc', 'none']), help="eg. `awsvpc`")
@click.option('--launch-type', default='EC2', show_default=True, required=False, type=click.Choice(['EC2', 'FARGATE']), help="eg. `EC2`")
@click.option('--cpu', default=None, help="eg. `256` [0.25 vCPU]")
@click.option('--memory', default=None, help="eg. `512` [512 MiB]")
@click.option('--constraints', default=None, multiple=True, help="eg. `attribute:ecs.instance-type =~ t2.*`")
@click.option('--tags', default=None, multiple=True, help="key1=value1")
@click.option('--pid-mode', type=click.Choice(['host', 'task']), help="eg. `task`")
@click.option('--ipc-mode', type=click.Choice(['host', 'task', 'none']), help="eg. `task`")
@click.option('--volume-names', default=None, multiple=True, help="eg. `volume-1`")
@click.option('--volume-host-paths', default=None, multiple=True, help="eg. `/ecs/webdata`")
@click.option('--volume-scopes', default=None, multiple=True, type=click.Choice(['shared', 'task']), help="eg. `task`")
@click.option('--volume-autoprovisions', default=False, multiple=True, type=click.Choice(['true', 'false']), help="eg. `true`")
@click.option('--volume-drivers', default=None, multiple=True, help="eg. `rexray/bs`")
@click.option('--volume-driver-options', default=None, multiple=True, help="eg. `volumetype=gp2,size=5`")       # for split usage `,`
@click.option('--volume-driver-labels', default=None, multiple=True, help="eg. `label1=value1,label2=value2`")  # for split usage `,`
@click.option('--container-names', multiple=True, default=None)
@click.option('--container-images', multiple=True, default=None)
@click.option('--container-private-repo', multiple=True, default=None)
@click.option('--container-repo-auths', multiple=True, default=None)
@click.option('--container-memory', '--container-memory-hard-limit', 'container_memory', multiple=True, default=None)
@click.option('--container-memory-reservation', '--container-memory-soft-limit', 'container_memory_reservation', multiple=True, default=None)
@click.option('--container-cpus', multiple=True, default=None)
@click.option('--container-gpus', multiple=True, default=None)
@click.option('--container-essentials', multiple=True, type=click.Choice(['true', 'false']), default=None)
@click.option('--container-entrypoints', multiple=True, default=None)
@click.option('--container-commands', multiple=True, default=None)
@click.option('--container-directories', multiple=True, default=None)
@click.option('--container-env-variables', multiple=True, default=None)
@click.option('--container-ports', default=None, multiple=True, help="eg. `tcp=8000:80,udp=5432:5432`")
@click.option('--container-start-timeouts', multiple=True, type=int, default=None)
@click.option('--container-stop-timeouts', multiple=True, type=int, default=None)
@click.option('--container-disable-networkings', multiple=True, type=click.Choice(['true', 'false']), default=None)
@click.option('--container-links', multiple=True, default=None)
@click.option('--container-hostnames', multiple=True, default=None)
@click.option('--container-dns-servers', multiple=True, default=None)
@click.option('--container-dns-searchs', multiple=True, default=None)
@click.option('--container-extra-hosts', multiple=True, default=None)
@click.option('--container-read-root', multiple=True, default=None)
@click.option('--container-mount-points', multiple=True, default=None)
@click.option('--container-volumes-from', multiple=True, default=None)
@click.option('--container-log-configuration', multiple=True, type=click.Choice(['true', 'false']), default=None)
@click.option('--container-log-drivers', multiple=True, type=click.Choice(['awslog', 'fluentd', 'gelf', 'journald', 'json-file', 'logentries', 'splunk', 'sumologic', 'syslog']), default=None)
@click.option('--container-log-options', multiple=True, default=None)
@click.option('--container-log-secret', multiple=True, default=None)
@click.option('--container-privileged', multiple=True, type=click.Choice(['true', 'false']), default=None)
@click.option('--container-user', multiple=True, default=None)
@click.option('--container-security-options', multiple=True, default=None)
@click.option('--container-resource-limits', multiple=True, default=None, help="eg. `core:10:20,cpu:20:10`")
@click.option('--container-docker-labels', multiple=True, default=None)
@click.option('--container-interactive', multiple=True, default=None)
@click.option('--container-pseudo-terminal', multiple=True, default=None)
@click.option('--container-depends-on', multiple=True, default=None)
@click.pass_context
def create_task_definition(ctx, name, *args, **kwargs):
    """
    \b
    TODO: Describe how to create task definition usage command line

    \b
    # Create task definition
    cmd::ecsctl create task-definition ...
    """
    bw = ctx.obj['bw']
    resp, err = bw.create_task_definition(name, *args, **kwargs)
    if err:
        click.echo(click.style(resp, fg='red'))
    else:
        click.echo(resp['taskDefinition']['taskDefinitionArn'])


@create.command(name='service')
@click.argument('name', required=True)
@click.option('--task-definition', default=None)
@click.option('--desired-count', default=None)
@click.option('--client-token', default=None)
@click.option('--launch-type', default='EC2', show_default=True, type=click.Choice(['EC2', 'FARGATE']))
@click.option('--platform-version', default=None)
@click.option('--role', default=None)
@click.option('--health-check', default=None)
@click.option('--scheduling-strategy', default='REPLICA', show_default=True, type=click.Choice(['REPLICA', 'DAEMON']))
@click.option('--enable-ecs-managed-tags', default=None, is_flag=True)
@click.option('--propagate-tags', default=None, type=click.Choice(['TASK_DEFINITION', 'SERVICE']))
@click.option('--tags', default=None, help="key1=value1")
@click.option('--deployment-controller', default='ECS', type=click.Choice(['ECS', 'CODE_DEPLOY', 'EXTERNAL']))
@click.option('--deployment-conf-max', default=None, type=int, help="deploymentConfiguration-maximumPercent")
@click.option('--deployment-conf-min', default=None, type=int, help="deploymentConfiguration-minimumHealthyPercent")
@click.option('--constraints', default=None, help="eg. `attribute:ecs.instance-type =~ t2.*`")
@click.option('--strategies', default=None, help="spread=attribute:ecs.availability-zone")
@click.option('--service-registries-arn', multiple=True, default=None)
@click.option('--service-registries-port', multiple=True, default=None)
@click.option('--service-registries-container-name', multiple=True, default=None)
@click.option('--service-registries-container-port', multiple=True, default=None)
@click.option('--load-balancers-target-group-arn', multiple=True, default=None)
@click.option('--load-balancers-name', multiple=True, default=None)
@click.option('--load-balancers-container-name', multiple=True, default=None)
@click.option('--load-balancers-container-port', multiple=True, default=None)
@click.option('--awsvpc-subnets', default=None)
@click.option('--awsvpc-security-groups', default=None)
@click.option('--awsvpc-assign-public-ip', default='DISABLED', type=click.Choice(["ENABLED", "DISABLED"]))
@click.pass_context
def create_service(ctx, name, *args, **kwargs):
    """
    \b
    TODO: Describe how to create service usage command line

    \b
    # Create service
    cmd::ecsctl create service ...
    """
    bw = ctx.obj['bw']
    resp, err = bw.create_service(name, *args, **kwargs)
    if err:
        click.echo(click.style(resp, fg='red'))
    else:
        click.echo(resp['clusterArn'])


@create.command(name='secret')
@click.argument('name', required=True)
@click.pass_context
def create_secret(ctx, name):
    """
    \b
    TODO: Describe how to create secret usage command line

    \b
    # Create secret
    cmd::ecsctl create secret ...
    """
    bw = ctx.obj['bw']
    raise NotImplementedError


@create.command(name='loadbalancer')
@click.argument('name', required=True)
@click.pass_context
def create_loadbalancer(ctx, name):
    """
    \b
    TODO: Describe how to create load-balancer usage command line

    \b
    # Create load balancer
    cmd::ecsctl create loadbalancer ...
    """
    bw = ctx.obj['bw']
    raise NotImplementedError


@create.command(name='autoscaling')
@click.argument('service', required=True)
@click.pass_context
def create_autoscaling(ctx, service):
    """
    \b
    TODO: Describe how to create auto scaling usage command line

    \b
    # Create auto scaling
    cmd::ecsctl create autoscaling ...
    """
    bw = ctx.obj['bw']
    raise NotImplementedError
