Sercets
=======

Django app
^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: yaml

    apiVersion: v1
    kind: Secret
    metadata:
      name: my-app
    spec:
      DJANGO_SECRET_KEY: secret-key
      POSTGRES_DB: my-db
      POSTGRES_USER: my-user
      POSTGRES_PASSWORD: my-password


Postgresql
^^^^^^^^^^

.. code:: yaml

    apiVersion: v1
    kind: Secret
    metadata:
      name: my-postgresql
    spec:
      DJANGO_SECRET_KEY: secret-key
      POSTGRES_DB: my-db
      POSTGRES_USER: my-user
      POSTGRES_PASSWORD: my-password
