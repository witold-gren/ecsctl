import subprocess


class Pty:
    def __init__(self, bw=None, task=None, command=(),
                 stdin=False, tty=False, cluster='default', container=None,
                 ssh_user=None, ssh_bastion_user=None, ssh_bastion_ip=None, ssh_key_location=None):
        self.bw = bw
        self.task = task
        self.command = command
        self.stdin = stdin
        self.tty = tty
        self.cluster = cluster
        self.container = container
        self.ssh_user = ssh_user
        self.ssh_bastion_user = ssh_bastion_user
        self.ssh_bastion_ip = ssh_bastion_ip
        self.ssh_key_location = ssh_key_location

    def get_ecs_hostname_of_task(self):
        info = self.bw.describe_task(self.task, cluster=self.cluster)
        ecs_containers = info['containers']
        first_container_id, first_container_name, container_id = None, None, None
        for c in ecs_containers:
            if not first_container_id:
                first_container_id = c.get('runtimeId')
            if not first_container_name:
                first_container_name = c.get('name')
            if c.get('name') == self.container:
                container_id = c.get('runtimeId')
                break
        if not self.container:
            self.container = first_container_name
        if not container_id:
            container_id = first_container_id
        if info['launchType'] == 'FARGATE':
            raise Exception('"exec" does not work with FARGATE.')
        private_ip = info['containerInstance'][0]['ec2_data'].get('PrivateIpAddress')
        public_ip = info['containerInstance'][0]['ec2_data'].get('PublicIpAddress')
        return container_id, private_ip, public_ip

    def _get_container_id_from_ssh(self, base_cmd):
        cmd = "{base_cmd} docker ps --filter \"name={container_name}\" | " \
              "grep -w \"{container_name}\" | " \
              "awk '{{print $1}}'".format(base_cmd=base_cmd, container_name=self.container)
        resp = subprocess.check_output(cmd, shell=True)
        return resp.decode("utf-8").strip()

    def _add_ssh_key(self):
        process = subprocess.run(['ssh-add', self.ssh_key_location])
        if process.returncode != 0:
            raise Exception('failed to add the key: {}'.format(self.ssh_key_location))

    def exec_command(self):
        container_id, private_ip, public_ip = self.get_ecs_hostname_of_task()

        if not public_ip:
            base_cmd = 'ssh -i {key_location} -A -t -o StrictHostKeyChecking=no {bastion_user}@{bastion_ip} ' \
                       'ssh -t -o StrictHostKeyChecking=no {user}@{private_ip}'.format(
                key_location=self.ssh_key_location,
                bastion_user=self.ssh_bastion_user,
                bastion_ip=self.ssh_bastion_ip,
                private_ip=private_ip,
                user=self.ssh_user)
            if not container_id:
                container_id = self._get_container_id_from_ssh(base_cmd)
            cmd = '{base_cmd} docker exec{stdin}{tty} {container_id} {command}'.format(
                stdin=' -i' if self.stdin else '',
                tty=' -t' if self.tty else '',
                base_cmd=base_cmd,
                container_id=container_id,
                command=''.join(self.command))
        else:
            base_cmd = 'ssh -i {key_location} -A -t -o StrictHostKeyChecking=no {user}@{public_ip}'.format(
                key_location=self.ssh_key_location,
                user=self.ssh_user,
                public_ip=public_ip)
            if not container_id:
                container_id = self._get_container_id_from_ssh(base_cmd)
            cmd = '{base_cmd} docker exec{stdin}{tty} {container_id} {command}'.format(
                stdin=' -i' if self.stdin else '',
                tty=' -t' if self.tty else '',
                base_cmd=base_cmd,
                container_id=container_id,
                command=''.join(self.command))

        subprocess.call(cmd, shell=True)

        # TODO: With ssh connection work only from docker 18.09
        # client = docker.APIClient(docker_url, version=self.api_version)
        # resp = client.exec_create(
        #     container_id, self.command, stdin=self.stdin, tty=self.tty
        # )
        # dockerpty.start_exec(client, resp['Id'], interactive=self.stdin)
