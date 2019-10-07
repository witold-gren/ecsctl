import re
import pytz
import pprint
import datetime
import stringcase


def convert_to_snakecase(data, delete_empty_values=True):
    """
    stringcase.snakecase('fooBarBaz') # => "_foo_bar_baz"
    """
    EXCEPTIONS_CHILD = ['dockerLabels']

    if isinstance(data, dict):
        _data = {}
        for key, value in data.items():
            _key = stringcase.snakecase(key)
            if delete_empty_values and not isinstance(value, int) and not value:
                continue
            if key in EXCEPTIONS_CHILD:
                _value = value
            else:
                _value = convert_to_snakecase(value, delete_empty_values)
            _data[_key] = _value
        return _data
    elif isinstance(data, list):
        _list = []
        for value in data:
            _list.append(convert_to_snakecase(value, delete_empty_values))
        return _list
    else:
        return data


def convert_to_camelcase(data):
    """
    stringcase.camelcase('foo_bar_baz') # => "fooBarBaz"
    """
    EXCEPTIONS = ['awslogs_group', 'awslogs_region', 'awslogs_stream_prefix']
    EXCEPTIONS_CHILD = ['docker_labels']

    if isinstance(data, dict):
        _data = {}
        for key, value in data.items():
            if key in EXCEPTIONS:
                _key = key.replace('_', '-')
            else:
                _key = stringcase.camelcase(key)
            if key in EXCEPTIONS_CHILD:
                _value = value
            else:
                _value = convert_to_camelcase(value)
            _data[_key] = _value
        return _data
    elif isinstance(data, list):
        _list = []
        for value in data:
            _list.append(convert_to_camelcase(value))
        return _list
    else:
        return data


def secret_name(cluster, app, variable):
    return "{}.{}.{}".format(cluster, app, variable)


