.. _monitoring_dashboard:

Monitoring Dashboard
====================

SampleDB can be used with the `Flask-MonitoringDashboard <https://flask-monitoringdashboard.readthedocs.io/en/latest/index.html>`_ package to monitor performance. To do so, you need to set the ``SAMPLEDB_ENABLE_MONITORINGDASHBOARD`` :ref:`environment variable <monitoring_dashboard_configuration>`. You should then also make sure the file indicated by the ``SAMPLEDB_MONITORINGDASHBOARD_DATABASE`` variable persists between restarts of SampleDB, e.g. by bind mounting it, and might want to include it in your backups.

As the monitoring, logging and optionally profiling done for the monitoring dashboard will impact performance, it is not recommended to use this for a production installation of SampleDB. However it can be a useful tool during testing and development.

.. note:: Support for this is experimental in version 0.21 and it may be removed in the future.