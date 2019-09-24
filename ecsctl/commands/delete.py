import click

from ..alias import AliasedGroup
from .. import wrapboto, display


@click.group(cls=AliasedGroup, short_help='Delete resources.')
def delete():
    pass


@delete.command(name='service')
@click.argument('service', required=True)
@click.option('--force', is_flag=True, default=False, help='Scale down count to 0 before deleting.')
@click.option('-o', '--output', type=click.Choice(['raw']),
              help="Output format.")
@click.option('-c', '--cluster',
              help="Specify cluster to execute command. Default usage cluster from context.")
@click.pass_context
def delete_service(ctx, service, cluster, force, output):
    """
    \b
    # Delete running service my-app if don't have any running task
    cmd::ecsctl delete service my-app

    \b
    # Fore stopping all task and then delete running service
    cmd::ecsctl delete service my-app --force
    """
    if not cluster:
        cluster = ctx.obj['cluster']
    bw = ctx.obj['bw']
    resp, err = bw.delete_service(service, cluster=cluster, force=force)
    if err:
        click.echo(click.style(resp, fg='red'))
    else:
        if output == 'raw':
            click.echo(display.de_unicode(resp['service']))
        else:
            click.echo(resp['service']['serviceArn'])


@delete.command(name='task-definition')
@click.argument('task-definition', required=True)
@click.option('-c', '--cluster',
              help="Specify cluster to execute command. Default usage cluster from context.")
@click.pass_context
def delete_task_definition(ctx, task_definition, cluster):
    """
    \b
    # Delete task definition
    cmd::ecsctl delete task-definition my-app:1
    """
    bw = ctx.obj['bw']
    resp, err = bw.deregister_task_definition(task_definition)
    if err:
        click.echo(click.style(resp, fg='red'))
    else:
        click.echo(resp['taskDefinitionArn'])


@delete.command(name='task-definition-family')
@click.argument('task-definition-family', required=True)
@click.option('-c', '--cluster',
              help="Specify cluster to execute command. Default usage cluster from context.")
@click.pass_context
def delete_task_definition_family(ctx, task_definition_family, cluster):
    """
    \b
    # Delete all task definition and deregister task definition family
    cmd::ecsctl delete task-definition-family my-app
    """
    bw = ctx.obj['bw']
    resp, err = bw.deregister_task_definition_family(task_definition_family)
    if err:
        click.echo(click.style(resp, fg='red'))
    else:
        click.echo('\n'.join(td['taskDefinitionArn'] for td in resp))


@delete.command(name='secret')
@click.argument('task-definition-family', required=True)
@click.option('-e', '--variable-name', multiple=True,
              help="Set one element to delete from parameter store.")
@click.option('-c', '--cluster',
              help="Specify cluster to execute command. Default usage cluster from context.")
@click.pass_context
def delete_task_definition_family(ctx, task_definition_family, variable_name, cluster):
    """
    \b
    # Delete all variables from selected task definition family
    cmd::ecsctl delete secret my-app

    \b
    # Delete one variable from selected task definition family
    cmd::ecsctl delete secret my-app -e SECRET_NAME -e SECRET_NAME_2
    """
    if not cluster:
        cluster = ctx.obj['cluster']
    bw = ctx.obj['bw']
    resp = bw.delete_secret(cluster, task_definition_family, variable_name)
    if resp.get('DeletedParameters'):
        click.echo('Deleted environment variables:')
        click.echo('\n'.join(resp.get('DeletedParameters')))
    if resp.get('InvalidParameters'):
        click.echo(click.style('Invalid environment variables:', fg="red"))
        click.echo(click.style('\n'.join(resp.get('InvalidParameters')), fg='red'))
