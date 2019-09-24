import click
from ..alias import AliasedGroup


def get_value(found_elements, kind):
    try:
        return found_elements[0].value
    except IndexError:
        raise ValueError('`{}` - this value doesn\'t exist.'.format(kind))


@click.group(cls=AliasedGroup, short_help='Update resources.')
@click.pass_context
def update(ctx):
    pass


@update.command(name='task-definition')
@click.argument('task-definition-family', required=True)
@click.option('--image-tag', required=True, multiple=True,
              help="Specify image to update in task definition.")
@click.option('-c', '--cluster',
              help="Specify cluster to execute command. Default usage cluster from context.")
@click.pass_context
def update_task_definitions(ctx, task_definition_family, image_tag, cluster):
    """
    \b
    # Update tag image in one container.
    cmd::ecsctl update task-definition my-app --image-tag backend=PR-123

    \b
    # Update tags image in two container.
    cmd::ecsctl update task-definition my-app --image-tag backend=PR-123 --image-tag frontend=PR-123
    """
    if not cluster:
        cluster = ctx.obj['cluster']
    bw = ctx.obj['bw']
    data = {}
    for image in image_tag:
        try:
            container, tag = image.split('=')
        except ValueError as e:
            click.echo(click.style('Set tag for container `--image-tag CONTAINER=DOCKER-TAG`. '
                                   'You used `--image-tag {}`'.format(image), fg="red"))
            return
        data[container] = tag
    resp = bw.update_task_definition(task_definition_family, cluster, images_tags=data)
    click.echo(click.style(resp['taskDefinition']['taskDefinitionArn'], fg="green"))


@update.command(name='service')
@click.argument('service', required=True)
@click.option('--version', type=int,
              help="Specify task-definition version to update in service.")
@click.option('--latest', is_flag=True,
              help="Specify latet version to update in service.")
@click.option('--rollback', is_flag=True,
              help="Rollback to one version before current service version.")
@click.option('-c', '--cluster',
              help="Specify cluster to execute command. Default usage cluster from context.")
@click.pass_context
def update_services(ctx, service, version, latest, rollback, cluster):
    """
    \b
    # Update to latest task-definition revision usage in selected service.
    cmd::ecsctl update service my-app --latest

    \b
    # Update to one version back which was usage in selected service.
    cmd::ecsctl update service my-app --rollback

    \b
    # Update selected service to 10 revision of task definition.
    cmd::ecsctl update service my-app --version 10
    """
    task_definition = None
    if not cluster:
        cluster = ctx.obj['cluster']
    bw = ctx.obj['bw']

    if rollback:
        task_definition = bw.get_task_definition_from_service(cluster, service, version='rollback')
    elif latest:
        task_definition = bw.get_task_definition_from_service(cluster, service, version='latest')
    elif version:
        task_definition = bw.get_task_definition_from_service(cluster, service, version=version)

    if task_definition:
        resp = bw.update_service(service, task_definition, cluster)
        output = resp['service']['serviceArn']
        click.echo(click.style(output, fg='green'))
    else:
        click.echo(click.style('Set one parameters: --version, --latest or --rollback.', fg='yellow'))
