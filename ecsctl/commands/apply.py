import click

from ..alias import AliasedGroup
from .. import core, display, exceptions


@click.group(cls=AliasedGroup, short_help='Create or update resources.', invoke_without_command=True)
@click.option('-f', '--file', 'file_path', type=click.Path(exists=True),
              help="Select file or folder that contains the configuration to apply.")
@click.option('-t', '--template', 'template_path', type=click.Path(exists=True),
              help="Select file or folder that contains the template configuration to apply.")
@click.option('-e', '--env', 'envs', multiple=True,
              help="During update task-definition also update service.")
@click.option('--env-file', 'env_file', multiple=True,
              help="During update task-definition also update service.")
@click.option('--dry-run', is_flag=True, default=False,
              help="If true, only print the object that would be sent, without sending it")
@click.option('--deploy', is_flag=True, default=False,
              help="During update task-definition also update service.")
@click.option('-c', '--cluster',
              help="Specify cluster to execute command. Default usage cluster from context.")
@click.pass_context
def apply(ctx, file_path, template_path, dry_run, deploy, envs, env_file, cluster, **kwargs):
    """
    \b
    # Apply yaml file with service definition
    cmd::ecsctl apply -f my-app/service.yaml

    \b
    # Apply yaml file with task definition
    cmd::ecsctl apply -f my-app/task-definition.yaml

    \b
    # Apply yaml template with task definition and set variables
    cmd::ecsctl apply -t my-app/task-definition.yaml.tpl --env image=my-image -e tag=1.0.0

    \b
    # Apply yaml template with task definition and file with variables
    cmd::ecsctl apply -t my-app/task-definition.yaml.tpl --env-file dev.env

    \b
    # Apply yaml template with task definition and file with variables
    cmd::ecsctl apply -t my-app/task-definition.yaml.tpl --env-file common.env --env-file dev.env

    \b
    # Apply folder with configuration files
    cmd::ecsctl apply -f my-app/

    \b
    # Apply yaml file with task definition and update service
    cmd::ecsctl apply -f my-app/task-definition.yaml --deploy

    \b
    # Check yaml file with task definition
    cmd::ecsctl apply -f my-app/task-definition.yaml --dry-run
    """
    bw = ctx.obj['bw']
    if not cluster:
        cluster = ctx.obj['cluster']
    if file_path and not template_path:
        _type, f = 'file', core.FileLoader(file_path)
    elif template_path and not file_path:
        _type, f = 'template', core.FileLoaderTemplate(template_path)
    else:
        click.echo(click.style(str('Usage only template or file to apply.'), fg='red'))
        return
    for doc in f.load():
        object_type = core.ObjectType(cluster=cluster, item=doc)
        tmpl = object_type.get_template()
        if _type == 'template':
            tmpl.render(envs, env_file)
        click.echo(click.style(object_type.ID, fg='yellow'))
        if dry_run:
            tmpl.run_before(boto_wrapper=bw)
            param = display.de_unicode(tmpl.to_request())
            tmpl.run_after(param, boto_wrapper=bw)
            click.echo(click.style(param, fg='blue'))
            click.echo('\n')
        else:
            try:
                resp = bw.apply_object(tmpl=tmpl, deploy=deploy)
            except Exception as err:
                click.echo(click.style(str(err), fg='red'))
            else:
                click.echo(click.style(object_type.show_response(resp), fg="green"))
                if resp.get('deploy'):
                    ID = 'Service: {}'.format(resp['deploy']['service']['serviceName'])
                    show_response = resp['deploy']['service']['serviceArn']
                    task_definition = resp['deploy']['service']['taskDefinition']
                    click.echo(click.style(ID, fg='yellow'))
                    click.echo(click.style('{} -> {}'.format(show_response, task_definition), fg="green"))
