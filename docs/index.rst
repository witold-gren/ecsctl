=============================================
ecsctl - command line tool for manage AWS ECS
=============================================

kubectl-style command line tool for AWS EC2 Container Service (ECS). This tool is alpha version and contains
bugs and not catched exceptions. Also to usage all feature in you cluster must exist specific configuration: eg.
`IAM Roles`, `AWSS cloudwatch-agent`, `ecs agent configuration` and much more.

I will prepare more examples and documentation when ecsctl will stable.

Big thanks for Xiuming Chen for first iteration of this project https://github.com/cxmcc/ecsctl I added much more new
features (it will problematic to cerate lot of pull requests) to this project so I decide create another repository.

.. include:: pages/introduction.rst

.. toctree::
   :maxdepth: 1
   :caption: Contents:

   pages/introduction
   pages/installation
   pages/tutorials/index
   pages/example

..
   Indices and tables
   ==================

   * :ref:`genindex`
   * :ref:`modindex`
   * :ref:`search`
