************
Before start
************

Before you start working with `ecsctl` check that tool was install correctly.

.. code-block:: bash

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

As you can see you have a lot of options to work with cluster. If you need see some example of one option also try usage help.


.. code-block:: bash

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
