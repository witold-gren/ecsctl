************
Introduction
************

`ecsctl` is commandline tool for managing the whole lifecycle of your application:

* safely and easily create, update, destroy, scale and restart ECS services
* auto create configuration for service discovery
* describe all information about your cluster
* see AWS CloudWatch statistic for nodes and services
* configure many cluster usage one configuration
* usage yaml file to configure all ECS objects
* you don't need extra files to start working with all functionality
* safely and easily create, update, destroy parameter store for secrets for your containers
* view statuses of running ecs services
* easily exec through your VPC bastion host into your running containers, or ssh into a ECS container machine in your cluster
* setup SSH tunnels to the private AWS resources in VPC that your service uses so that you can connect to them from your work machine.

`ecsctl` is able to work with running cluster and export all configuration from ECS configuration.
It work similar like `kubectl` so the curve for learning is very easy.

See the example/ folder in this repository to show yaml files.