class ProxyTemplate:

    def __init__(self, name=None, tags=None, yaml=None, json=None, clean=True, cluster=None, **kwargs):
        self.name = name
        self.yaml = convert_to_camelcase(yaml) if yaml else yaml
        self.json = convert_to_snakecase(json, clean) if json else json
        self.tags = tags
        self.cluster = cluster

    def run_before(self, *args, **kwargs):
        pass

    def run_after(self, *args, **kwargs):
        pass

    def to_file(self):
        raise NotImplementedError

    def to_request(self):
        raise NotImplementedError

    def _generate_template(self):
        self.template['metadata']['name'] = self.name
        self.template['spec'] = self.json
        if self.tags:
            self.template['metadata']['tags'] = self.tags
        return self.template

    def _to_human_envs(self):
        """
        FROM:
        environment:
        - name: SECRETS_BUCKET_NAME
          value: rg-dev-ecs-config

        TO:
        environment:
        - SECRETS_BUCKET_NAME=rg-dev-ecs-config
        """
        # https://deployfish.readthedocs.io/en/latest/yaml.html#secrets-management-with-aws-parameter-store
        # TODO: `- PASSWORD1:secure=${env.PASSWORD1}` - pobranie z zmiennych środowiskowych
        # TODO: `environment_file: config.env` - pobranie z pliku w lokalnym katalogu
        # TODO: `VARIABLE:secure:arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab=VALUE`

        container_definitions = []
        for container in self.json.pop('container_definitions'):
            container['environment'] = self._to_human_list(container.pop('environment', []))
            container_definitions.append(container)
        self.json['container_definitions'] = container_definitions

    def _to_human_ports(self):
        """
        FROM:
        port_mappings:
          - containerPort: 80
            hostPort: 80
            protocol: tcp
        TO:
        port_mappings:
          - "80"
          - "8443:443"
          - "8125:8125/udp"
        """
        container_definitions = []
        for container in self.json.pop('container_definitions'):
            ports = []
            for port in container.pop('port_mappings', []):
                port_conf = ""
                h_port, c_port, proto = port.get('host_port'), port.get('container_port'), port.get('protocol')
                if proto != 'tcp':
                    port_conf = '{}:{}/{}'.format(h_port, c_port, proto)
                elif h_port == c_port:
                    port_conf = h_port
                elif h_port != c_port:
                    port_conf = '{}:{}'.format(h_port, c_port)
                if port_conf:
                    ports.append(port_conf)
            container['port_mappings'] = ports
            container_definitions.append(container)
        self.json['container_definitions'] = container_definitions

    def _from_human_envs(self):
        """
        FROM:
        environment:
        - SECRETS_BUCKET_NAME=rg-dev-ecs-config

        TO:
        environment:
        - name: SECRETS_BUCKET_NAME
          value: rg-dev-ecs-config
        """
        # https://deployfish.readthedocs.io/en/latest/yaml.html#secrets-management-with-aws-parameter-store
        # TODO: `- PASSWORD1:secure=${env.PASSWORD1}` - pobranie z zmiennych środowiskowych
        # TODO: `environment_file: config.env` - pobranie z pliku w lokalnym katalogu
        # TODO: `VARIABLE:secure:arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab=VALUE`
        container_definitions = []
        for container in self.yaml.pop('containerDefinitions'):
            container['environment'] = self._from_human_list(container.pop('environment', []))
            container_definitions.append(container)
        self.yaml['containerDefinitions'] = container_definitions

    def _from_human_ports(self):
        """
        FROM:
        port_mappings:
          - "80"
          - "8443:443"
          - "8125:8125/udp"

        TO:
        port_mappings:
          - containerPort: 80
            hostPort: 80
            protocol: tcp
        """
        container_definitions = []
        for container in self.yaml.pop('containerDefinitions'):
            ports = []
            for port in container.pop('portMappings', []):
                reg = re.findall(r'(\d+)(\:)?(\d+)?(\/)?(udp|tcp)?', str(port))
                if reg:
                    h_port, _, c_port, _, protocol = reg[0]
                    if not c_port:
                        c_port = h_port
                    if not protocol:
                        protocol = 'tcp'
                    ports.append({'hostPort': int(h_port), 'containerPort': int(c_port), 'protocol': protocol})
            container['portMappings'] = ports
            container_definitions.append(container)
        self.yaml['containerDefinitions'] = container_definitions

    @staticmethod
    def _to_human_list(data, key='name', value='value'):
        """
        FROM:
        environment:
        - name: KEY1
          value: value1
        - name: KEY2
          value: value2

        TO:
        tags:
          - KEY1=value1
          - KEY2=value2
        """
        _empty = []
        if data:
            for item in data:
                _empty.append('{}={}'.format(item.get(key), item.get(value)))
            return _empty
        return data

    @staticmethod
    def _to_human_dict(data, key='name', value='value'):
        """
        FROM:
        tags:
        - key: KEY1
          value: value1
        - key: KEY2
          value: value2

        TO:
        tags:
          KEY1: value1
          KEY2: value2
        """
        _empty = {}
        if data:
            for item in data:
                _empty[item.get(key)] = item.get(value)
            return _empty
        return data

    @staticmethod
    def _from_human_list(data, key='name', value='value'):
        """
        FROM:
        tags:
          - KEY1=value1
          - KEY2=value2

        TO:
        environment:
        - name: KEY1
          value: value1
        - name: KEY2
          value: value2
        """
        _empty = []
        if data:
            for item in data:
                _key, *_value = item.split('=')
                _empty.append({key: _key, value: '='.join(_value)})
            return _empty
        return data

    @staticmethod
    def _from_human_dict(data, key='name', value='value'):
        """
        FROM:
        tags:
          KEY1: value1
          KEY2: value2

        TO:
        tags:
        - key: KEY1
          value: value1
        - key: KEY2
          value: value2
        """
        _empty = []
        if data:
            print(data)
            for _key, _value in data.items():
                _empty.append({key: _key, value: _value})
            return _empty
        return data


