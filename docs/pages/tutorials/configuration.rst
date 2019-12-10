*************
Configuration
*************

You must have the necessary privileges to configure the cluster. Also some functionality need extra privileges to work correctly.
This tutorial not cover this functionality (AWS IAM Roles). For the future we will prepare example IAM Roles to get access
to specific functionality. Before you start configure you cluster please check configuration option:

.. code-block:: bash

    $ ecsctl config --help

    Usage: ecsctl config [OPTIONS] COMMAND [ARGS]...

    Options:
      --help  Show this message and exit.

    Commands:
      context  # Change default cluster to another cmd::ecsctl config context my-own-config-name-2
      set      # Create configuration for new cluster usage aws profile cmd::ecsctl config set my-own-config-name...
      show     # Show configuration for default cluster cmd::ecsctl config show # Show configuration for all...


If you need see all parameter and many examples show help in set parameter.

.. code-block:: bash

    $ ecsctl config set --help

    Usage: ecsctl config set [OPTIONS] NAME

      # Create configuration for new cluster usage aws profile
      ecsctl config set my-own-config-name --cluster-name my-cluster --aws-profile my-aws-profile

      # Create configuration for new cluster usage access-key and secret-access
      ecsctl config set my-own-config-name --cluster-name my-cluster --aws-access-key-id XXX --aws-secret-access-key YYY --aws-region ZZZ

      # Set bastion host IP and ssh key
      ecsctl config set my-own-config-name --ssh-bastion-ip 1.2.3.4 --ssh-key-location ~/.ssh/my_extra_key

    Options:
      --cluster-name TEXT
      --aws-access-key-id TEXT
      --aws-secret-access-key TEXT
      --aws-region TEXT
      --aws-session-token TEXT
      --aws-profile TEXT
      --ssh-user TEXT               [default: ec2-user]
      --ssh-bastion-user TEXT       [default: ec2-user]
      --ssh-bastion-ip TEXT
      --ssh-key-location TEXT       [default: ~/.ssh/id_rsa]
      --help                        Show this message and exit.


Configuration Parameters
^^^^^^^^^^^^^^^^^^^^^^^^

*cluster-name*
    your cluster name

*aws-access-key-id*
    your aws access key id if you don't usage IAM Role and AWS Profile

*aws-secret-access-key*
    your aws secret key if you don't usage IAM Role and AWS Profile

*aws-region*
    aws region when cluster was running

*aws-session-token*
    aws session token

*aws-profile*
    aws profile if you usage cross account permission

*ssh-user*
    user name for login to EC2 instance `[default: ec2-user]`

*ssh-bastion-user*
    user name in bastin host to login to EC2 instance `[default: ec2-user]`

*ssh-bastion-ip*
    bastion host ip address

*ssh-key-location*
    path to your ssh key `[default: ~/.ssh/id_rsa]`


Configure by environment variables
==================================

If you need configure cluster access you are able usage virtual environments. Please set this variables:

.. code-block:: bash

    $ export AWS_ECS_CLUSTER_NAME=<your cluster name>
    $ export AWS_ACCESS_KEY_ID=<your aws access key id if you don't usage IAM Role>
    $ export AWS_SECRET_ACCESS_KEY=<your aws secret key if you don't usage IAM Role>
    $ export AWS_DEFAULT_REGION=<aws region when cluster was running>
    $ export AWS_SESSION_TOKEN=<aws session token>
    $ export AWS_PROFILE=<aws profile if you usage cross account permission>
    $ export AWS_ECS_SSH_USER=<user name for login to EC2 instance>
    $ export AWS_ECS_SSH_BASTION_USER=<user name in bastin host to login to EC2 instance>
    $ export AWS_ECS_SSH_BASTION_IP=<bastion host ip address>
    $ export AWS_ECS_SSH_KEY_LOCATION=<path to your ssh key>


Configure by aws profile
========================

Create configuration for new cluster usage aws profile.

.. code-block:: bash

    $ ecsctl config set my-own-cluster-name --cluster-name aws-ecs-cluster-name --aws-profile my-aws-profile

example:

.. code-block:: bash

    $ ecsctl config set dev --cluster-name project-dev --aws-profile project-profile


Configure by access_key and secret_access_key
=============================================

Create configuration for new cluster usage access_key and secret_access_key.

.. code-block:: bash

    $ ecsctl config set my-own-cluster-name --cluster-name aws-ecs-cluster-name --aws-access-key-id XXX --aws-secret-access-key YYY --aws-region ZZZ

example:

.. code-block:: bash

    $ ecsctl config set dev --cluster-name project-dev --aws-access-key-id QTIDJO2GG165XAE1T2BA --aws-secret-access-key i9OP7lwv-qEr3768o+Ayiy|Ha\ZgxrLvLYdE5RcQ --aws-region us-east-1


Configure other parameters
==========================

This parameters is necessary if you need usage `exec` command to connect with you docker. By default `ecsctl` also configure other parameters:

* AWS_ECS_SSH_USER=ec2-user
* ssh_user=ec2-user
* ssh_bastion_user=ec2-user
* ssh_key_location=~/.ssh/id_rsa

If you need set extra parameters also usage this configuration:

.. code-block:: bash

    $ ecsctl config set my-own-config-name --ssh-bastion-ip 1.2.3.4 --ssh-key-location ~/.ssh/my_extra_key


.. code-block:: bash

    $ ecsctl config set my-own-config-name --ssh-user developer --ssh-bastion-user ubuntu --ssh-bastion-ip 1.2.3.4 --ssh-key-location ~/.ssh/cluster_developer_key


Check configuration
===================

After finish configuration your cluster check that everything was set correctly:

.. code-block:: bash

    $ ecsctl config show

    [dev]
    cluster = DEV
    aws_profile = my-profile
    ssh_bastion_ip = 1.2.3.4
    ssh_key_location = /Users/user/.ssh/my_key
    ssh_user = ec2-user
    ssh_bastion_user = ec2-user

If you have more clusters you also are able check all configuration:

.. code-block:: bash

    $ ecsctl config show --show-all

    [ecsctl]
    context = dev

    [dev]
    cluster = DEV
    aws_profile = my-profile
    ssh_bastion_ip = 1.2.3.4
    ssh_key_location = /Users/user/.ssh/my_key_dev
    ssh_user = ec2-user
    ssh_bastion_user = ec2-user

    [stg]
    cluster = STG
    aws_profile = my-profile-stg
    ssh_bastion_ip = 2.3.4.5
    ssh_key_location = /Users/user/.ssh/my_key_stg
    ssh_user = ec2-user
    ssh_bastion_user = ec2-user

    [prd]
    cluster = PRD
    aws_profile = my-profile-prd
    ssh_bastion_ip = 3.4.5.6
    ssh_key_location = /Users/user/.ssh/my_key_prd
    ssh_user = ec2-user
    ssh_bastion_user = ec2-user

Also your ar able check where is your configuration file if you need create backup.


.. code-block:: bash

    $ ecsctl config show --show-path

    /Users/developer/.ecsctl/config
    [dev]
    cluster = DEV
    aws_profile = my-profile
    ssh_bastion_ip = 1.2.3.4
    ssh_key_location = /Users/user/.ssh/my_key_dev
    ssh_user = ec2-user
    ssh_bastion_user = ec2-user


Switch cluster
==============

Last option is change context between clusters. The following command changes the context to a current cluster:

.. code-block:: bash

    $ ecsctl config context prd
