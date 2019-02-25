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

==========
User guide
==========

Introduction
------------

This project is a wip. It is a new nova-virt driver that allows the management
an IntelRSD deployment software architecture. This architecture deployment
facilitates the orchestration of a composable infrastructure through OpenStack.
The new driver itself enables the management of RSD composable nodes through
the use of nova compute service. Therefore you can manage the deployement of a
composed node like you would a VM, container or a baremetal instance, etc.

To set up your OpenStack deployment to use the new virt driver follow the
instructions provided in `installation_guide.rst`.


Usage Instructions
------------------

The new nova-rsd virt driver aims to use the same CLI commands as any of the
other standard virt drivers.

Currently the following commands are supported by the new nova-rsd virt driver:

  ::

      openstack server create --image <IMAGE_ID> --flavor <FLAVOR_ID> <INSTANCE_NAME>

      openstack server delete <INSTANCE_NAME>

      openstack server start <INSTANCE_NAME>

      openstack server stop <INSTANCE_NAME>

      openstack server reboot --hard <INSTANCE_NAME>

      openstack server reboot --soft <INSTANCE_NAME>

      openstack server reboot <INSTANCE_NAME>


To create an instance of type composed node through OpenStack you have to use
one of the specific RSD flavors that are automatically generated based on the
resources available in the RSD deployment. These flavors can be identified by
their name and the extra_specs used to define them when created. The
extra_specs define the custom resources used by the resource provider to track
resource consumption through the placement API.

  .. Example::

        +----------------------------+----------------------------+
        | Field                      | Value                      |
        +----------------------------+----------------------------+
        | OS-FLV-DISABLED:disabled   | False                      |
        | OS-FLV-EXT-DATA:ephemeral  | 0                          |
        | access_project_ids         | None                       |
        | disk                       | 0                          |
        | id                         | 785919MB-32vcpus           |
        | name                       | RSD-785919MB-32vcpus       |
        | os-flavor-access:is_public | True                       |
        | properties                 | resources:CUSTOM_1_S_3='1' |
        | ram                        | 785919                     |
        | rxtx_factor                | 1.0                        |
        | swap                       |                            |
        | vcpus                      | 32                         |
        +----------------------------+----------------------------+


In general a flavor can only be used once depending on the amount of composable
systems available in the RSD deployment. They will define the specific system that
will be consumed from the RSD deployment.


Usage Tracking
--------------

The consumption of resource can be tracked through nova hypervisors used to boot
the composed node instances from. These are defined at the ``Chassis`` level of
the RSD deployment.
It can also be tracked in the placement API in terms of resource providers and
their inventory. There is a resource provider for each of the hypervisors at
the ``Chassis`` level and the a child resource provider for each ``System``
contained within the defined ``Chassis``.