class TaskDefinition(ProxyTemplate):
    template_name = "TaskDefinition"
    response = "taskDefinition.taskDefinitionArn"
    template = {
        "apiVersion": "v1",
        "kind": "TaskDefinition",
        "metadata": {
            "name": None,
        },
        "spec": None
    }

    def to_file(self, **kwargs):
        # inferenceAccelerators do't work when describe
        self.name = self.json.pop('family')
        self.tags = self._to_human_dict(self.json.pop('tags', []))
        self._to_human_ports()
        self._to_human_envs()
        self._to_human_secrets()
        return self._generate_template()

    def to_request(self, **kwargs):
        self.yaml['family'] = self.name
        tags = self._from_human_dict(self.tags)
        if tags:
            self.yaml['tags'] = tags
        if not self.yaml.get('cpu') is None:
            self.yaml['cpu'] = str(self.yaml['cpu'])
        if not self.yaml.get('memory') is None:
            self.yaml['memory'] = str(self.yaml['memory'])
        self._from_human_envs()
        self._from_human_ports()
        return self.yaml

    def _from_human_secrets(self, boto_wrapper):
        """
        FROM:
        secrets:
          - ENV_VAR

        TO:
        secrets:
          - name: ENV_VAR
            valueFrom: arn:aws:ssm:us-west-2:111122223333:parameter/CLUSTER_NAME.TASK_DEFINITION.ENV_VAR
        """
        add_execution_role_arn = False
        container_definitions = []
        for container in self.yaml.pop('containerDefinitions'):
            secrets, secrets_param = [], []
            for var in container.pop('secrets', []):
                secrets_param.append(secret_name(self.cluster, self.name, var))
            if secrets_param:
                add_execution_role_arn = True
                response = boto_wrapper.ssm.get_parameters(
                    Names=secrets_param, WithDecryption=False)
                if response['InvalidParameters']:
                    raise ValueError('Incorrect params: {}'.format(', '.join(response['InvalidParameters'])))
                for x in response['Parameters']:
                    name = x.get('Name').split('.')[-1]
                    secrets.append({'name': name, 'valueFrom': x.get('ARN')})
                container['secrets'] = secrets
            container_definitions.append(container)
        self.yaml['containerDefinitions'] = container_definitions
        if add_execution_role_arn and not 'executionRoleArn' in self.yaml:
            aws_account_id = boto_wrapper.sts.get_caller_identity()['Account']
            execution_role = 'arn:aws:iam::{}:role/{}_ecs_parameter_store_task_definition_role'.format(
                aws_account_id, self.cluster)
            self.yaml['executionRoleArn'] = execution_role

    def _to_human_secrets(self):
        """
        FROM:
        secrets:
          - name: ENV_VAR
            valueFrom: arn:aws:ssm:us-west-2:111122223333:parameter/CLUSTER_NAME.TASK_DEFINITION.ENV_VAR
        TO:
        secrets:
          - ENV_VAR
        """
        container_definitions = []
        for container in self.json.pop('container_definitions'):
            secrets = []
            for secret in container.pop('secrets', []):
                task_name = re.findall(r'.+\/(.+)\.(.+)\.(.+)$', secret['value_from'])
                if task_name:
                    cluster, task_definition, var = task_name[0]
                    if self.cluster == cluster and self.name == task_definition and var == secret['name']:
                        secrets.append(secret['name'])
                else:
                    secrets.append(secret)
            if secrets:
                container['secrets'] = secrets
            container_definitions.append(container)
        self.json['container_definitions'] = container_definitions

    def _check_aws_group(self, boto_wrapper):
        # check cloud watch
        for _container in self.yaml['containerDefinitions']:
            if _container.get('logConfiguration', {}).get('logDriver') == 'awslogs':
                group = _container.get('logConfiguration', {}).get('options', {}).get('awslogs-group', None)
                response = None
                if group:
                    response = boto_wrapper.logs_client.describe_log_groups(logGroupNamePrefix=group)
                if not response['logGroups']:
                    boto_wrapper.logs_client.create_log_group(logGroupName=group, tags={'Cluster': self.cluster})

    def run_before(self, boto_wrapper=None):
        self._from_human_secrets(boto_wrapper)
        self._check_aws_group(boto_wrapper)


class Service(ProxyTemplate):
    template_name = "Service"
    response = "service.serviceArn"
    template = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": None
        },
        "spec": None
    }

    def to_file(self, **kwargs):
        self.name = self.json.pop('service_name')
        self.tags = self._to_human_dict(self.json.pop('tags', []))
        self.json['cluster'] = self.json.pop('cluster_arn', None)
        self.json['role'] = self.json.pop('role_arn', None)
        if not 'deployment_controller' in self.json:
            self.json['deployment_controller'] = {'type': 'ECS'}
        if 'propagate_tags' in self.json:
            if self.json.get('propagate_tags') == "NONE":
                del self.json['propagate_tags']
        if 'enable_e_c_s_managed_tags' in self.json:
            data = self.json.pop('enable_e_c_s_managed_tags')
            self.json['enable_ecs_managed_tags'] = data
        if 'role' in self.json and not self.json['role']:
            del self.json['role']
        return self._generate_template()

    def to_request(self, **kwargs):
        self.yaml['serviceName'] = self.name
        if not 'cluster' in self.yaml:
            self.yaml['cluster'] = self.cluster
        tags = self._from_human_dict(self.tags)
        if tags:
            self.yaml['tags'] = tags
        if 'enable_ecs_managed_tags' in self.yaml:
            data = self.yaml.pop('enable_ecs_managed_tags')
            self.yaml['enableECSManagedTags'] = data
        return self.yaml


