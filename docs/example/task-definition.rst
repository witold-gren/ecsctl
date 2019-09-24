Task definition
---------------

Django app
^^^^^^^^^^

.. code:: yaml

    apiVersion: v1
    kind: TaskDefinition
    metadata:
      name: my-app
    spec:
      network_mode: bridge
      task_role_arn: arn:aws:iam::000000000000:role/my-app-s3-access
      cpu: 512
      memory: 512
      container_definitions:
      - name: backend
        port_mappings:
        - 0:8000
        command:
        - /gunicorn.sh
        hostname: backend
        image: my-account/my-repo:my-tag
        cpu: 512
        memory: 512
        memory_reservation: 256
        essential: true
        mount_points:
        - container_path: /app/shared/media
          source_volume: volume-1
        log_configuration:
          log_driver: awslogs
          options:
            awslogs_group: my-project
            awslogs_region: eu-west-1
            awslogs_stream_prefix: backend-stream
        environment:
          - POSTGRES_HOST=my-postgres.dev.local
          - POSTGRES_PORT=5432
          - CONN_MAX_AGE=60
          - DJANGO_READ_DOT_ENV_FILE=False
          - DJANGO_ADMIN_URL=admin/
          - DJANGO_SETTINGS_MODULE=config.settings.production
          - DJANGO_ALLOWED_HOSTS=.dev.example.com
          - DJANGO_AWS_STORAGE_BUCKET_NAME=my-app
          - DJANGO_AWS_S3_REGION_NAME=eu-west-1
          - AWS_DEFAULT_REGION=eu-west-1
          - DJANGO_SECURE_SSL_REDIRECT=False
          - SENTRY_ENVIRONMENT=dev
          - REDIS_URL=my-redis.dev.local
          - CORS_ORIGIN_WHITELIST=http://localhost:3000,https://app.dev.example.com
          - SENTRY_DSN=
        secrets:
          - DJANGO_SECRET_KEY
          - POSTGRES_DB
          - POSTGRES_USER
          - POSTGRES_PASSWORD
        docker_labels:
          traefik.enable: "true"
          traefik.frontend.rule: "Host:backend.dev.example.com"
          traefik.protocol: "http"
          traefik.port: "8000"
      volumes:
        - host:
            source_path: /home/ec2-user/data/my-app
          name: volume-1

Postgres
^^^^^^^^

.. code:: yaml

    apiVersion: v1
    kind: TaskDefinition
    metadata:
      name: my-postgresql
    spec:
      cpu: 512
      memory: 256
      network_mode: bridge
      container_definitions:
      - name: postgres
        image: postgres:11.1
        hostname: postgres
        cpu: 512
        memory: 256
        memory_reservation: 128
        port_mappings:
        - 5432
        mount_points:
        - container_path: /var/lib/postgresql/data
          source_volume: rexray-vol
        log_configuration:
          log_driver: awslogs
          options:
            awslogs_group: my-project
            awslogs_region: eu-west-1
            awslogs_stream_prefix: postgresql
        environment:
        - PGDATA=/var/lib/postgresql/data/pgdata
        secrets:
        - POSTGRES_DB
        - POSTGRES_USER
        - POSTGRES_PASSWORD
      volumes:
      - name: rexray-vol
        docker_volume_configuration:
          autoprovision: true
          scope: shared
          driver: rexray/ebs
          driverOpts:
            volumetype: gp2
            size": "5"


Redis
^^^^^

.. code:: yaml

    apiVersion: v1
    kind: TaskDefinition
    metadata:
      name: my-redis
    spec:
      cpu: 128
      memory: 128
      network_mode: bridge
      container_definitions:
      - name: redis
        image: redis:3.0
        hostname: redis
        cpu: 512
        memory: 128
        memory_reservation: 64
        port_mappings:
        - 6379
        log_configuration:
          log_driver: awslogs
          options:
            awslogs_group: my-project
            awslogs_region: eu-west-1
            awslogs_stream_prefix: redis


Traefik
^^^^^^^

.. code:: yaml

    apiVersion: v1
    kind: TaskDefinition
    metadata:
      name: my-traefik
    spec:
      task_role_arn: arn:aws:iam::000000000000:role/dev_ecs_traefik_task_definition_role
      container_definitions:
      - name: traefik
        image: my-account/my-repository:traefik-cluster-ecs
        cpu: 0
        memory: 512
        memory_reservation: 256
        essential: true
        mount_points:
          - container_path: /var/log/traefik/
            source_volume: volume-logs
        ulimits:
        - name: nofile
          soft_limit: 10240
          hard_limit: 65536
        log_configuration:
          log_driver: awslogs
          options:
            awslogs_group: my-traefik
            awslogs_region: eu-west-1
            awslogs_stream_prefix: traefik
        environment:
        - AWS_REGION=eu-west-1
        - DOMAIN=dev.example.com
        - CLUSTER_HOST=default
        - STACK_NAME=Traefik-dev
        - ENVIRONMENT=dev
        - ACME_CA_SERVER=https://acme-staging-v02.api.letsencrypt.org/directory
        - ACME_EMAIL=myemail@example.com
        port_mappings:
        - 0:80
        - 0:8080
        docker_labels:
          traefik.enable: "true"
          traefik.frontend.rule: "Host:traefik.dev.example.com"
          traefik.protocol: "http"
          traefik.port: "8080"
          traefik.frontend.auth.basic: "superadmin:$2y$05Y09T3ftXeRIQiS9vW6GS2B9O.LVB2WKLKssO9yW6lj8iviICVzQkccy"
      volumes:
        - name: volume-logs
          host:
            source_path: /var/log/ecs/traefik/
