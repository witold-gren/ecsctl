import re
import boto3
import pprint
import stringcase
import oyaml as yaml
from datetime import datetime

from botocore.exceptions import ClientError, ParamValidationError
from . import template


class BotoWrapperException(Exception):
    pass


class BotoWrapper:

    def __init__(self, session=None, *args, **kwargs):
        if not session:
            aws_access_key_id = kwargs.get('aws_access_key_id')
            aws_secret_access_key = kwargs.get('aws_secret_access_key')
            aws_session_token = kwargs.get('aws_session_token')
            region_name = kwargs.get('aws_region')
            profile_name = kwargs.get('aws_profile')
            session = boto3.session.Session(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_session_token=aws_session_token,
                region_name=region_name,
                profile_name=profile_name)
        self.session = session
        self.ecs_client = session.client('ecs')
        self.ec2_client = session.client('ec2')
        self.logs_client = session.client('logs')
        self.cloudwatch = session.client('cloudwatch')
        self.servicediscovery = session.client('servicediscovery')
        self.ssm = session.client('ssm')
        self.sts = session.client('sts')
        self.elb = session.client('elbv2')
        self.route53 = session.client('route53')

    def create_object(self, param, deploy=None, tmpl=None):
        func = getattr(self, '_execute_create_{}'.format(stringcase.snakecase(tmpl.template_name)))
        return func(param, deploy, tmpl)

    # TODO: create update object like service
    # def update_object(self, param, deploy=None, tmpl=None):
    #     func = getattr(self, '_execute_update_{}'.format(stringcase.snakecase(tmpl.name)))
    #     return func(param, deploy, tmpl)

    def apply_object(self, tmpl, deploy=None):
        tmpl.run_before(boto_wrapper=self)
        resp = self.create_object(tmpl.to_request(), deploy, tmpl)
        tmpl.run_after(resp, boto_wrapper=self)
        return resp

    def get_service_metric_data(self, cluster, start_time, end_time):
        data_queries = []
        for service_arn in self.all_service_arns(cluster=cluster):
            service = service_arn.split('/')[-1]
            for metrics_type in ['CPUUtilization', 'MemoryUtilization']:
                data_queries.append({
                    'Id': '{}-{}'.format(metrics_type.lower(), service).replace('-', '_'),
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/ECS',
                            'MetricName': metrics_type,
                            'Dimensions': [
                                {
                                    'Name': 'ServiceName',
                                    'Value': service
                                },
                                {
                                    'Name': 'ClusterName',
                                    'Value': cluster
                                },
                            ]
                        },
                        'Period': 1800,
                        'Stat': 'Average',
                        'Unit': 'Percent'
                    },
                    'ReturnData': True
                })

        try:
            response = self.cloudwatch.get_metric_data(
                MetricDataQueries=data_queries,
                StartTime=start_time,
                EndTime=end_time,
                ScanBy='TimestampDescending',
                MaxDatapoints=100
            )
        except ClientError as err:
            return str(err), True

        prepare = {}
        for resp_metrics in response['MetricDataResults']:
            service, metric = resp_metrics['Label'].split(' ')
            if not service in prepare:
                prepare[service] = {}
            if 'CPUUtilization' == metric:
                prepare[service]['CPUUtilization'] = resp_metrics['Values']
            elif 'MemoryUtilization' == metric:
                prepare[service]['MemoryUtilization'] = resp_metrics['Values']

        output = []
        for key, values in prepare.items():
            cpu, memory = 'none', 'none'
            if len(values['CPUUtilization']) == 1:
                cpu = '{:.2f}%'.format(values['CPUUtilization'][0])
            if len(values['MemoryUtilization']) == 1:
                memory = '{:.2f}%'.format(values['MemoryUtilization'][0])
            output.append((key, cpu, memory))
        return output, False

    def get_container_instance_metric_data(self, cluster, start_time, end_time):
        data_queries, instance_id, node = [], {}, None
        for data_node in self.get_container_instances(cluster=cluster, ec2_detail=True):
            node = data_node['ec2InstanceId']

            try:
                dimensions = [
                    {'Name': 'InstanceId', 'Value': node},
                    {'Name': 'AutoScalingGroupName', 'Value': list(filter(
                        lambda x: x['Key'] == 'aws:autoscaling:groupName', data_node['ec2_data']['Tags']))[0]['Value']},
                    {'Name': 'ImageId', 'Value': data_node['ec2_data']['ImageId']},
                    {'Name': 'InstanceType', 'Value': data_node['ec2_data']['InstanceType']}
                ]
            except (IndexError, KeyError) as e:
                dimensions = []

            instance_id[node] = data_node['containerInstanceArn'].split('/')[-1]
            for metrics_type in [
                    ('AWS/EC2', 'CPUUtilization', [{'Name': 'InstanceId', 'Value': node}]),
                    ('ECSInstancesMetrics', 'mem_used_percent', dimensions),
                    ('ECSInstancesMetrics', 'swap_used_percent', dimensions),
                    ('ECSInstancesMetrics', 'disk_used_percent', dimensions + [
                        {"Name": "path", "Value": "/"},
                        {'Name': 'fstype', 'Value': 'ext4'},
                        {'Name': 'device', 'Value': 'nvme0n1p1'}])]:
                data_queries.append({
                    'Id': '{}___{}'.format(metrics_type[1].lower(), node).replace('-', '_'),
                    'MetricStat': {
                        'Metric': {
                            'Namespace': metrics_type[0],
                            'MetricName': metrics_type[1],
                            'Dimensions': metrics_type[2]
                        },
                        'Period': 300,
                        'Stat': 'Average',
                        'Unit': 'Percent'
                    },
                    'ReturnData': True
                })

        try:
            response = self.cloudwatch.get_metric_data(
                MetricDataQueries=data_queries,
                StartTime=start_time,
                EndTime=end_time,
                ScanBy='TimestampDescending',
                MaxDatapoints=100
            )
        except ClientError as err:
            return str(err), True

        prepare = {}
        for resp_metrics in response['MetricDataResults']:
            _m, _i = resp_metrics.get('Id', '').split('___')
            node = _i.replace('_', '-')
            metric = resp_metrics['Label'].split(' ')[-1]
            if not node in prepare:
                prepare[node] = {}
            if 'CPUUtilization' == metric:
                prepare[node]['CPUUtilization'] = resp_metrics['Values']
            elif 'mem_used_percent' == metric:
                prepare[node]['MemoryUtilization'] = resp_metrics['Values']
            elif 'disk_used_percent' == metric:
                prepare[node]['DiskUsedPercent'] = resp_metrics['Values']
            elif 'swap_used_percent' == metric:
                prepare[node]['SwapUsedPercent'] = resp_metrics['Values']

        output = []
        for key, values in prepare.items():
            cpu, memory, disk, swap = 'none', 'none', 'none', 'none'
            if len(values.get('CPUUtilization', '')) == 1:
                cpu = '{:.2f}%'.format(values['CPUUtilization'][0])
            if len(values.get('MemoryUtilization', '')) == 1:
                memory = '{:.2f}%'.format(values['MemoryUtilization'][0])
            if len(values.get('DiskUsedPercent', '')) == 1:
                disk = '{:.2f}%'.format(values['DiskUsedPercent'][0])
            if len(values.get('SwapUsedPercent', '')) == 1:
                swap = '{:.2f}%'.format(values['SwapUsedPercent'][0])
            output.append((instance_id.get(key, 'none'), key, cpu, memory, disk, swap))
        return output, False

    def get_cluster_metric_data(self, cluster, start_time, end_time):
        #TODO: add reg exp fo get only letter from cluster name
        data_queries = []
        for metrics_type in ['CPUUtilization', 'CPUReservation', 'MemoryUtilization', 'MemoryReservation']:
            data_queries.append({
                'Id': '{}-{}'.format(metrics_type.lower(), cluster).replace('-', '_'),
                'MetricStat': {
                    'Metric': {
                        'Namespace': 'AWS/ECS',
                        'MetricName': metrics_type,
                        'Dimensions': [
                            {
                                'Name': 'ClusterName',
                                'Value': cluster
                            }
                        ]
                    },
                    'Period': 1800,
                    'Stat': 'Average',
                    'Unit': 'Percent'
                },
                'ReturnData': True
            })

        try:
            response = self.cloudwatch.get_metric_data(
                MetricDataQueries=data_queries,
                StartTime=start_time,
                EndTime=end_time,
                ScanBy='TimestampDescending',
                MaxDatapoints=100
            )
        except ClientError as err:
            return str(err), True

        prepare = {}
        for resp_metrics in response['MetricDataResults']:
            metric = resp_metrics['Label']
            if not cluster in prepare:
                prepare[cluster] = {}
            if 'CPUUtilization' == metric:
                prepare[cluster]['CPUUtilization'] = resp_metrics['Values']
            elif 'CPUReservation' == metric:
                prepare[cluster]['CPUReservation'] = resp_metrics['Values']
            elif 'MemoryUtilization' == metric:
                prepare[cluster]['MemoryUtilization'] = resp_metrics['Values']
            elif 'MemoryReservation' == metric:
                prepare[cluster]['MemoryReservation'] = resp_metrics['Values']

        output = []
        for key, values in prepare.items():
            cpu, cpu_res, memory, memory_res = 'none', 'none', 'none', 'none'
            if len(values['CPUUtilization']) == 1:
                cpu = '{:.2f}'.format(values['CPUUtilization'][0])
            if len(values['CPUReservation']) == 1:
                cpu_res = '{:.2f}'.format(values['CPUReservation'][0])
            if len(values['MemoryUtilization']) == 1:
                memory = '{:.2f}'.format(values['MemoryUtilization'][0])
            if len(values['MemoryReservation']) == 1:
                memory_res = '{:.2f}'.format(values['MemoryReservation'][0])
            output.append((key, '{}%/{}%'.format(cpu_res, cpu), '{}%/{}%'.format(memory_res, memory)))
        return output, False

    def describe_instance(self, instance_id):
        try:
            resp = self.ec2_client.describe_instances(InstanceIds=[instance_id])
        except Exception as e:
            return str(e)
        return resp['Reservations'][0]['Instances'][0]

    def all_service_arns(self, cluster='default'):
        paginator = self.ecs_client.get_paginator('list_services')
        out = []
        for page in paginator.paginate(cluster=cluster):
            out += page['serviceArns']
        return out

    def get_services(self, cluster='default'):
        services = self.all_service_arns(cluster=cluster)
        out = []
        while services:
            batch_services, services = services[:10], services[10:]
            resp = self.ecs_client.describe_services(
                cluster=cluster,
                services=batch_services,
            )
            out += resp['services']
        return out

    def describe_service(self, service, cluster='default'):
        resp = self.ecs_client.describe_services(
            cluster=cluster,
            services=[service],
        )
        if not resp['services']:
            raise BotoWrapperException('Service not found.')
        return resp['services'][0]

    def all_container_instance_arns(self, cluster='default'):
        paginator = self.ecs_client.get_paginator('list_container_instances')
        out = []
        for page in paginator.paginate(cluster=cluster):
            out += page['containerInstanceArns']
        return out

    def get_container_instances(self, cluster='default', ec2_detail=True):
        out = []
        nodes = self.all_container_instance_arns(cluster=cluster)
        while nodes:
            response = {}
            batch_nodes, nodes, output = nodes[:100], nodes[100:], []
            output_ecs = self.ecs_client.describe_container_instances(
                cluster=cluster,
                containerInstances=batch_nodes,
            )
            if ec2_detail:
                output_ec2 = self.ec2_client.describe_instances(
                    InstanceIds=[x['ec2InstanceId'] for x in output_ecs['containerInstances']]
                )
                ecs = output_ecs['containerInstances']
                ec2 = output_ec2['Reservations']
                for ecs_inst, ec2_inst in zip(ecs, ec2):
                    if not ecs_inst['ec2InstanceId'] in response:
                        response[ecs_inst['ec2InstanceId']] = {}
                    response[ecs_inst['ec2InstanceId']]['ECS'] = ecs_inst
                    if not ec2_inst['Instances'][0]['InstanceId'] in response:
                        response[ec2_inst['Instances'][0]['InstanceId']] = {}
                    response[ec2_inst['Instances'][0]['InstanceId']]['EC2'] = ec2_inst['Instances'][0]
                for instance_id, values in response.items():
                    data = values['ECS']
                    data['ec2_data'] = values['EC2']
                    output.append(data)
                out.extend(output)
            else:
                out = output_ecs['containerInstances']
        return out

    def describe_container_instance(self, node, output='json', cluster='default'):
        try:
            resp = self.ecs_client.describe_container_instances(
                cluster=cluster,
                containerInstances=[node],
            )
        except Exception as e:
            return str(e), True

        if not resp['containerInstances']:
            return 'This instance doen\'t exist. {}'.format(node), True
        data = resp['containerInstances'][0]
        if output != 'yaml':
            output_ec2 = self.ec2_client.describe_instances(
                InstanceIds=[resp['containerInstances'][0]['ec2InstanceId']]
            )
            data['ec2_data'] = output_ec2['Reservations'][0]['Instances'][0]
        return data, False

    def all_cluster_arns(self):
        resp = self.ecs_client.list_clusters()
        return resp['clusterArns']

    def get_clusters(self):
        clusters = self.all_cluster_arns()
        out = []
        while clusters:
            batch_clusters, clusters = clusters[:10], clusters[10:]
            resp = self.ecs_client.describe_clusters(
                clusters=batch_clusters,
            )
            out += resp['clusters']
        return out

    def describe_cluster(self, cluster):
        resp = self.ecs_client.describe_clusters(
            clusters=[cluster],
        )
        return resp['clusters'][0]

    def _get_val(self, _list, _index, default=None):
        try:
            val = _list[_index]
        except (IndexError, TypeError):
            val = default
        return val

    def _create_volumes(self, kwargs):
        volumes = []
        volume_names = kwargs.get('volume_names', [])
        volume_scopes = kwargs.get('volume_scopes')
        volume_autoprovisions = kwargs.get('volume_autoprovisions')
        volume_drivers = kwargs.get('volume_drivers')
        volume_driver_options = kwargs.get('volume_driver_options')
        volume_driver_labels = kwargs.get('volume_driver_labels')
        volume_host_paths = kwargs.get('volume_host_paths')

        for x, name in enumerate(volume_names):
            volume_configuration, volume = {}, {'name': name}
            if self._get_val(volume_host_paths, x):
                volume['host'] = {'sourcePath': self._get_val(volume_host_paths, x)}
            if self._get_val(volume_scopes, x):
                volume_configuration['scope'] = self._get_val(volume_scopes, x)
            if self._get_val(volume_autoprovisions, x):
                volume_configuration['autoprovision'] = True if self._get_val(volume_autoprovisions, x) in ['true',
                                                                                                            'True'] else False
            if self._get_val(volume_drivers, x):
                volume_configuration['driver'] = self._get_val(volume_drivers, x)
            if self._get_val(volume_driver_options, x):
                volume_configuration['driverOpts'] = dict(
                    x.split('=') for x in self._get_val(volume_driver_options, x).split(','))
            if self._get_val(volume_driver_labels, x):
                volume_configuration['labels'] = dict(
                    x.split('=') for x in self._get_val(volume_driver_labels, x).split(','))
            if volume_configuration:
                volume['dockerVolumeConfiguration'] = volume_configuration
            volumes.append(volume)

        return volumes

    def _create_containers(self, kwargs):
        """
        TODO: add this params
        'linuxParameters': {
            'capabilities': {
                'add': [
                    'string',
                ],
                'drop': [
                    'string',
                ]
            },
            'devices': [
                {
                    'hostPath': 'string',
                    'containerPath': 'string',
                    'permissions': [
                        'read' | 'write' | 'mknod',
                    ]
                },
            ],
            'initProcessEnabled': True | False,
            'sharedMemorySize': 123,
            'tmpfs': [
                {
                    'containerPath': 'string',
                    'size': 123,
                    'mountOptions': [
                        'string',
                    ]
                },
            ],
            'maxSwap': 123,
            'swappiness': 123
        },
        'secrets': [
            {
                'name': 'string',
                'valueFrom': 'string'
            },
        ],
        'healthCheck': {
            'command': [
                'string',
            ],
            'interval': 123,
            'timeout': 123,
            'retries': 123,
            'startPeriod': 123
        },
        'systemControls': [
            {
                'namespace': 'string',
                'value': 'string'
            },
        ],
        'resourceRequirements': [
            {
                'value': 'string',
                'type': 'GPU'
            },
        ],
        'firelensConfiguration': {
            'type': 'fluentd' | 'fluentbit',
            'options': {
                'string': 'string'
            }
        }
        """
        container_definitions = []

        container_names = kwargs.get('container_names')
        container_images = kwargs.get('container_images')
        container_private_repo = kwargs.get('container_private_repo')
        container_repo_auths = kwargs.get('container_repo_auths')
        container_memory = kwargs.get('container_memory')
        container_memory_reservation = kwargs.get('container_memory_reservation')
        container_cpus = kwargs.get('container_cpus')
        container_links = kwargs.get('container_links')
        container_ports = kwargs.get('container_ports')
        container_essentials = kwargs.get('container_essentials')
        # container_gpus = kwargs.get('container_gpus')
        container_entrypoints = kwargs.get('container_entrypoints')
        container_commands = kwargs.get('container_commands')
        container_env_variables = kwargs.get('container_env_variables')
        container_mount_points = kwargs.get('container_mount_points')
        container_volumes_from = kwargs.get('container_volumes_from')
        container_start_timeouts = kwargs.get('container_start_timeouts')
        container_stop_timeouts = kwargs.get('container_stop_timeouts')
        container_hostnames = kwargs.get('container_hostnames')
        container_user = kwargs.get('container_user')
        container_directories = kwargs.get('container_directories')
        container_privileged = kwargs.get('container_privileged')
        container_read_root = kwargs.get('container_read_root')
        container_disable_networkings = kwargs.get('container_disable_networkings')
        container_dns_servers = kwargs.get('container_dns_servers')
        container_dns_searchs = kwargs.get('container_dns_searchs')
        container_extra_hosts = kwargs.get('container_extra_hosts')
        container_security_options = kwargs.get('container_security_options')
        container_docker_labels = kwargs.get('container_docker_labels')
        container_resource_limits = kwargs.get('container_resource_limits')
        container_log_configuration = kwargs.get('container_log_configuration')
        container_log_drivers = kwargs.get('container_log_drivers')
        container_log_options = kwargs.get('container_log_options')
        container_log_secret = kwargs.get('container_log_secret')
        container_interactive = kwargs.get('container_interactive')
        container_pseudo_terminal = kwargs.get('container_pseudo_terminal')
        container_depends_on = kwargs.get('container_depends_on')

        for x, name in enumerate(container_names):
            container = {'name': name, 'image': self._get_val(container_images, x)}

            if self._get_val(container_private_repo, x) and self._get_val(container_repo_auths, x):
                container['repositoryCredentials'] = {'credentialsParameter': self._get_val(container_repo_auths, x)}
            if self._get_val(container_cpus, x):
                if self._get_val(container_cpus, x) < 128:
                    raise BotoWrapperException("Task CPU (unit) should be greater than or equal to 128.")
                container['cpu'] = self._get_val(container_cpus, x)
            if self._get_val(container_memory, x):
                if self._get_val(container_cpus, x) < 4:
                    raise BotoWrapperException("Task Memory (unit) should be greater than or equal to 4.")
                container['memory'] = self._get_val(container_memory, x)
            if self._get_val(container_memory_reservation, x):
                if self._get_val(container_memory_reservation, x) < 4:
                    raise BotoWrapperException("Task Memory (unit) should be greater than or equal to 4.")
                container['memoryReservation'] = self._get_val(container_memory_reservation, x)
            if self._get_val(container_links, x):
                _links = self._get_val(container_links, x)
                if _links:
                    container['links'] = [link for link in _links.split(',')]
            if self._get_val(container_ports, x):
                #80,8443:443,8125:8125/udp
                port_mappings = []
                for ports in self._get_val(container_ports, x).split(','):
                    _ports, _protocol = ports.split('/') if '/' in ports else (ports, 'tcp')
                    _c_port, _h_port = _ports, _ports
                    if ':' in _ports:
                        _c_port, _h_port = _ports.split(':')
                    port_mappings.append({
                        'containerPort': int(_c_port) if _c_port.isdigit() else _c_port,
                        'hostPort': int(_h_port) if _c_port.isdigit() else _c_port,
                        'protocol': _protocol
                    })
                container['portMappings'] = port_mappings
            if self._get_val(container_essentials, x):
                container['essential'] = self._get_val(container_essentials, x)
            if self._get_val(container_entrypoints, x):
                container['entryPoint'] = [self._get_val(container_entrypoints, x)]
            if self._get_val(container_commands, x):
                container['entryPoint'] = [self._get_val(container_commands, x)]
            if self._get_val(container_env_variables, x):
                _environment = []
                for env in self._get_val(container_env_variables, x):
                    k, v = env.split("=")
                    _environment.append({'name': k, 'value': v})
                container['environment'] = _environment
            if self._get_val(container_mount_points, x):
                mount_points = []
                for point in self._get_val(container_mount_points, x).split(','):
                    _source, _path, _readonly = point, point, False
                    if len(point.split(":")) > 3:
                        _source, _path, _readonly = point.split(":")
                    elif len(point.split(":")) == 2:
                        _source, _path = point.split(":")
                    mount_points.append({
                        'sourceVolume': _source,
                        'containerPath': _path,
                        'readOnly': True if _readonly in ['true', 'True'] else False
                    })
                container['mountPoints'] = mount_points
            if self._get_val(container_volumes_from, x):
                volumes_from = []
                for vol in self._get_val(container_volumes_from, x).split(','):
                    _source, _readonly = vol, True
                    if len(vol.split(":")) == 2:
                        _source, _readonly = vol.split(":")
                    volumes_from.append({
                        'sourceContainer': _source,
                        'readOnly': True if _readonly in ['true', 'True'] else False
                    })
                container['volumesFrom'] = volumes_from

            if self._get_val(container_start_timeouts, x):
                container['startTimeout'] = self._get_val(container_start_timeouts, x)
            if self._get_val(container_stop_timeouts, x):
                container['stopTimeout'] = self._get_val(container_stop_timeouts, x)
            if self._get_val(container_hostnames, x):
                container['hostname'] = self._get_val(container_hostnames, x)
            if self._get_val(container_user, x):
                container['user'] = self._get_val(container_user, x)
            if self._get_val(container_directories, x):
                container['workingDirectory'] = self._get_val(container_directories, x)
            if self._get_val(container_privileged, x):
                container['privileged'] = True if self._get_val(container_privileged, x) in ['true', 'True'] else False
            if self._get_val(container_read_root, x):
                container['readonlyRootFilesystem'] = True if self._get_val(container_read_root, x) in ['true', 'True'] else False
            if self._get_val(container_disable_networkings, x):
                container['disableNetworking'] = self._get_val(container_disable_networkings, x)
            if self._get_val(container_dns_servers, x):
                container['dnsServers'] = [x for x in self._get_val(container_dns_servers, x).split(',')]
            if self._get_val(container_dns_searchs, x):
                container['dnsSearchDomains'] = [x for x in self._get_val(container_dns_searchs, x).split(',')]
            if self._get_val(container_extra_hosts, x):
                extra_hosts = []
                for host in self._get_val(container_extra_hosts, x).split(','):
                    hostname, ip = host.split(":")
                    extra_hosts.append({'hostname': hostname, 'ipAddress': ip})
                container['extraHosts'] = extra_hosts
            if self._get_val(container_security_options, x):
                container['dockerSecurityOptions'] = [x for x in self._get_val(container_security_options, x).split(',')]
            if self._get_val(container_docker_labels, x):
                labels = {}
                for label in self._get_val(container_docker_labels, x).split(','):
                    key, value = label.split('=')
                    labels[key] = value
                container['dockerLabels'] = labels
            if self._get_val(container_resource_limits, x):
                limits = []
                NAMES = ['core', 'cpu', 'data', 'fsize', 'locks', 'memlock', 'msgqueue', 'nice', 'nofile',
                         'nproc', 'rss', 'rtprio', 'rttime', 'sigpending', 'stack']
                for limit in self._get_val(container_resource_limits, x).split(','):
                    _name, _soft, _hard = limit, None, None
                    if len(limit.split(':')) == 3:
                        _name, _soft, _hard = limit.split(':')
                    elif len(limit.split(':')) == 2:
                        _name, _soft, = limit.split(':')
                    if _name in NAMES:
                        l = {'name': _name}
                        if _soft and _soft.isdigit(): l['softLimit'] = int(_soft)
                        if _hard and _hard.isdigit(): l['softLimit'] = int(_hard)
                        limits.append(l)
                    else:
                        raise BotoWrapperException("Invalid resource name. Your value is `{}`, correct values: {}.".format(
                            _name, ','.join(NAMES)))
                container['ulimits'] = limits
            if self._get_val(container_log_configuration, x):
                LOG_DRIVER = ['json-file', 'syslog', 'journald', 'gelf', 'fluentd', 'awslogs', 'splunk', 'awsfirelens']
                log_conf = {}

                if self._get_val(container_log_drivers, x) in LOG_DRIVER:
                    log_conf['logDriver'] = self._get_val(container_log_drivers, x)

                if self._get_val(container_log_options, x):
                    options = {}
                    for log_option in self._get_val(container_log_options, x).split(','):
                        k, v = log_option.split('=')
                        options[k] = v
                    log_conf['options'] = options

                if self._get_val(container_log_secret, x):
                    secrets = []
                    for log_secret in self._get_val(container_log_secret, x).split(','):
                        k, v = log_secret.split('=')
                        secrets.append({'name': k, 'valueFrom': v})
                    log_conf['secretOptions'] = secrets
                container['logConfiguration'] = log_conf
            if self._get_val(container_pseudo_terminal, x):
                container['pseudoTerminal'] = True if self._get_val(container_pseudo_terminal, x) in ['true', 'True'] else False
            if self._get_val(container_interactive, x):
                container['interactive'] = True if self._get_val(container_interactive, x) in ['true', 'True'] else False
            if self._get_val(container_depends_on, x):
                depends = []
                CONDITIONS = ['START', 'COMPLETE', 'SUCCESS', 'HEALTHY']
                for depend in self._get_val(container_depends_on, x).split(','):
                    _container, _condition = depend.split('=')
                    if not _condition in CONDITIONS:
                        raise BotoWrapperException("Your condition `` is incorrect. Select one of: {}".format(
                            _condition, ','.join(CONDITIONS)))
                    depends.append({
                        'containerName': _container,
                        'condition': _condition
                    })
                container['dependsOn'] = depends

            container_definitions.append(container)
        return container_definitions

    def _execute_create_task_definition(self, param, deploy=None, tmpl=None, **kwargs):
        try:
            resp = self.ecs_client.register_task_definition(**param)
            task_name = re.findall(r'.+\/(.+)\:\d+?', str(resp['taskDefinition']['taskDefinitionArn']))
            service = None
            if deploy:
                for s in self.get_services(tmpl.cluster):
                    service_task_name = re.findall(r'.+\/(.+)\:\d+?', s['taskDefinition'])
                    if task_name == service_task_name:
                        service = s
                        break
                if service:
                    service_resp = self.update_service(
                        task_definition=resp['taskDefinition']['taskDefinitionArn'],
                        cluster=tmpl.cluster,
                        service=service['serviceArn'])
                    resp['deploy'] = service_resp
        except ClientError as err:
            raise BotoWrapperException(str(err))
        except ParamValidationError as err:
            raise BotoWrapperException("{}\n{}".format(err.fmt.split('\n')[0], err.kwargs['report']))
        return resp

    def update_service(self, service, task_definition, cluster='default'):
        try:
            resp = self.ecs_client.update_service(
                cluster=cluster,
                service=service,
                taskDefinition=task_definition)
        except ClientError as err:
            raise BotoWrapperException(str(err))
        except ParamValidationError as err:
            raise BotoWrapperException("{}\n{}".format(err.fmt.split('\n')[0], err.kwargs['report']))
        return resp

    def create_task_definition(self, name, *args, **kwargs):
        """
        TODO: Sdd this functionality to `task_definition`
        proxyConfiguration={
            'type': 'APPMESH',
            'containerName': 'string',
            'properties': [
                {
                    'name': 'string',
                    'value': 'string'
                },
            ]
        }
        """
        task_definition = {
            "family": name,
            "containerDefinitions": self._create_containers(kwargs)
        }

        if kwargs.get('task_role'):
            task_definition['taskRoleArn'] = kwargs.get('task_role')
        if kwargs.get('task_execution_role'):
            task_definition['executionRoleArn'] = kwargs.get('task_execution_role')
        if kwargs.get('network_mode'):
            task_definition['networkMode'] = kwargs.get('network_mode')
        if kwargs.get('launch_type'):
            task_definition['requiresCompatibilities'] = [kwargs.get('launch_type')]
        if kwargs.get('cpu'):
            task_definition['cpu'] = kwargs.get('cpu')
        if kwargs.get('memory'):
            task_definition['memory'] = kwargs.get('memory')
        if kwargs.get('pid_mode'):
            task_definition['pidMode'] = kwargs.get('pid_mode')
        if kwargs.get('ipc_mode'):
            task_definition['ipcMode'] = kwargs.get('ipc_mode')

        constraints = kwargs.get('constraints')
        if constraints:
            task_definition['placementConstraints'] = [{'type': 'memberOf', 'expression': exp} for exp in constraints]

        volumes = self._create_volumes(kwargs)
        if volumes:
            task_definition['volumes'] = volumes

        tags = kwargs.get('tags')
        if tags:
            task_definition['tags'] = [dict(zip(['key', 'value'], tag.split('='))) for tag in tags]

        return self._execute_create_task_definition(task_definition)

    def update_task_definition(self, task_definition_familly, cluster, images_tags):
        familie = self.all_task_definition_families(family_prefix=task_definition_familly)
        if familie:
            familly_name, last_task, count = familie[0]
            task_definition, tags = self.describe_task_definition(last_task, cluster, tags=True)
            task_definition = self.strip_task_def_data(task_definition)
            if tags:
                task_definition['tags'] = tags
            for x, container in enumerate(task_definition.get('containerDefinitions')):
                image_tag = images_tags.get(container.get('name'))
                if image_tag:
                    image = container['image'].split(':')[0]
                    task_definition['containerDefinitions'][x]['image'] = '{}:{}'.format(image, image_tag)

            return self._execute_create_task_definition(task_definition)

    def _execute_create_service(self, param, deploy=None, tmpl=None, **kwargs):
        for x, service in enumerate(param.get('serviceRegistries', [])):
            if 'registryArn' in service and service['registryArn'] is None:
                namespace = service.pop('_namespace', None)
                arn = self._execute_create_sercive_deiscovery(service=param, namespace=namespace)
                param['serviceRegistries'][x]['registryArn'] = arn

        try:
            resp = self.ecs_client.create_service(**param)
        except ClientError as err:
            raise BotoWrapperException("{}".format(str(err)))
        except ParamValidationError as err:
            raise BotoWrapperException("{}\n{}".format(err.fmt.split('\n')[0], err.kwargs['report']))
        return resp

    def _execute_create_sercive_deiscovery(self, service, namespace=None):
        namespaces, ns = self.servicediscovery.list_namespaces(MaxResults=100), None
        if len(namespaces['Namespaces']) == 1:
            ns = namespaces['Namespaces'][0]
        elif namespace:
            for _namespace in namespaces:
                if _namespace['Name'] == namespace:
                    ns = _namespace
                    break
        if not ns:
            raise BotoWrapperException(
                'Select namespaces `spec.service_registries._namespace: ` for service discovery in service file. '
                'Current you have {} namespaces: {}'.format(
                    len(namespaces['Namespaces'], ','.join([x['Name'] for x in namespaces['Namespaces']]))))
        dns_record_type = 'SRV'
        response = self.servicediscovery.create_service(
            Name=service['serviceName'],
            NamespaceId=ns['Id'],
            CreatorRequestId=service['serviceName'],
            Description='Service discovery for ECS service `{}`.'.format(service['serviceName']),
            DnsConfig={
                'NamespaceId': ns['Id'],
                'RoutingPolicy': 'MULTIVALUE',                  # TODO: check what it means? MULTIVALUE/WEIGHTED
                'DnsRecords': [{'Type': dns_record_type, 'TTL': 60}]
            }
        )
        return response['Service']['Arn']

    def create_service(self, name, cluster='default', **kwargs):
        deployment_conf = {}

        task_definition = kwargs.get('task_definition')
        desired_count = kwargs.get('desired_count')
        client_token = kwargs.get('client_token')
        launch_type = kwargs.get('launch_type')
        platform_version = kwargs.get('platform_version')
        role = kwargs.get('role')
        health_check = kwargs.get('health_check')
        scheduling_strategy = kwargs.get('scheduling_strategy')
        enable_ecs_managed_tags = kwargs.get('enable_ecs_managed_tags')
        propagate_tags = kwargs.get('propagate_tags')
        tags = kwargs.get('tags')
        deployment_controller = kwargs.get('deployment_controller')
        deployment_conf_max = kwargs.get('deployment_conf_max')
        deployment_conf_min = kwargs.get('deployment_conf_min')
        constraints = kwargs.get('constraints')
        strategies = kwargs.get('strategies')
        service_registries_arn = kwargs.get('service_registries_arn')
        service_registries_port = kwargs.get('service_registries_port')
        service_registries_container_name = kwargs.get('service_registries_container_name')
        service_registries_container_port = kwargs.get('service_registries_container_port')
        load_balancers_target_group_arn = kwargs.get('load_balancers_target_group_arn')
        load_balancers_name = kwargs.get('load_balancers_name')
        load_balancers_container_name = kwargs.get('load_balancers_container_name')
        load_balancers_container_port = kwargs.get('load_balancers_container_port')
        awsvpc_subnets = kwargs.get('awsvpc_subnets')
        awsvpc_security_groups = kwargs.get('awsvpc_security_groups')
        awsvpc_assign_public_ip = kwargs.get('awsvpc_assign_public_ip')

        service = {
            'cluster': cluster,
            'serviceName': name,
        }

        if task_definition:
            service['taskDefinition'] = task_definition
        if desired_count:
            service['desiredCount'] = desired_count
        if client_token:
            service['clientToken'] = client_token
        if launch_type:
            service['launchType'] = launch_type
        if platform_version:
            service['platformVersion'] = platform_version
        if role:
            service['role'] = role
        if health_check:
            service['healthCheckGracePeriodSeconds'] = health_check
        if scheduling_strategy:
            service['schedulingStrategy'] = scheduling_strategy
        if enable_ecs_managed_tags:
            service['enableECSManagedTags'] = enable_ecs_managed_tags
        if propagate_tags:
            service['propagateTags'] = propagate_tags
        if tags:
            tags = []
            for tag in tags.split(','):
                k, v = tag.split('=')
                tags.append({'key': k, 'value': v})
            service['tags'] = tags
        if deployment_controller:
            service['deploymentController'] = {'type': deployment_controller}
        if deployment_conf_max:
            deployment_conf['maximumPercent'] = deployment_conf_max
        if deployment_conf_min:
            deployment_conf['minimumHealthyPercent'] = deployment_conf_min
        if deployment_conf:
            service['deploymentConfiguration'] = deployment_conf
        if constraints:
            service['placementConstraints'] = [{'type': 'memberOf', 'expression': exp} for exp in constraints.split(',')]
        if strategies:
            _strategies = []
            for strategy in strategies.split(','):
                _type, _field = strategy, None
                if len(strategy.split('=')) > 1:
                    _type, _field = strategy
                _s = {'type': _type}
                if _field: _s['field'] = _field
                _strategies.append(_s)
            service['placementStrategy'] = _strategies

        if service_registries_arn:
            service_registries = []
            for x, arn in enumerate(service_registries_arn):
                registries = dict(registryArn=arn)
                registries['port'] = self._get_val(service_registries_port, x)
                registries['containerName'] = self._get_val(service_registries_container_name, x)
                registries['containerPort'] = self._get_val(service_registries_container_port, x)
                service_registries.append(registries)
            service['serviceRegistries'] = service_registries

        if load_balancers_name:
            load_balancers = []
            for x, name in enumerate(load_balancers_name):
                load_balancer = dict(loadBalancerName=name)
                load_balancer['targetGroupArn'] = self._get_val(load_balancers_target_group_arn, x)
                load_balancer['containerName'] = self._get_val(load_balancers_container_name, x)
                load_balancer['containerPort'] = self._get_val(load_balancers_container_port, x)
            service['loadBalancers'] = load_balancers

        if awsvpc_subnets:
            service['networkConfiguration'] = {
                'awsvpcConfiguration': {
                    'subnets': awsvpc_subnets.split(','),
                    'securityGroups': awsvpc_security_groups.split(','),
                    'assignPublicIp': awsvpc_assign_public_ip or 'DISABLED'
                }
            }

        return self._execute_create_service(service)

    def delete_service(self, service, cluster='default', force=False):
        if force:
            resp = self.ecs_client.update_service(
                service=service,
                cluster=cluster,
                desiredCount=0,
            )
        try:
            resp = self.ecs_client.delete_service(
                service=service,
                cluster=cluster)
        except Exception as e:
            return str(e), True
        return resp, False

    def deregister_task_definition(self, task_definition):
        try:
            resp = self.ecs_client.deregister_task_definition(
                taskDefinition=task_definition,
            )
        except Exception as e:
            return str(e), True

        return resp['taskDefinition'], False

    def deregister_task_definition_family(self, task_definition_family):
        out = []
        task_definitions = self.all_task_definitions(task_definition_family, 'ACTIVE')
        for task_definition in task_definitions:
            resp, err = self.deregister_task_definition(task_definition)
            if not err:
                out.append(resp)
            else:
                return str(resp), True
        return out, False

    def all_tasks(self, cluster='default', status='RUNNING'):
        paginator = self.ecs_client.get_paginator('list_tasks')
        out = []
        for page in paginator.paginate(cluster=cluster, desiredStatus=status):
            out += page['taskArns']
        return out

    def get_tasks(self, cluster, status):
        out, tasks = [], self.all_tasks(cluster=cluster, status=status)

        while tasks:
            batch_tasks, tasks = tasks[:100], tasks[100:]
            resp = self.ecs_client.describe_tasks(
                tasks=batch_tasks,
                cluster=cluster,
            )
            out += resp['tasks']

        return out

    def all_task_definition_families(self, family_prefix=None, status='ALL'):
        out = []
        paginator = self.ecs_client.get_paginator('list_task_definition_families')
        params = dict(status=status)
        if family_prefix is not None:
            params['familyPrefix'] = family_prefix
        for page in paginator.paginate(**params):
            for familly in page['families']:
                count = 0
                last = 'EMPTY'
                paginator_td = self.ecs_client.get_paginator('list_task_definitions')
                for page in paginator_td.paginate(familyPrefix=familly, sort='DESC'):
                    _len = len(page['taskDefinitionArns'])
                    if last == 'EMPTY' and _len:
                        last = page['taskDefinitionArns'][0]
                    count += _len
                out.append((familly, last, count))
        return out

    def all_task_definitions(self, family_prefix=None, status='ALL'):
        paginator = self.ecs_client.get_paginator('list_task_definitions')
        out = []
        params = dict(status=status)
        if family_prefix is not None:
            params['familyPrefix'] = family_prefix
        for page in paginator.paginate(**params):
            out += page['taskDefinitionArns']
        return out

    def get_task_definition_from_service(self, cluster, service, version):
        _service = self.describe_service(service, cluster)
        task_definition = _service['taskDefinition']

        reg = re.findall(r'arn\:aws\:ecs\:(.+)\:(.+)\:task-definition\/(.+)\:(.+)?', task_definition)
        _region, _account_id, _task_definition, _version = reg[0]

        if version == 'rollback':
            if int(_version) > 1:
                task_definition = 'arn:aws:ecs:{}:{}:task-definition/{}:{}'.format(
                    _region, _account_id, _task_definition, int(_version) - 1)
        elif version == 'latest':
            _familie = self.all_task_definition_families(_task_definition)
            if _familie:
                _familly_name, _last_task, _count = _familie[0]
                task_definition = _last_task
        else:
            _familie = self.all_task_definition_families(_task_definition)
            if _familie:
                _familly_name, _last_task, _count = _familie[0]
                if 0 < int(version) <= _count:
                    task_definition = 'arn:aws:ecs:{}:{}:task-definition/{}:{}'.format(
                        _region, _account_id, _task_definition, version)

        return task_definition

    def describe_task(self, task, cluster='default', simple=False):
        resp = self.ecs_client.describe_tasks(
            tasks=[task],
            cluster=cluster,
        )
        if not resp['tasks']:
            raise BotoWrapperException('Task not found.')
        task = resp['tasks'][0]
        if not simple:
            output_ec2 = self.describe_container_instance(task['containerInstanceArn'], cluster=cluster)
            task['containerInstance'] = output_ec2
        return task

    def describe_task_definition(self, task_definition, cluster='default', tags=False):
        resp = self.ecs_client.describe_task_definition(
            taskDefinition=task_definition,
        )
        if tags:
            return resp['taskDefinition'], resp.get('tags', [])
        return resp['taskDefinition']

    def describe_object(self, data, export, obj='TaskDefinition', **kwargs):
        tmpl = getattr(template, obj)(json=data, clean=export, **kwargs)
        return tmpl.to_file()

    def convert_to_yaml(self, data):
        return yaml.dump(data, default_flow_style=False)

    def _execute_create_task(self, param, deploy=None, tmpl=None, namespace=None, **kwargs):
        raise NotImplementedError

    def run(self, name=None, cluster='default', command=(), image=None, cpu=1024, memory=2048, count=1):
        task_def_family = name
        container_name = name
        service_name = '%s-svc' % name
        container_definition = {
            'name': container_name,
            'image': image,
            'cpu': cpu,
            'memory': memory,
        }
        if command:
            container_definition['command'] = 'command'
        resp = self.ecs_client.register_task_definition(
            family=task_def_family,
            containerDefinitions=[container_definition],
        )
        task_def_arn = resp['taskDefinition']['taskDefinitionArn']
        resp = self.ecs_client.create_service(
            cluster=cluster,
            serviceName=service_name,
            taskDefinition=task_def_arn,
            desiredCount=count,
        )

    def stop_task(self, task, cluster='default', reason='Stopped with ecsctl.'):
        resp = self.ecs_client.stop_task(
            task=task, cluster=cluster, reason=reason
        )
        return resp

    def drain_node(self, node, cluster='default'):
        resp = self.ecs_client.update_container_instances_state(
            cluster=cluster,
            containerInstances=[node],
            status='DRAINING',
        )
        return resp

    def undrain_node(self, node, cluster='default'):
        resp = self.ecs_client.update_container_instances_state(
            cluster=cluster,
            containerInstances=[node],
            status='ACTIVE',
        )
        return resp

    def scale_service(self, service, count, cluster='default'):
        resp = self.ecs_client.update_service(
            cluster=cluster,
            service=service,
            desiredCount=count,
        )
        return resp

    def strip_task_def_data(self, info):
        info = info.copy()
        for item in ['status', 'taskDefinitionArn', 'revision', 'requiresAttributes', 'compatibilities']:
            if item in info:
                del info[item]
        return info

    def strip_service_data(self, info):
        info = info.copy()
        for item in ['events', 'status', 'serviceArn', 'createdAt', 'deployments', 'runningCount', 'pendingCount']:
            if item in info:
                del info[item]
        return info

    def strip_task_data(self, info):
        info = info.copy()
        for item in ['containerInstance', 'containerInstanceArn', 'lastStatus', 'desiredStatus', 'cpu', 'memory',
                     'version', 'connectivity', 'connectivityAt', 'pullStartedAt', 'pullStoppedAt', 'createdAt',
                     'startedAt', 'attachments', 'healthStatus', 'containers', 'taskArn']:
            if item in info:
                del info[item]
        return info

    def logs(self, task, cluster, *args, **kwargs):
        awslogs_group, awslogs_stream, containers, logs, info = [], [], [], [], []

        container = kwargs.get('container')
        start_time = int(kwargs.get('start_time').timestamp()) * 1000 if kwargs.get('start_time') else None
        end_time = int(kwargs.get('end_time').timestamp()) * 1000 if kwargs.get('end_time') else None
        filter_pattern = kwargs.get('filter')
        byte_size = kwargs.get('byte_size')

        try:
            _task = self.describe_task(task, cluster=cluster, simple=True)
        except Exception as e:
            return str(e), True

        _task_definition = self.describe_task_definition(_task['taskDefinitionArn'], cluster=cluster)

        for x, _container in enumerate(_task_definition['containerDefinitions']):
            containers.append(_container.get('name'))
            if container and _container.get('name') != container:
                continue
            if _container.get('logConfiguration', {}).get('logDriver') == 'awslogs':
                opt = _container.get('logConfiguration', {}).get('options', {})
                if opt.get('awslogs-group'):
                    awslogs_group.append(opt.get('awslogs-group'))
                    if opt.get('awslogs-stream-prefix'):
                        awslogs_stream.append(opt.get('awslogs-stream-prefix'))
                    else:
                        msg = 'Log configuration don\'t have `awslogs-stream-prefix` configuration.'
                        info.append((_container.get('name'), msg))
                else:
                    msg = 'Log configuration don\'t have `awslogs-group` configuration.'
                    info.append((_container.get('name'), msg))
            else:
                msg = 'Log configuration driver is not `logDriver`.'
                info.append((_container.get('name'), msg))

        if len(awslogs_stream) == 0:
            if info:
                for i in info:
                    print('[{}] {}'.format(*i))
            else:
                return "Select existing container: {}".format(', '.join(containers)), True
        elif len(set(awslogs_group)) > 1:
            return "Select one container to show log because they usage different `awslogs-group`: {}".format(
                ', '.join(containers)), True
        elif awslogs_group:
            prefix = awslogs_stream[0] if container else None
            count_event, count_stream = 0, 0

            if filter_pattern:
                for event in self.__filter_log_events(awslogs_group[0], start_time, end_time, prefix, filter_pattern):
                    templ = self.__log_message(event)
                    count_event += 1
                    print(templ)
                return 'NUMBER OF LOGS: {}'.format(count_event), False
            else:
                events, selected_task = [], None
                if not prefix and len(awslogs_stream) == 1 and len(containers) == 1:
                    selected_task = '{}/{}/{}'.format(awslogs_stream[0], containers[0], task)
                # logStreamNamePrefix: {awslogs_stream_prefix}/{container_definitions.name}/{id}
                streams = self.__get_all_streams(
                    awslogs_group[0], prefix, containers, get_bytes_size=byte_size,
                    start_time=start_time, end_time=end_time, selected_task=selected_task)

                if not start_time and not end_time:
                    from_head = False

                for stream in streams:
                    count_stream += 1
                    for event in self.__get_log_events(
                            awslogs_group[0], stream['logStreamName'], start_time=start_time, end_time=end_time, from_head=from_head):
                        event['logStreamName'] = stream['logStreamName']
                        count_event += 1
                        templ = self.__log_message(event)
                        if not from_head:
                            print(templ)
                        else:
                            events.append((self.__convert_date(event.get('timestamp')), templ))
                if events:
                    events = sorted(events, key=lambda k: k[0])
                    for event in events:
                        print(event[1])
                else:
                    print('[empty log]')
                return '', False
        return "This task don\'t usage CloudWatch Logs.", False

    def __convert_date(self, unixformat):
        return datetime.fromtimestamp(int(str(unixformat)[:-3])).strftime('%Y-%m-%d %H:%M:%S')

    def __log_message(self, event):
        container_name = '\033[94m[{}]\033[0m '.format(event.get('logStreamName').split('/')[0])
        timestamp = '\033[93m{}\033[0m '.format(self.__convert_date(event.get('timestamp')))
        message = event.get('message')
        return '{}{}{}'.format(container_name, timestamp, message)

    def __filter_log_events(self, log_group, start_time=None, end_time=None, log_prefix=None, filter_pattern=None):
        """Generate all the log events from a CloudWatch group.

        :param log_group: Name of the CloudWatch log group.
        :param start_time: Only fetch events with a timestamp after this time.
            Expressed as the number of milliseconds after midnight Jan 1 1970.
        :param end_time: Only fetch events with a timestamp before this time.
            Expressed as the number of milliseconds after midnight Jan 1 1970.
        """
        kwargs = {
            'logGroupName': log_group,
            'limit': 500
        }

        if log_prefix:
            kwargs['logStreamNamePrefix'] = log_prefix
        if start_time is not None:
            kwargs['startTime'] = start_time
        if end_time is not None:
            kwargs['endTime'] = end_time
        if filter_pattern:
            kwargs['filterPattern'] = filter_pattern

        while True:
            resp = self.logs_client.filter_log_events(**kwargs)
            yield from resp['events']

            if not start_time and not end_time:
                break
            if start_time and not end_time:
                break

            try:
                kwargs['nextToken'] = resp['nextToken']
            except KeyError:
                break

    def __get_log_events(self, log_group, log_stream, start_time=None, end_time=None, from_head=True):
        kwargs = {
            'logGroupName': log_group,
            'logStreamName': log_stream,
            'startFromHead': from_head,
            'limit': 500
        }

        if start_time is not None:
            kwargs['startTime'] = start_time
        if end_time is not None:
            kwargs['endTime'] = end_time

        while True:
            resp = self.logs_client.get_log_events(**kwargs)

            yield from resp['events']

            try:
                kwargs['nextToken'] = resp['nextForwardToken']
            except KeyError:
                break

            if not from_head or not resp['events']:
                break

    def __describe_log_streams(self, log_group, prefix=None, selected_task=None):
        kwargs = {
            'logGroupName': log_group,
            'descending': True,
            'orderBy': 'LastEventTime',
            'limit': 50
        }

        if prefix or selected_task:
            kwargs['logStreamNamePrefix'] = prefix or selected_task
            kwargs['orderBy'] = 'LogStreamName'

        while True:
            resp = self.logs_client.describe_log_streams(**kwargs)

            yield from resp['logStreams']

            try:
                kwargs['nextToken'] = resp['nextToken']
            except KeyError:
                break

    def __get_all_streams(self, awslogs_group, prefix=None, containers=None, sort_by='lastEventTimestamp',
                          get_bytes_size=None, start_time=None, end_time=None, selected_task=None):
        streams = []
        for stream in self.__describe_log_streams(awslogs_group, prefix, selected_task):
            add_stream = True
            if not selected_task:
                check_stream = True if prefix else any([x for x in containers if x in stream['logStreamName']])
                add_stream = stream['storedBytes'] > 0 and check_stream
            if add_stream:
                # TODO: add start_time and end_time filter!!!
                if 'firstEventTimestamp' in stream:
                    stream['firstEventTimestamp'] = self.__convert_date(stream['firstEventTimestamp'])
                if 'lastEventTimestamp' in stream:
                    stream['lastEventTimestamp'] = self.__convert_date(stream['lastEventTimestamp'])
                if 'creationTime' in stream:
                    stream['creationTime'] = self.__convert_date(stream['creationTime'])
                if 'lastIngestionTime' in stream:
                    stream['lastIngestionTime'] = self.__convert_date(stream['lastIngestionTime'])
                if 'uploadSequenceToken' in stream:
                    del stream['uploadSequenceToken']
                streams.append(stream)
        streams = sorted(streams, key=lambda k: k.get(sort_by))

        if get_bytes_size > 0 and prefix:
            sum_bytes_size, count = 0, 0
            for stream in streams:
                sum_bytes_size += stream['storedBytes']
                count += 1
                if get_bytes_size < sum_bytes_size:
                    break
            return streams[-abs(count):]
        elif get_bytes_size > 0 and not prefix:
            container_types, _streams = [], []
            for stream in reversed(streams):
                check_container = [x for x in containers if x in stream['logStreamName']]
                if check_container and not check_container[0] in container_types:
                    container_types.append(check_container[0])
                    _streams.append(stream)
                if len(container_types) == len(containers):
                    break
            streams = _streams
        return streams

    def _execute_create_secret(self, param, deploy=None, tmpl=None, **kwargs):
        response = []
        try:
            for _param in param:
                resp = self.ssm.put_parameter(**_param)
                response.append('{} = Version:{}'.format(_param.get('Name'), resp.get('Version')))
        except ClientError as err:
            raise BotoWrapperException("{}".format(str(err)))
        except ParamValidationError as err:
            raise BotoWrapperException("{}\n{}".format(err.fmt.split('\n')[0], err.kwargs['report']))
        return {'response':  '\n'.join(response)}

    def all_secret(self, cluster=None, family_prefix=None, variables=None):
        parameters = {}
        for secret in self.__get_all_secret(cluster=cluster, task_definition_family=family_prefix):
            try:
                cluster, app, value = secret['Name'].split('.')
            except Exception as e:
                continue
            if not cluster in parameters:
                parameters[cluster] = {}
            if not app in parameters[cluster]:
                parameters[cluster][app] = {}
            if not value in parameters[cluster][app]:
                parameters[cluster][app][value] = secret
        row = []
        for cluster_name, value in parameters.items():
            for task_definition_family, vars in value.items():
                if not variables:
                    row.append((cluster_name, task_definition_family, len(vars)))
                else:
                    for key, values in vars.items():
                        row.append((values['Name'], values['Version'], values['LastModifiedDate']))
        return row

    def __get_all_secret(self, **kwargs):
        kwargs['MaxResults'] = 50

        cluster = kwargs.pop('cluster', None)
        task_definition_family = kwargs.pop('task_definition_family', None)
        if cluster and task_definition_family:
            filter_param = {'Key': 'Name', 'Values': ['{}.{}'.format(cluster, task_definition_family)]}
            kwargs['Filters'] = [filter_param]

        while True:
            resp = self.ssm.describe_parameters(**kwargs)
            yield from resp['Parameters']

            try:
                kwargs['NextToken'] = resp['NextToken']
            except KeyError:
                break

    def delete_secret(self, cluster, task_definition_family=None, variable_name=None):
        response, names = {'DeletedParameters': [], 'InvalidParameters': []}, []
        if variable_name:
            for var in variable_name:
                names.append('{}.{}.{}'.format(cluster, task_definition_family, var))
        else:
            for secret in self.__get_all_secret():
                try:
                    cluster, app, value = secret['Name'].split('.')
                except Exception as e:
                    continue
                if app == task_definition_family:
                    names.append(secret['Name'])
        for part in [names[i:i + 10] for i in range(0, len(names), 10)]:
            resp = self.ssm.delete_parameters(Names=part)
            response['DeletedParameters'].extend(resp.get('DeletedParameters', []))
            response['InvalidParameters'].extend(resp.get('InvalidParameters', []))
        return response

    def describe_secret(self, task_definition_family, cluster='default', simple=False):
        parameters, response = [], []
        for secret in self.__get_all_secret(cluster=cluster, task_definition_family=task_definition_family):
            parameters.append(secret.get('Name'))
        if parameters:
            response = self.ssm.get_parameters(Names=parameters, WithDecryption=True)
        return response.get('Parameters', [])

    def all_service_discovery(self):
        response = self.servicediscovery.list_namespaces(MaxResults=100)
        return response.get('Namespaces')

    def describe_service_discovery(self, namespace_id, show_all=False):
        param = dict(MaxResults=100)
        if not show_all:
            param['Filters'] = [
                {
                    'Name': 'NAMESPACE_ID',
                    'Values': [namespace_id],
                    'Condition': 'EQ'
                },
            ]
        try:
            out = self.servicediscovery.list_services(**param).get('Services')
        except:
            out = []
        return out

    def all_load_balancer(self):
        try:
            out = self.elb.describe_load_balancers(PageSize=100)['LoadBalancers']
        except:
            out = []
        return out

    def all_hosted_zone(self):
        try:
            out = self.route53.list_hosted_zones(MaxItems="100")['HostedZones']
        except:
            out = []
        return out

    def all_resource_record(self, hosted_zone_id=None):
        try:
            out = self.route53.list_resource_record_sets(HostedZoneId=hosted_zone_id).get('ResourceRecordSets')
        except:
            out = []
        return out
