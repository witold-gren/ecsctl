Service
-------

Django app
^^^^^^^^^^

.. code:: yaml

    apiVersion: v1
    kind: Service
    metadata:
      name: my-app
    spec:
      task_definition: my-app
      desired_count: 1
      launch_type: EC2
      scheduling_strategy: REPLICA
      deployment_configuration:
        maximum_percent: 200
        minimum_healthy_percent: 50
      deployment_controller:
        type: ECS


Postgres
^^^^^^^^

.. code:: yaml

    apiVersion: v1
    kind: Service
    metadata:
      name: my-postgresql
    spec:
      task_definition: my-postgresql
      desired_count: 1
      launch_type: EC2
      scheduling_strategy: REPLICA
      service_registries:
        - registry_arn:
          container_name: postgres
          container_port: 5432
          _namespace: dev.local
      deployment_configuration:
        maximum_percent: 200
        minimum_healthy_percent: 50
      deployment_controller:
        type: ECS


Redis
^^^^^

.. code:: yaml

    apiVersion: v1
    kind: Service
    metadata:
      name: my-redis
    spec:
      task_definition: my-redis
      desired_count: 1
      launch_type: EC2
      scheduling_strategy: REPLICA
      service_registries:
        - registry_arn:
          container_name: redis
          container_port: 6379
          _namespace: dev.local
      deployment_configuration:
        maximum_percent: 200
        minimum_healthy_percent: 50
      deployment_controller:
        type: ECS


Traefik
^^^^^^^

.. code:: yaml

    apiVersion: v1
    kind: Service
    metadata:
      name: my-traefik
    spec:
      task_definition: my-traefik
      desired_count: 1
      launch_type: EC2
      scheduling_strategy: REPLICA
      role: arn:aws:iam::806640025155:role/dev_ecs_traefik_service_role
      load_balancers:
      - target_group_arn: arn:aws:elasticloadbalancing:eu-west-1:000000000000:targetgroup/Traefik-dev-traefik/aef5ce4876180c5b
        container_name: traefik
        container_port: 80
      placement_strategy:
      - type: spread
        field: attribute:ecs.availability-zone
      - type: spread
        field: instanceId
      deployment_configuration:
        maximum_percent: 200
        minimum_healthy_percent: 50
      deployment_controller:
        type: ECS
