import click
from .colorize import HelpColorsGroup


class AliasedGroup(HelpColorsGroup):

    def get_command(self, ctx, cmd_name):
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv
        mapping = {
            'svc': 'service',
            'services': 'service',
            'no': 'container-instance',
            'node': 'container-instance',
            'nodes': 'container-instance',
            'container-instances': 'container-instance',
            'clusters': 'cluster',
            'task-definitions': 'task-definition',
            'td': 'task-definition',
            'taskdef': 'task-definition',
            'taskdefs': 'task-definition',
            'tdf': 'task-definition-family',
            'task-definition-families': 'task-definition-family',
            'taskdef-family': 'task-definition-family',
            'taskdef-families': 'task-definition-family',
            'po': 'task',
            'pod': 'task',
            'pods': 'task',
            'ta': 'task',
            'tasks': 'task',
            'log': 'logs',
            'alb': 'loadbalancer',
            'lb': 'loadbalancer',
            'hz': 'hosted-zones',
            '53': 'hosted-zones',
            'zone': 'hosted-zones',
            'route53': 'hosted-zones',
            'cw': 'cloudwatch'
        }
        if cmd_name in mapping:
            rv = click.Group.get_command(self, ctx, mapping[cmd_name])
            if rv is not None:
                return rv
