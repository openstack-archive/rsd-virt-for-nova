..
      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

==================
Installation Guide
==================

Pre-requisites
--------------

* Access to the internet
* An IntelRSD deployment, managed by a PODM
* Min. one PSME communicating with yout PODM, with available compute systems


Installation of OpenStack
-------------------------

The following guide provides developer instructions on how to deploy OpenStack
using the deployment tool DevStack:

    https://docs.openstack.org/devstack/latest/guides/single-machine.html

Once you have set up your environment to deploy DevStack please refer to the
below configuration instructions to enable the nova-rsd driver contained in
this repo.

DevStack Configuration
~~~~~~~~~~~~~~~~~~~~~~

These configuration instructions provide directions for this minimal
installation of the nova-rsd driver with OpenStack. It also assumes that you
already have setup and configured an RSD PODM that is communicating with
available composable compute systems, via one or more PSMEs.

  .. Note::

      For instructions on setting up a PODM and PSMEs please refer to the user guides
      and code repositories referred to in the following links:

        https://github.com/intel/intelRSD

        https://www.intel.com/content/www/us/en/architecture-and-technology/rack-scale-design/rack-scale-design-resources.html


A sample local.conf for DevStack is provided here, `examples/sample_local.conf`.
Please copy this file into your devstack reposititory and rename it local.conf
and adjust the configuration options provided where appropriate.

  ::

    cp examples/sample_local.conf devstack/local.conf

local.conf settings
~~~~~~~~~~~~~~~~~~~

In the local.conf the following parameters can be changed:

* HOST_IP:
    Set this option to be the ip address of where your OpenStack deployment
    will be running.

* ``enable_plugin nova-rsd <PATH_TO_NOVA_RSD_REPO> <REPO_BRANCH_NAME>``:
    Clone the nova-rsd repository and point PATH_TO_NOVA_RSD_REPO to its
    location.

    Set the REPO_BRANCH_NAME to be the branch of the above repo to be the one
    with the code version that you require. If left unspecified will default to
    master.

* PODM_IP:
    This parameter specifies the IP address of where your PODM is running to
    facilitate communication with its APIs.

    Default: ``localhost``

* PODM_USER:
    This parameter specifies the username to authenticate to the PODM with.

    Default: ``admin``

* PODM_PASSWD:
    This parameter specifies the password to authenticate to the PODM with,
    inconjuction with the username defined above.

    Default: ``admin``

* PODM_PORT:
    This parameter specifies the port that the PODM is certified to transport
    trsffic through.

    Default: ``8443``
