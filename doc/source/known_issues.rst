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

============
Known Issues
============

Introduction
------------

This project is being created as a new out-of-tree virt driver for nova. It is
currently a work-in-progress and there are a few issues and area that need to
be looked into and developed to bring the project to maturity.


Issues + Future work
--------------------

* Implementation of additional unit tests and inclusion of functional tests for
  the complete code coverage of the new virt driver.

* Needs to be tested on physical RSD compatible hardware.

* Implement the usage of the EventSubscription service provided by the PODM to
  improve the tracking of the removal/addition of physical resources from the
  RSD deployment.

* Check the status of the creation of duplicate flavors when they are auto
  generated. May have to be re-implemented now that the extra_specs are being
  used by the resource provider to track the inventory of the systems.