class Task(ProxyTemplate):
    template_name = "Task"
    response = "."
    template = {
        "apiVersion": "v1",
        "kind": "Task",
        "metadata": {
            "name": None
        },
        "spec": None
    }

    def to_file(self, **kwargs):
        task_definition_arn = self.json.pop('task_definition_arn')
        now = datetime.datetime.now(pytz.utc).strftime("%Y-%m-%d-%H-%M-%S")
        name = re.findall(r'^.+\/(.+)\:.+?', task_definition_arn)[0]
        self.name = '{}-{}'.format(name, now)
        self.json['cluster'] = self.json.pop('cluster_arn', None)
        if not 'task_definition' in self.json:
            self.json['task_definition'] = task_definition_arn
        if not 'count' in self.json:
            self.json['count'] = 1
        if not 'placementConstraints' in self.json:
            self.json['placementConstraints'] = []
        if not 'placementStrategy' in self.json:
            self.json['placementStrategy'] = []
        if not 'enableECSManagedTags' in self.json:
            self.json['enableECSManagedTags'] = False
        if not 'propagateTags' in self.json:
            self.json['propagateTags'] = False
        return self._generate_template()

    def to_request(self, **kwargs):
        return self.yaml


class Secret(ProxyTemplate):
    response = "response"
    template_name = "Secret"
    template = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {
            "name": None,
            'key_id': None
        },
        "spec": None
    }

    def __init__(self, name=None, tags=None, yaml=None, json=None, clean=True, cluster=None, **kwargs):
        self.name = name
        self.yaml = yaml
        self.json = json
        self.tags = tags
        self.cluster = cluster
        self.exist = None
        self.not_exist = None
        self.key_id = kwargs.get('metadata', {}).get('key_id', None)

    def to_file(self):
        app = None
        if not self.template['metadata']['key_id']:
            del self.template['metadata']['key_id']
        spec = {}
        for x in self.json:
            _, app, var = x.get('Name').split('.')
            spec[var] = x['Value']
        self.template['metadata']['name'] = app
        self.template['spec'] = spec
        return self.template

    def to_request(self, **kwargs):
        if self.exist is None or self.not_exist is None:
            self.run_before()
        resp = []
        for key, value in self.yaml.items():
            name = secret_name(self.cluster, self.name, key)
            param = dict(
                Name=name,
                Value=value,
                Type='SecureString',
                Tier='Standard')
            if name in self.not_exist:
                param['Overwrite'] = False
                param['Tags'] = [
                    {'Key': 'cluster', 'Value': self.cluster},
                    {'Key': 'task-definition-family', 'Value': self.name},
                    {'Key': 'variable', 'Value': key}]
            elif name in self.exist:
                param['Overwrite'] = True
            else:
                raise ValueError('This param in incorrect: {}'.format(key))
            if self.key_id:
                param['KeyId'] = self.key_id
            resp.append(param)
        return resp

    def _check_params(self, boto_wrapper):
        names = [secret_name(self.cluster, self.name, key) for key in self.yaml.keys()]
        parameters, invalid_parameters = [], []
        for name_part in [names[i:i + 10] for i in range(0, len(names), 10)]:
            response = boto_wrapper.ssm.get_parameters(
                Names=name_part, WithDecryption=False)
            parameters.extend([x.get('Name') for x in response.get('Parameters', [])])
            invalid_parameters.extend(response.get('InvalidParameters', []))
        self.exist = parameters
        self.not_exist = invalid_parameters

    def run_before(self, boto_wrapper=None):
        self._check_params(boto_wrapper)


class Scaling(ProxyTemplate):
    template_name = "Scaling"
    template = {
        "apiVersion": "v1",
        "kind": "Scaling",
        "metadata": {
            "name": None
        },
        "spec": None
    }

    def to_file(self):
        pass

    def to_request(self):
        pass
