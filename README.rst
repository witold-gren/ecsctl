ecsctl
======

kubectl-style command line tool for AWS EC2 Container Service (ECS). This tool is alpha version and contains
bugs and not catched exceptions. Also to usage all feature in you cluster must exist specific configuration: eg.
`IAM Roles`, `AWSS cloudwatch-agent`, `ecs agent configuration` and much more.

I will prepare more examples and documentation when ecsctl will stable.

Big thanks for Xiuming Chen for first iteration of this project https://github.com/cxmcc/ecsctl I added much more new
features (it will problematic to cerate lot of pull requests) to this project so I decide create another repository.


Installation
------------

.. code:: bash

    pip install git+https://github.com/witold-gren/ecsctl.git

Purpose
-------

A convenient command line tool to view ECS cluster status and do
troubleshooting.

This tool is trying to provide similar functionality of ``kubectl`` for
kubernetes.

Of course, ECS and kubernetes are so different. Many features on
kubernetes are not possible here in ECS.

Usage
-----

.. code:: bash

    $ ecsctl --help

    Usage: ecsctl [OPTIONS] COMMAND [ARGS]...

    Options:
      --help  Show this message and exit.

    Commands:
      apply     Create or update resources.
      config    Manage config file.
      create    Create resources.
      delete    Delete resources.
      describe  Show details of a specific resource.
      drain     Drain container instance.
      exec      Execute a command in a container.
      get       Display one or many resources.
      logs      Print the logs for a container usage CloudWatch.
      run       Run a particular image on the cluster.
      scale     Set a new size for a Service.
      stop      Stop service.
      top       Display Resource (CPU/Memory) usage.
      undrain   Undrain node back into active status.
      update    Update resources.


    $ ecsctl get --help

    Usage: ecsctl get [OPTIONS] COMMAND [ARGS]...

    Options:
      --help  Show this message and exit.

    Commands:
      cluster                 List cluster from your account.
      container-instance      List container instances from your cluster.
      hosted-zones            List hosted zones from your account.
      loadbalancer            List load balancer from your account.
      secret                  List secret group from your account.
      service                 List services from your cluster.
      service-discovery       List service discovery namespace from your account.
      task                    List task from your cluster.
      task-definition         List task definition from your cluster.
      task-definition-family  List task definition family from your cluster.


Configure
^^^^^^^

Configure environment variables for usage ecscli

.. code:: bash

    $ export AWS_ECS_CLUSTER_NAME=xxx
    $ export AWS_ACCESS_KEY_ID=xxx
    $ export AWS_SECRET_ACCESS_KEY=xxx
    $ export AWS_DEFAULT_REGION=xxx
    $ export AWS_SESSION_TOKEN=xxx
    $ export AWS_PROFILE=xxx
    $ export AWS_ECS_SSH_USER=xxx
    $ export AWS_ECS_SSH_BASTION_USER=xxx
    $ export AWS_ECS_SSH_BASTION_IP=xxx
    $ export AWS_ECS_SSH_KEY_LOCATION=xxx

Create configuration for new cluster usage aws profile

.. code:: bash

    $ ecsctl config set my-own-config-name --cluster-name my-cluster --aws-profile my-aws-profile

Create configuration for new cluster usage access-key and secret-access

.. code:: bash

    $ ecsctl config set my-own-config-name --cluster-name my-cluster --aws-access-key-id XXX --aws-secret-access-key YYY --aws-region ZZZ

Set docker port for existing cluster

.. code:: bash

    $ ecsctl config set my-own-config-name --docker-port 64646

Set docker api version for existing cluster

.. code:: bash

    $ ecsctl config set my-own-config-name --docker-api-version 1.30


Show configuration
^^^^^^^^^^^^^^^^^^

Show configuration for default cluster

.. code:: bash

    $ ecsctl config show

Show configuration for all configured clusters

.. code:: bash

    $ ecsctl config show --show-all

Show path for config file

.. code:: bash

    $ ecsctl config show --show-path


Switch context
^^^^^^^^^^^^^^

Switch default cluster:

.. code:: bash

    $ ecsctl config context default2


Cluster
^^^^^^^

List clusters:

.. code:: bash

    $ ecsctl get clusters
    NAME                    STATUS      RUNNING    PENDING    INSTANCE COUNT
    default                 ACTIVE            5          0                 1

    $ ecsctl get cluster --sort-by "settings[0].name"
    NAME                    STATUS      RUNNING    PENDING    INSTANCE COUNT
    default                 ACTIVE            5          0                 1

    $ ecsctl get cluster --quiet
    learning-10c-ecs-local

Get cluster details:

.. code:: bash

    $ ecsctl describe cluster default


Check CPU/Memory utilization:

.. code:: bash

    $ ecsctl top cluster

Show avaraged usage resource from last 1h (Current we have 20 September 2019 12:35)

.. code:: bash

    $ ecsctl top cluster --start-time 2019-09-20T12:35:00

Show avaraged usage resource from last 1d

.. code:: bash

    ecsctl top cluster --start-time 2019-09-20T12:35:00 --end-time 2019-09-19T12:35:00


Container Instances (nodes)
^^^^^^^^^^^^^^^^^^^^^^^^^^^

List nodes:

.. code:: bash

    % ecsctl get nodes --cluster mycluster
    INSTANCE ID                           EC2 INSTANCE ID      STATUS      RUNNING COUNT
    00000000-1111-2222-3333-444444444444  i-abcdef123456abcde  ACTIVE                  1

Get node detail:

.. code:: bash

    % ecsctl describe node 00000000-1111-2222-3333-444444444444


Drain/undrain node:

.. code:: bash

    % ecsctl drain 00000000-1111-2222-3333-444444444444

Services
^^^^^^^^

List services:

.. code:: bash

    % ecsctl get services

List services in certain order:

.. code:: bash

    % ecsctl get services --sort-by "createdAt"

Delete a service:

.. code:: bash

    % ecsctl delete service badservice

Delete a service (even if it has desiredCount > 0):

.. code:: bash

    % ecsctl delete service badservice --force


Run container quick start
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: bash

    % ecsctl run mycontainer --image busybox
    mycontainer

    % ecsctl get services
    NAME             TASK DEFINITION      DESIRED    RUNNING  STATUS    AGE
    mycontainer-svc  mycontainer:1              1          0  ACTIVE    10 seconds ago


Run docker exec on containers (Requires customizing docker daemon to listen on internal addresses)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: bash

    % ecsctl get tasks
    TASK ID                               STATUS    TASK DEFINITION    AGE
    42f052c4-80e9-411d-bea2-407b0b4a4b0b  PENDING   mycontainer:1      2 minutes ago
