# -*- coding: utf-8 -*-

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""Unit tests for the RSD virt driver."""

import json

import mock

from nova import context

from nova import exception

from nova import objects

from nova import rc_fields as fields

from nova.compute import power_state
from nova.compute import provider_tree

from nova.virt import fake
from nova.virt import hardware

from rsd_virt_for_nova.virt import rsd
from rsd_virt_for_nova.virt.rsd import driver

from oslo_utils import versionutils

from oslo_utils.fixture import uuidsentinel as uuids

from oslotest import base

import rsd_lib

from rsd_lib.resources.v2_1.chassis import chassis
from rsd_lib.resources.v2_2.system import system

from rsd_lib.resources.v2_3.node import node
from rsd_lib.resources.v2_3.node import node as v2_3_node

from sushy import connector


class FakeInstance(object):
    """A class to fake out nova instances."""

    def __init__(self, name, state, uuid, new_flavor, node):
        """Initialize the variables for fake instances."""
        self.name = name
        self.power_state = state
        self.uuid = uuid
        self.display_description = None
        self.flavor = new_flavor
        self.node = node

    def __getitem__(self, key):
        """Method to retrieve fake instance variables."""
        return getattr(self, key)

    def delete_node(self):
        """Fake delete node function."""
        pass

    def reset_node(self, action):
        """Fake reset node function."""
        pass


class FakeFlavor(object):
    """A class to fake out a flavor for a nova instance."""

    def __init__(self, vcpus, memory_mb, name, flavorid, extra_specs):
        """Initialize the variables for a fake flavor."""
        self.vcpus = vcpus
        self.memory_mb = memory_mb
        self.name = name
        self.flavorid = flavorid
        self.extra_specs = extra_specs

    def __getitem__(self, key):
        """Method to retrieve fake flavor variables."""
        return getattr(self, key)


class TestRSDDriver(base.BaseTestCase):
    """A test class for the driver."""

    @mock.patch.object(rsd, 'PODM_connection', autospaec=True)
    @mock.patch.object(connector, 'Connector', autospec=True)
    def setUp(self, mock_connector, pod_conn):
        """Initial setup of mocks for all of the unit tests."""
        super(TestRSDDriver, self).setUp()
        # Mock out the connection to the RSD redfish API
        self.root_conn = mock.MagicMock()
        mock_connector.return_value = self.root_conn

        # Create sample collections and instances of Chassis/System/Nodes
        with open('rsd_virt_for_nova/tests/json_samples/root.json',
                  'r') as f:
            self.root_conn.get.return_value.json.return_value = json.loads(
                                                                     f.read())
        self.rsd = rsd_lib.main.RSDLib('http://foo.bar:8442', username='foo',
                                       password='bar', verify=False).factory()

        with open('rsd_virt_for_nova/tests/json_samples/chassis_col.json',
                  'r') as f:
            self.root_conn.get.return_value.json.return_value = json.loads(
                                                                     f.read())
        self.chassis_col = chassis.ChassisCollection(
            self.root_conn, '/redfish/v1/Chassis',
            redfish_version='1.0.2')

        with open('rsd_virt_for_nova/tests/json_samples/chassis.json',
                  'r') as f:
            self.root_conn.get.return_value.json.return_value = json.loads(
                                                                     f.read())

        self.chassis_inst = chassis.Chassis(
            self.root_conn, '/redfish/v1/Chassis/Chassis1',
            redfish_version='1.0.2')

        with open('rsd_virt_for_nova/tests/json_samples/node_col.json',
                  'r') as f:
            self.root_conn.get.return_value.json.return_value = json.loads(
                                                                     f.read())
        self.node_collection = node.NodeCollection(
            self.root_conn, '/redfish/v1/Nodes', redfish_version='1.0.2')

        with open('rsd_virt_for_nova/tests/json_samples/node.json',
                  'r') as f:
            self.root_conn.get.return_value.json.return_value = json.loads(
                                                                     f.read())
        self.node_inst = node.Node(
            self.root_conn, '/redfish/v1/Nodes/Node1',
            redfish_version='1.0.2')

        with open('rsd_virt_for_nova/tests/json_samples/node_assembled.json',
                  'r') as f:
            self.root_conn.get.return_value.json.return_value = json.loads(
                                                                     f.read())
        self.node_ass_inst = node.Node(
            self.root_conn, '/redfish/v1/Nodes/Node1',
            redfish_version='1.0.2')

        with open('rsd_virt_for_nova/tests/json_samples/sys_collection.json',
                  'r') as f:
            self.root_conn.get.return_value.json.return_value = \
                json.loads(f.read())
        self.system_col = system.SystemCollection(
            self.root_conn, '/redfish/v1/Systems',
            redfish_version='1.0.2')

        with open('rsd_virt_for_nova/tests/json_samples/system.json',
                  'r') as f:
            self.root_conn.get.return_value.json.return_value = json.loads(
                                                                     f.read())
        self.system_inst = system.System(
            self.root_conn, '/redfish/v1/Systems/System1',
            redfish_version='1.0.2')

        # Mock out a fake virt driver and its dependencies/parameters
        self.RSD = driver.RSDDriver(fake.FakeVirtAPI())

        # Create Fake flavors and instances
        gb = self.system_inst.memory_summary.total_system_memory_gib
        mem = self.RSD.conv_GiB_to_MiB(gb)
        proc = self.system_inst.json['ProcessorSummary']['Count']
        flav_id = str(mem) + 'MB-' + str(proc) + 'vcpus'
        res = fields.ResourceClass.normalize_name(self.system_inst.identity)
        spec = 'resources:' + res
        # Mock out some instances for testing
        self.flavor = FakeFlavor(
            gb, mem, str('RSD.' + flav_id),
            self.system_inst.identity,
            spec)
        self.inst1 = FakeInstance('inst1', power_state.RUNNING,
                                  'inst1id', self.flavor,
                                  "/redfish/v1/Chassis/Chassis1")
        self.invalid_inst = FakeInstance(
                'inv_inst', power_state.RUNNING, 'inv_inst_id',
                self.flavor, "/redfish/v1/Chassis/Chassis1")
        self.RSD.instances = {self.inst1.uuid: self.inst1}

        # A provider tree for testing on the placement API
        self.ptree = provider_tree.ProviderTree()

        self.test_image_meta = {
            "disk_format": "raw",
        }

    @mock.patch.object(driver, 'set_nodes')
    @mock.patch.object(driver.RSDDriver, 'check_chassis_systems')
    def test_init_nodes_success(self, check_chas_sys, set_nodes):
        """Initialize nodes successful test."""
        # Setup for test to successfully create nodes for each valid chassis
        chas_col = self.RSD.driver.PODM.get_chassis_collection.return_value
        chas_col.members_identities = ['/redfish/v1/Chassis/Chassis1']
        self.RSD._init_nodes()

        # Confirm that the correct functionality is called and the correct
        # compute nodes are created to boot hypervisors from
        self.RSD.driver.podm_connection.assert_called()
        self.RSD.driver.PODM.get_chassis_collection.assert_called()
        chas_col.get_member.assert_called_with('/redfish/v1/Chassis/Chassis1')
        check_chas_sys.assert_called_with(chas_col.get_member.return_value)
        set_nodes.assert_called_with(['/redfish/v1/Chassis/Chassis1'])

    @mock.patch.object(driver, 'set_nodes')
    @mock.patch.object(driver.RSDDriver, 'check_chassis_systems')
    def test_init_nodes_failure(self, check_chas_sys, set_nodes):
        """Initialize nodes failure test."""
        # Setup for test failing to create nodes for each chassis
        chas_col = self.RSD.driver.PODM.get_chassis_collection.return_value
        self.RSD._init_nodes()

        # Verify failed nodes and insufficient function calls
        self.RSD.driver.podm_connection.assert_called()
        self.RSD.driver.PODM.get_chassis_collection.assert_called()
        chas_col.get_member.assert_not_called()
        check_chas_sys.assert_not_called()
        set_nodes.assert_called_with([])

    def test_init_host(self):
        """Test initializing the host."""
        # Run test
        host = self.RSD.init_host(self.chassis_inst)

        # Confirm the correct hostname is identified
        self.assertEqual(host, self.chassis_inst)

    @mock.patch.object(hardware, 'InstanceInfo')
    def test_get_info_valid(self, info):
        """Test getting information for a valid instance."""
        # Run test
        self.RSD.get_info(self.inst1)

        # Confirm that the correct hardware info os collected
        info.assert_called_once_with(state=self.inst1.power_state)

    @mock.patch.object(hardware, 'InstanceInfo')
    def test_get_info_invalid(self, info):
        """Test getting information for an invalid instance."""
        # An invalid instance throws an exception, hardware info not requested
        self.assertRaises(
            exception.InstanceNotFound, self.RSD.get_info, self.invalid_inst)

        info.assert_not_called()

    def test_get_available_nodes_false_refresh(self):
        """Test getting a list of the available nodes, no refresh."""
        # Run test checking the list of available nodes
        nodes = self.RSD.get_available_nodes(refresh=False)

        # Confirm that the correst functions are called and all of the correct
        # nodes are available
        self.assertEqual(nodes, self.RSD._nodes)

    def test_get_available_nodes_true_refresh(self):
        """Test getting a list of the available nodes, with refresh."""
        # Run test checking the list of available nodes, refresh
        nodes = self.RSD.get_available_nodes(refresh=True)

        # Confirm that the correst functions are called and all of the correct
        # nodes are available
        self.assertEqual(nodes, self.RSD._nodes)

    @mock.patch.object(driver.RSDDriver, 'get_available_nodes')
    def test_node_is_available_invalid(self, getNodes):
        """Test if a node is available for an instance, failure."""
        # Run test checking a node is available
        avail = self.RSD.node_is_available(self.chassis_inst.identity)

        # Confirm the correct functions are called and confirm that the
        # node being checked is not available
        getNodes.assert_called()
        self.assertEqual(self.RSD.instance_node, None)
        self.assertEqual(avail, False)

    @mock.patch.object(driver.RSDDriver, 'get_available_nodes')
    def test_node_is_available_valid(self, getNodes):
        """Test if a node is available for an instance, success."""
        # Run test checking a node is available
        # Setup mocks for a successful test
        getNodes.return_value = self.chassis_col.members_identities
        avail = self.RSD.node_is_available('/redfish/v1/Chassis/Chassis1')

        # Confirm successful check that node is available through the correct
        # function calls
        getNodes.assert_called()
        self.assertEqual(self.RSD.instance_node,
                         '/redfish/v1/Chassis/Chassis1')
        self.assertEqual(avail, True)

    def test_list_instances(self):
        """Test listing all instances."""
        # Run test to list available instances
        instances = self.RSD.list_instances()

        # Confirm the result matches the internal list
        self.assertEqual(instances, {self.inst1.uuid: self.inst1})

    @mock.patch.object(driver.RSDDriver, 'power_on')
    def test_spawn_success(self, power_on):
        """Test spawning an instance successfully."""
        # Mock out setup to successfully create a node
        node_col = self.RSD.driver.PODM.get_node_collection.return_value
        node_col.members_identities = ['/redfish/v1/Nodes/Node1']
        self.RSD.driver.PODM.get_node.return_value = self.node_ass_inst
        mock_context = context.get_admin_context()
        self.RSD.rsd_flavors = {
                self.flavor.flavorid: {
                    'id': 'flav_id',
                    'rsd_systems': {
                        '/redfish/v1/Chassis/Chassis1':
                                self.system_inst.identity
                        }
                    }
                }
        image_meta = objects.ImageMeta.from_dict(self.test_image_meta)
        # Run spawning test
        self.RSD.spawn(mock_context, self.inst1, image_meta,
                       [], None, {})

        # Confirm that a node instances is spawned and the physical composed
        # node is powered on
        self.RSD.driver.PODM.get_node_collection.assert_called_once()
        self.RSD.driver.PODM.get_node.assert_called_with(
                '/redfish/v1/Nodes/Node1')
        power_on.assert_called_once_with(mock_context, self.inst1, None)

    @mock.patch.object(v2_3_node, 'Node', autospec=True)
    def test_destroy_success(self, mock_node):
        """Test destroying an instance and deleting the composed node."""
        # Mock out instances and composed nodes for testing purposes
        node_collection = self.RSD.driver.PODM.get_node_collection
        node_inst = node_collection.return_value.compose_node.return_value
        rep_node = self.RSD.driver.PODM.get_node.return_value
        self.RSD._composed_nodes = {self.inst1.uuid: mock_node}

        # Try to destroy the instance
        self.RSD.destroy("context", self.inst1, network_info=None)

        # Confirm that the instance has been delete from the list of instances
        mock_node.delete_node.assert_called_once()
        node_collection.assert_called_once()
        node_collection.return_value.compose_node.assert_called_once()
        self.RSD.driver.PODM.get_node.assert_called_once_with(node_inst)
        rep_node.assemble_node.assert_called_once()
        self.assertNotIn(self.inst1.uuid, self.RSD.instances)

    @mock.patch.object(v2_3_node, 'Node', autospec=True)
    def test_destory_failure(self, mock_node):
        """Test failure to destroy a composed node instance."""
        # Mock out instances and composed nodes for testing purposes
        self.RSD._composed_nodes = {}
        node_collection = self.RSD.driver.PODM.get_node_collection
        node_inst = node_collection.return_value.compose_node.return_value
        # Try to destroy the instance
        self.RSD.destroy("context", self.inst1, network_info=None)

        # Confirm that the instance failed to delete and a new node was not
        # created to replace it
        mock_node.delete_node.assert_not_called()
        self.RSD.driver.PODM.get_node_collection.assert_not_called()
        node_collection.return_value.compose_node.assert_not_called()
        node_inst.assemble_node.assert_not_called()
        self.assertNotIn(self.inst1.uuid, self.RSD.instances)

    @mock.patch.object(driver.RSDDriver, '_create_flavors')
    @mock.patch.object(driver.RSDDriver, 'check_flavors')
    @mock.patch.object(driver.RSDDriver, 'check_chassis_systems')
    @mock.patch.object(versionutils, 'convert_version_to_int')
    @mock.patch.object(driver.RSDDriver, 'get_sys_proc_info')
    @mock.patch.object(driver.RSDDriver, 'get_sys_memory_info')
    def test_get_available_resource_success(self, mem_info, proc_info, conv_v,
                                            check_chas, check_flav,
                                            create_flav):
        """Test successfully getting available resources for a node."""
        # Set up the parameters for the test
        chas_str = '/redfish/v1/Chassis/Chassis1'
        self.RSD._nodes = [chas_str]
        sys_col = self.RSD.driver.PODM.get_system_collection.return_value
        chas_col = self.RSD.driver.PODM.get_chassis_collection.return_value
        resources = self.RSD.get_available_resource(chas_str)

        # Perform checks on all methods called on a successful run
        self.RSD.driver.PODM.get_chassis_collection.assert_called()
        self.RSD.driver.PODM.get_system_collection.assert_called_once()
        chas_col.get_member.assert_called_with(chas_str)
        check_chas.assert_called_with(chas_col.get_member.return_value)
        check_flav.assert_called_with(sys_col, sys_col.members_identities)
        create_flav.assert_called_once()
        mem_info.assert_called_with(check_chas.return_value)
        proc_info.assert_called_with(check_chas.return_value)
        conv_v.assert_called_with('1.0')
        self.assertEqual({'cpu_info': '',
                          'disk_available_least': 0,
                          'hypervisor_hostname': chas_str,
                          'hypervisor_type': 'composable',
                          'hypervisor_version': conv_v.return_value,
                          'local_gb': 0,
                          'local_gb_used': 0,
                          'memory_mb': mem_info.return_value,
                          'memory_mb_used': 0,
                          'numa_topology': None,
                          'supported_instances':
                          [('x86_64', 'baremetal', 'hvm')],
                          'vcpus': proc_info.return_value,
                          'vcpus_used': 0}, resources)

    @mock.patch.object(driver.RSDDriver, 'create_child_inventory')
    @mock.patch.object(driver.RSDDriver, 'create_inventory')
    @mock.patch.object(driver.RSDDriver, 'check_chassis_systems')
    def test_update_provider_tree_success(self, check_chas, create_inv,
                                          create_child_inv):
        """Successfully updating the RP tree test."""
        # Setup a valid resource provider tree for the test
        self.ptree = provider_tree.ProviderTree()
        self.ptree.new_root('/redfish/v1/Chassis/Chassis1', uuids.cn)

        # Setup other mocked calls for a successful test
        chas_col = self.RSD.driver.PODM.get_chassis_collection.return_value
        chas_col.members_identities = ['/redfish/v1/Chassis/Chassis1']
        chas_col.get_member.return_value = self.chassis_inst
        check_chas.return_value = ['/redfish/v1/Systems/System1']
        self.RSD.update_provider_tree(self.ptree,
                                      '/redfish/v1/Chassis/Chassis1')

        # Confirm that the provider tree for the placement API has been
        # updated correctly with a child node for each compute system available
        self.RSD.driver.PODM.get_system_collection.assert_called_once()
        self.RSD.driver.PODM.get_chassis_collection.assert_called()
        chas_col.get_member.assert_called_with('/redfish/v1/Chassis/Chassis1')
        check_chas.assert_called_with(self.chassis_inst)
        create_child_inv.assert_called_once_with('/redfish/v1/Systems/System1')
        create_inv.assert_called_once_with(check_chas.return_value)

    @mock.patch.object(driver.RSDDriver, 'create_child_inventory')
    @mock.patch.object(driver.RSDDriver, 'create_inventory')
    @mock.patch.object(driver.RSDDriver, 'check_chassis_systems')
    def test_update_provider_tree_failure(self, check_chas, create_inv,
                                          create_child_inv):
        """Failing to update the RP tree test."""
        # Setup a valid resource provider tree for the test
        self.ptree = provider_tree.ProviderTree()

        # Setup other mocked calls for a successful test
        sys_col = self.RSD.driver.PODM.get_system_collection.return_value
        chas_col = self.RSD.driver.PODM.get_chassis_collection.return_value
        self.RSD.update_provider_tree(self.ptree,
                                      '/redfish/v1/Chassis/Chassis1')

        # Confirn that the provider tree for the placement API was not updated
        # correctly and no new nodes were created
        self.RSD.driver.PODM.get_system_collection.assert_called_once()
        self.RSD.driver.PODM.get_chassis_collection.assert_called()
        chas_col.get_member.assert_not_called()
        check_chas.assert_not_called()
        sys_col.get_member.assert_not_called()
        create_child_inv.assert_not_called()
        create_inv.assert_not_called()

    def test_get_sys_proc_info_failure(self):
        """Test failing to get sys_proc info."""
        # Set up a failing test for getting system processor information
        sys_col = self.RSD.driver.PODM.get_system_collection.return_value
        cpus = self.RSD.get_sys_proc_info(None)

        # Confirm that the relavant functions fail when called
        self.RSD.driver.PODM.get_system_collection.assert_called_once()
        sys_col.get_member.assert_not_called()
        self.assertEqual(cpus, 0)

    def test_get_sys_proc_info_success(self):
        """Test succeeding in getting sys_proc info."""
        # Set up for a successful test for getting system processor information
        sys_col = self.RSD.driver.PODM.get_system_collection.return_value
        cpus = self.RSD.get_sys_proc_info(['/redfish/v1/Systems/System1'])

        # Confirm that the relavant functions fail when called
        # And correct proccessor information is calculated
        self.RSD.driver.PODM.get_system_collection.assert_called_once()
        sys_col.get_member.assert_called_with('/redfish/v1/Systems/System1')
        self.assertEqual(cpus, 0)

    @mock.patch.object(driver.RSDDriver, 'conv_GiB_to_MiB')
    def test_get_sys_memory_info_failure(self, conv_mem):
        """Test failing to get sys_mem info."""
        # Set up a failing test for getting system memory information
        sys_col = self.RSD.driver.PODM.get_system_collection.return_value
        mem_mb = self.RSD.get_sys_memory_info(None)

        # Confirm that the relavant functions fail when called
        self.RSD.driver.PODM.get_system_collection.assert_called_once()
        sys_col.get_member.assert_not_called()
        conv_mem.assert_not_called()
        self.assertEqual(mem_mb, 0)

    @mock.patch.object(driver.RSDDriver, 'conv_GiB_to_MiB')
    def test_get_sys_memory_info_success(self, conv_mem):
        """Test suceeding at getting sys_mem info."""
        # Set up mocks to successfully get memory information for a system
        sys_col = self.RSD.driver.PODM.get_system_collection.return_value
        sys_col.members_identities = ['/redfish/v1/Systems/System1']
        sys_col.get_member.return_value = self.system_inst
        self.RSD.driver.composed_nodes = {
            self.node_inst.system.identity: self.node_inst.identity}
        # Run the test and get the result
        mem_mb = self.RSD.get_sys_memory_info(['/redfish/v1/Systems/System1'])

        # Confirm that the relavant functions fail when called
        self.RSD.driver.PODM.get_system_collection.assert_called_once()
        sys_col.get_member.assert_called_once_with(
                '/redfish/v1/Systems/System1')
        conv_mem.assert_called_with(
                self.system_inst.memory_summary.total_system_memory_gib)
        # Confirm the result is as to be expected
        self.assertEqual(
                mem_mb,
                conv_mem(
                  self.system_inst.memory_summary.total_system_memory_gib).__radd__())

    def test_conv_GiB_to_MiB(self):
        """Test the conversion of GiB to MiB."""
        # Run test on memory conversion function
        MiB = self.RSD.conv_GiB_to_MiB(8)

        # Confirm the correct result is generated
        self.assertEqual(8191, MiB)

    @mock.patch.object(v2_3_node, 'Node', autospec=True)
    def test_invalid_power_off(self, mock_node):
        """Test the failed powering off of and instance."""
        # power off the invalid instance test
        self.RSD.power_off(self.invalid_inst)

        # power state is not as it should be and the action function
        # reset is not called
        self.assertNotEqual(self.inst1.power_state, power_state.SHUTDOWN)
        mock_node.reset_node.assert_not_called()

    @mock.patch.object(v2_3_node, 'Node', autospec=True)
    def test_valid_power_off(self, mock_node):
        """Test the powering off of an instance."""
        # Mock out a node and instance to power off
        self.RSD._composed_nodes = {self.inst1.uuid: mock_node}

        # Run power off test
        self.RSD.power_off(self.inst1)

        # Confirm that the composed node instance is in the shutdown state
        self.assertEqual(self.inst1.power_state, power_state.SHUTDOWN)
        mock_node.reset_node.assert_called_once_with('graceful shutdown')

    @mock.patch.object(v2_3_node, 'Node', autospec=True)
    def test_invalid_power_on(self, mock_node):
        """Test the powering on of an invalid instance."""
        # Run power on test
        self.RSD.power_on(mock.MagicMock(), self.invalid_inst, 'network_info')

        # No reset action is called on the node
        mock_node.reset_node.assert_not_called()

    @mock.patch.object(v2_3_node, 'Node', autospec=True)
    def test_valid_power_on(self, mock_node):
        """Test the powering on of an instance."""
        # Mock out instances and composed nodes for testing purposes
        self.RSD._composed_nodes = {self.inst1.uuid: mock_node}

        # Power on a valid instance
        self.RSD.power_on(mock.MagicMock(), self.inst1, 'network_info')

        # Confirm that the composed node instance is in the running state
        self.assertEqual(self.inst1.power_state, power_state.RUNNING)
        mock_node.reset_node.assert_called_once_with('force on')

    @mock.patch.object(v2_3_node, 'Node', autospec=True)
    def test_invalid_reboot(self, mock_node):
        """Test reboot of an invalid instance."""
        # Perform a hard reboot on an invalid node
        self.RSD.reboot(
            mock.MagicMock(), self.invalid_inst, 'network_info', 'HARD')

        # No reset action is called
        mock_node.reset_node.assert_not_called()

    @mock.patch.object(v2_3_node, 'Node', autospec=True)
    def test_valid_hard_reboot(self, mock_node):
        """Test valid reboot of a composed node instance."""
        # Mock out instances and composed nodes for testing purposes
        self.RSD._composed_nodes = {self.inst1.uuid: mock_node}

        # Perform a hard reboot on a valid node
        self.RSD.reboot(mock.MagicMock(), self.inst1, 'network_info', 'HARD')

        # Confirm the correct reset action is called
        mock_node.reset_node.assert_called_with('force restart')

    @mock.patch.object(v2_3_node, 'Node', autospec=True)
    def test_valid_soft_reboot(self, mock_node):
        """Test valid reboot of a composed node instance."""
        # Mock out instances and composed nodes for testing purposes
        self.RSD._composed_nodes = {self.inst1.uuid: mock_node}

        # Perform a soft reboot on a valid node
        self.RSD.reboot(mock.MagicMock(), self.inst1, 'network_info', 'SOFT')

        # Confirm the correct reset action is called
        mock_node.reset_node.assert_called_with('graceful restart')

    @mock.patch.object(driver.RSDDriver, 'conv_GiB_to_MiB')
    @mock.patch.object(driver.RSDDriver, 'get_sys_memory_info')
    @mock.patch.object(driver.RSDDriver, 'get_sys_proc_info')
    def test_create_inventory_success(self, sys_proc_info, sys_mem_info,
                                      conv_mem):
        """Test creating a inventory for a provider tree."""
        # Setup test to successfully create inventory
        sys_mem_info.return_value = \
                self.system_inst.memory_summary.total_system_memory_gib
        sys_proc_info.return_value = \
                self.system_inst.json['ProcessorSummary']['Count']
        inv = self.RSD.create_inventory([self.system_inst.identity])

        # Check that the correct functions are called and the inventory
        # is generated correctly
        sys_proc_info.assert_called()
        sys_mem_info.assert_called()
        self.assertEqual(inv, {'MEMORY_MB': {
                                  'reserved': 0,
                                  'total': sys_mem_info.return_value,
                                  'max_unit': sys_mem_info.return_value,
                                  'min_unit': 1,
                                  'step_size': 1,
                                  'allocation_ratio': 1
                                  },
                               'VCPU': {
                                  'reserved': 0,
                                  'total': 1,
                                  'max_unit': 1,
                                  'min_unit': 1,
                                  'step_size': 1,
                                  'allocation_ratio': 1}
                               })

    @mock.patch.object(driver.RSDDriver, 'conv_GiB_to_MiB')
    @mock.patch.object(fields.ResourceClass, 'normalize_name')
    def test_create_child_inventory(self, norm_name, conv_mem):
        """Test creating inventory for the child RP's."""
        # Set up a test to create the inventory for child resource providers
        sys_col = self.RSD.driver.PODM.get_system_collection.return_value
        sys_col.get_member.return_value = self.system_inst
        mem = conv_mem.return_value - 512
        proc = self.system_inst.json['ProcessorSummary']['Count']
        flav_id = str(mem) + 'MB-' + str(proc) + 'vcpus'
        child_inv = self.RSD.create_child_inventory(
                '/redfish/v1/Systems/System1')

        # Check that the correct functions are called and the inventory
        # is generated correctly
        self.RSD.driver.PODM.get_system_collection.assert_called_once()
        sys_col.get_member.assert_called_once_with(
                '/redfish/v1/Systems/System1')
        conv_mem.assert_called_once_with(
                self.system_inst.memory_summary.total_system_memory_gib)
        norm_name.assert_called_once_with(flav_id)
        self.assertEqual(child_inv, {norm_name.return_value: {
                                          'total': 1,
                                          'reserved': 0,
                                          'min_unit': 1,
                                          'max_unit': 1,
                                          'step_size': 1,
                                          'allocation_ratio': 1,
                                          }
                                     })

    def test_check_chassis_systems_invalid(self):
        """Test checking the systems available through an invalid chassis."""
        # Error raied for invalid chassis system check
        self.assertRaises(
            AttributeError, self.RSD.check_chassis_systems,
            'invalid_chassis_instance')

    def test_check_chassis_systems_valid(self):
        """Test checking the systems available through a valid chassis."""
        # Run test to check available systems for a Chassis
        systems = self.RSD.check_chassis_systems(self.chassis_inst)

        # Confirm that the generated list equals the systems linked to the
        # Chassis
        self.assertEqual(systems, ['/redfish/v1/Systems/System1',
                                   '/redfish/v1/Systems/System2',
                                   '/redfish/v1/Systems/System3',
                                   '/redfish/v1/Systems/System4'])
