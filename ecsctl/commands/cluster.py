import click
from .. import wrapboto
from ..pty import Pty
from ..colorize import HelpColorsGroup


@click.group(cls=HelpColorsGroup, short_help='Drain container instance.', invoke_without_command=True)
@click.option('--cluster')
@click.argument('node', required=True)
@click.pass_context
def drain(ctx, node, cluster):
    """
    \b
    # Drain container instance for maintenance.
    cmd::ecsctl drain 4f58fecf-92a0-4b78-bd3a-4d8e2f35fc14
    """
    if not cluster:
        cluster = ctx.obj['cluster']
    bw = ctx.obj['bw']
    resp = bw.drain_node(node, cluster=cluster)
    click.echo(resp['containerInstances'][0]['containerInstanceArn'])


@click.group(cls=HelpColorsGroup, short_help='Undrain node back into active status.', invoke_without_command=True)
@click.option('--cluster')
@click.argument('node', required=True)
@click.pass_context
def undrain(ctx, node, cluster):
    """
    \b
    # Undrain container instance for maintenance.
    cmd::ecsctl undrain 4f58fecf-92a0-4b78-bd3a-4d8e2f35fc14
    """
    if not cluster:
        cluster = ctx.obj['cluster']
    bw = ctx.obj['bw']
    resp = bw.undrain_node(node, cluster=cluster)
    click.echo(resp['containerInstances'][0]['containerInstanceArn'])


@click.group(cls=HelpColorsGroup, name='exec', short_help='Execute a command in a container.', invoke_without_command=True)
@click.option('--cluster')
@click.option('-i', '--stdin', is_flag=True, default=False, show_default=True)
@click.option('-t', '--tty', is_flag=True, default=False, show_default=True)
@click.option('-c', '--container', default=None)
@click.option('--ssh-user')
@click.option('--ssh-bastion-user')
@click.option('--ssh-bastion-ip')
@click.option('--ssh-key-location')
@click.argument('task', required=True)
@click.argument('command', nargs=-1)
@click.pass_context
def exec_command(ctx, task, command, stdin, tty, cluster, container,
                 ssh_user, ssh_bastion_user, ssh_bastion_ip, ssh_key_location):
    """
    \b
    # Show date in docker
    cmd::ecsctl exec 78a4d51c-d7ff-439c-91bf-a459482b2c93 date

    \b
    # Connect to first container in task ID
    cmd::ecsctl exec -it 78a4d51c-d7ff-439c-91bf-a459482b2c93 bash

    \b
    # Connect to backend container in task ID
    cmd::ecsctl exec -it -c backend 78a4d51c-d7ff-439c-91bf-a459482b2c93 sh

    \b
    # Connect to backend container in task ID
    cmd::ecsctl exec -it -c backend 78a4d51c-d7ff-439c-91bf-a459482b2c93 sh

    \b
    # Connect to backend container in task ID with ubuntu user
    cmd::ecsctl exec -it --ssh-user ubuntu -c backend 78a4d51c-d7ff-439c-91bf-a459482b2c93 bash

    \b
    # Connect to backend container in task ID with custom ssh key
    cmd::ecsctl exec -it --ssh-key-location ~/.ssh/my-key -c backend 78a4d51c-d7ff-439c-91bf-a459482b2c93 bash

    \b
    # Connect to backend container in task ID with bastion host IP and specific user
    cmd::ecsctl exec -it --ssh-bastion-ip 1.2.3.4 --ssh-bastion-user dev -c backend 78a4d51c-d7ff-439c-91bf-a459482b2c93 bash
    """
    if not cluster:
        cluster = ctx.obj['cluster']
    if not ssh_user:
        ssh_user = ctx.obj['ssh_user']
    if not ssh_bastion_user:
        ssh_bastion_user = ctx.obj['ssh_bastion_user']
    if not ssh_bastion_ip:
        ssh_bastion_ip = ctx.obj['ssh_bastion_ip']
    if not ssh_key_location:
        ssh_key_location = ctx.obj['ssh_key_location']
    bw = ctx.obj['bw']
    pty = Pty(bw=bw, task=task, command=command, cluster=cluster,
              tty=tty, stdin=stdin, container=container,
              ssh_user=ssh_user, ssh_bastion_user=ssh_bastion_user,
              ssh_bastion_ip=ssh_bastion_ip, ssh_key_location=ssh_key_location)
    pty.exec_command()


@click.group(cls=HelpColorsGroup, short_help='Run a particular image on the cluster.', invoke_without_command=True)
@click.argument('command', nargs=-1, required=False)
@click.argument('name')
@click.option('--image', required=True)
@click.option('--cluster')
@click.pass_context
def run(ctx, name, cluster, **kwargs):
    """
    \b
    TODO: Describe how to usage run in command line
    """
    if not kwargs.get('cluster'):
        cluster = ctx.obj['cluster']
    bw = ctx.obj['bw']
    output = bw.run(name=name, cluster=cluster, **kwargs)
    click.echo(output)


@click.group(cls=HelpColorsGroup, short_help='Set a new size for a Service.', invoke_without_command=True)
@click.argument('service', required=True)
@click.option('--cluster')
@click.option('--replicas', type=int, required=True)
@click.pass_context
def scale(ctx, replicas, service, cluster):
    """
    \b
    # Scale service to 3 task
    cmd::ecsctl scale --replicas 2 my-app
    """
    if not cluster:
        cluster = ctx.obj['cluster']
    bw = ctx.obj['bw']
    resp = bw.scale_service(service, replicas, cluster=cluster)
    output = resp['service']['serviceArn']
    click.echo(output)
