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
"""
An RSD hypervisor+api.

Inherits from Nova's FakeDriver to facilicate allocating/composing RSD
nodes. Enables communication to the PODM to enable this.

"""

import copy

import json

from collections import OrderedDict

from nova import context

from nova import exception

from nova import objects

from nova import rc_fields as fields

from nova.compute import power_state
from nova.objects import fields as obj_fields
from nova.objects import flavor
from nova.virt import driver
from nova.virt import hardware

from rsd_virt_for_nova.conf import rsd as cfg
from rsd_virt_for_nova.virt import rsd

from oslo_log import log as logging

from oslo_utils import versionutils

CONF = cfg.CONF

LOG = logging.getLogger(__name__)

PODM_NODE = ()


def set_nodes(nodes):
    """Set RSDDriver's node.list.

    It has effect on the following methods:
        get_available_nodes()
        get_available_resource
    To restore the change, call restore_nodes()
    """
    global PODM_NODE
    PODM_NODE = nodes


class RSDDriver(driver.ComputeDriver):
    """Implementation of nova compute driver to compose RSD nodes from nova."""

    def __init__(self, virtapi, read_only=False):
        """Initialize the RSDDriver."""
        super(RSDDriver, self).__init__(virtapi)
        # Initializes vairables to track compute nodes and instances
        self.driver = rsd.PODM_connection()
        self.instances = OrderedDict()
        self.rsd_flavors = OrderedDict()
        self._nodes = self._init_nodes()
        self._composed_nodes = OrderedDict()
        self.instance_node = None

    def _init_nodes(self):
        """Create a compute node for every compute sled."""
        self.driver.podm_connection()
        nodes = []
        CHASSIS_COL = self.driver.PODM.get_chassis_collection()
        for c in CHASSIS_COL.members_identities:
            chas = CHASSIS_COL.get_member(c)
            cha_sys = self.check_chassis_systems(chas)
            if cha_sys != []:
                nodes.append(c)
        set_nodes(nodes)
        return copy.copy(PODM_NODE)

    def init_host(self, host):
        """Initialize anything that is necessary for the driver to function."""
        return host

    def get_info(self, instance):
        """Get instance info including power state."""
        if instance.uuid not in self.instances:
            raise exception.InstanceNotFound(instance_id=instance.uuid)
        i = self.instances[instance.uuid]
        return hardware.InstanceInfo(state=i.power_state)

    def get_available_nodes(self, refresh=True):
        """Return nodenames of all nodes managed by the compute service."""
        self._nodes = self._init_nodes()
        return self._nodes

    def node_is_available(self, nodename):
        """Return whether this compute service manages a particular node."""
        if nodename in self.get_available_nodes():
            self.instance_node = nodename
            return True
        # Refresh and check again.
        return nodename in self.get_available_nodes(refresh=True)

    def list_instances(self):
        """List all available instances."""
        return self.instances

    def spawn(self, context, instance, image_meta, injected_files,
              admin_password, allocations, network_info=None,
              block_device_info=None):
        """Spawn an RSD composed node on a boot request."""
        uuid = instance.uuid
        # Assembles the composed node and tracks node from the instance
        COMPOSED_NODE_COL = self.driver.PODM.get_node_collection()
        node_inst = None
        flav_id = instance.flavor.flavorid
        sys_list = self.rsd_flavors[flav_id]['rsd_systems']
        for n in COMPOSED_NODE_COL.members_identities:
            try:
                node_inst = self.driver.PODM.get_node(n)
            except Exception as ex:
                LOG.warn("Malformed composed node instance:%s", ex)

            if node_inst is not None:
                node_state = node_inst.composed_node_state
                p_state = node_inst.power_state
                if node_state == 'assembled' and p_state == 'off':
                    # Provide nova instance with composed node info
                    node_sys_id = node_inst.system.identity
                    if node_sys_id in sys_list:
                        self.instances[uuid] = instance
                        self._composed_nodes[uuid] = node_inst
                        instance.display_description = \
                            json.dumps({"node_identity": n,
                                        "node_uuid": node_inst.uuid})
                        self.power_on(context, instance, network_info)
                        return
        raise Exception("Failed to assign composed node for instance.")

    def destroy(self, context, instance, network_info, block_device_info=None,
                destroy_disks=True):
        """Destroy RSD composed node on nova delete request."""
        key = instance.uuid
        if key in self._composed_nodes:
            node_inst = self._composed_nodes[key]
            LOG.info("Disassembling RSD composed node.")
            node_inst.delete_node()

            if key in self.instances:
                # Looks up the correct node to deallocate resources froma
                del self.instances[key]
            else:
                LOG.warning("Key not in instances.")

            LOG.info("Reallocating resources for composed node.")
            COMPOSED_NODE_COL = self.driver.PODM.get_node_collection()
            try:
                node_inst = COMPOSED_NODE_COL.compose_node()
                rep_node = self.driver.PODM.get_node(node_inst)
                rep_node.assemble_node()
            except Exception as ex:
                LOG.warn("Node is already allocated: %s", ex)
        else:
            if key in self.instances:
                # Looks up the correct node to deallocate resources from
                del self.instances[key]
            else:
                LOG.warning("Key '%(key)s' not in instances '%(inst)s'",
                            {'key': key,
                             'inst': self.instances}, instance=instance)

    def get_available_resource(self, nodename):
        """Update compute manager resource info on ComputeNode table."""
        cpu_info = ''
        if nodename not in self._nodes:
            return {}

        SYSTEM_COL = self.driver.PODM.get_system_collection()
        members = SYSTEM_COL.members_identities

        CHASSIS_COL = self.driver.PODM.get_chassis_collection()
        chas = CHASSIS_COL.get_member(nodename)
        cha_sys = self.check_chassis_systems(chas)

        # Check if all flavors are valid
        self.check_flavors(SYSTEM_COL, members)
        self._create_flavors()
        res = {
            'vcpus': self.get_sys_proc_info(cha_sys),
            'memory_mb': self.get_sys_memory_info(cha_sys),
            'local_gb': 0,
            'vcpus_used': 0,
            'memory_mb_used': 0,
            'local_gb_used': 0,
            'hypervisor_type': 'composable',
            'hypervisor_version': versionutils.convert_version_to_int('1.0'),
            'hypervisor_hostname': nodename,
            'cpu_info': cpu_info,
            'disk_available_least': 0,
            'supported_instances': [(
                obj_fields.Architecture.X86_64,
                obj_fields.HVType.BAREMETAL,
                obj_fields.VMMode.HVM)],
            'numa_topology': None,
        }
        return res

    def update_provider_tree(self, provider_tree, nodename, allocations=None):
        """Update ProviderTree with current resources + inventory information.

        When this method returns, provider_tree should represent the correct
        hierarchy of nested resource providers associated with this compute
        node, as well as the inventory, aggregates, and traits associated with
        those resource providers.
        This method supersedes get_inventory(): if this method is implemented,
        get_inventory() is not used.
        :note: Renaming a provider (by deleting it from provider_tree and
        re-adding it with a different name) is not supported at this time.
        See the developer reference documentation for more details:
        https://docs.openstack.org/nova/latest/reference/update-provider-tree.html
        """
        SYSTEM_COL = self.driver.PODM.get_system_collection()
        sys_s = SYSTEM_COL.members_identities
        systems = []
        for s in sys_s:
            systems.append(s)

        CHASSIS_COL = self.driver.PODM.get_chassis_collection()

        for c in CHASSIS_COL.members_identities:
            chas = CHASSIS_COL.get_member(nodename)
            cha_sys = self.check_chassis_systems(chas)
            if cha_sys != []:
                for s in cha_sys:
                    sys_inv = self.create_child_inventory(s)
                    try:
                        provider_tree.new_child(s, nodename)
                    except Exception as ex:
                        LOG.warn("Failed to create new RP: %s", ex)
                    provider_tree.update_inventory(s, sys_inv)
            chas_inv = self.create_inventory(cha_sys)
            provider_tree.update_inventory(nodename, chas_inv)

    def get_sys_proc_info(self, systems):
        """Track vcpus made available by the PODM."""
        cpus = 1
        SYSTEM_COL = self.driver.PODM.get_system_collection()
        try:
            cpus = 0
            for s in systems:
                ss = SYSTEM_COL.get_member(s)
                if ss.identity in self.driver.composed_nodes.keys():
                    cpus = cpus + ss.processors.summary.count
        except Exception as ex:
            LOG.info("Failed to get processor info: %s", ex)
        return cpus

    def get_sys_memory_info(self, systems):
        """Track memory available in the PODM."""
        ram = 1
        SYSTEM_COL = self.driver.PODM.get_system_collection()
        try:
            ram = 0
            for s in systems:
                ss = SYSTEM_COL.get_member(s)
                if ss.identity in self.driver.composed_nodes.keys():
                    mem = ss.memory_summary.size_gib
                    ram = \
                        ram + self.conv_GiB_to_MiB(mem)
        except Exception as ex:
            LOG.info("Failed to get memory info: %s", ex)
        return ram

    def conv_GiB_to_MiB(self, input_GiB):
        """Convert gib to mib."""
        return int(input_GiB / 0.000976562500000003)

    def power_off(self, instance, timeout=0, retry_interval=0):
        """Power off the specified instance.

        :param instance: nova.objects.instance.Instance
        :param timeout: time to wait for GuestOS to shutdown
        :param retry_interval: How often to signal guest while
                                  waiting for it to shutdown
        """
        key = instance.uuid
        timeout = timeout or None
        if key in self.instances and key in self._composed_nodes:
            LOG.info("Powering off composed node: %s", key)
            self.instances[instance.uuid].power_state = power_state.SHUTDOWN
            node_inst = self._composed_nodes[key]
            node_inst.reset_node('graceful shutdown')

    def power_on(self, context, instance, network_info,
                 block_device_info=None):
        """Power on the specified instance.

        :param instance: nova.objects.instance.Instance
        """
        key = instance.uuid
        if key in self.instances and key in self._composed_nodes:
            LOG.info("Powering on composed node: %s", key)
            self.instances[instance.uuid].power_state = power_state.RUNNING
            node_inst = self._composed_nodes[key]
            node_inst.reset_node('force on')

    def reboot(self, context, instance, network_info, reboot_type,
               block_device_info=None, bad_volumes_callback=None):
        """Reboot the specified instance.

        After this is called successfully, the instance's state
        goes back to power_state.RUNNING. The virtualization
        platform should ensure that the reboot action has completed
        successfully even in cases in which the underlying domain/vm
        is paused or halted/stopped.
        :param instance: nova.objects.instance.Instance
        :param network_info: instance network information
        :param reboot_type: Either a HARD or SOFT reboot
        :param block_device_info: Info pertaining to attached volumes
        :param bad_volumes_callback: Function to handle any bad volumes
            encountered
        """
        key = instance.uuid
        if key in self.instances and key in self._composed_nodes:
            node_inst = self._composed_nodes[key]
            if reboot_type == 'HARD':
                LOG.info(
                    "Force restart composed node for a hard reboot: %s", key)
                node_inst.reset_node('force restart')
            else:
                LOG.info("Graceful restart composed node for reboot: %s", key)
                node_inst.reset_node('graceful restart')

    def create_inventory(self, system):
        """Function to create provider tree inventory."""
        mem_max = 1
        proc_max = 1
        if self.get_sys_memory_info(system) >= mem_max:
            mem_max = self.get_sys_memory_info(system)
        if self.get_sys_proc_info(system) >= proc_max:
            proc_max = self.get_sys_proc_info(system)

        return {
                    'VCPU': {
                       'total': proc_max,
                       'max_unit': proc_max,
                       'min_unit': 1,
                       'step_size': 1,
                       'allocation_ratio': 1,
                       'reserved': 0
                    },
                    'MEMORY_MB': {
                        'total': mem_max,
                        'max_unit': mem_max,
                        'min_unit': 1,
                        'step_size': 1,
                        'allocation_ratio': 1,
                        'reserved': 0
                    }
                }

    def create_child_inventory(self, system):
        """Create custom resources for all of the child RP's."""
        SYSTEM_COL = self.driver.PODM.get_system_collection()
        sys = SYSTEM_COL.get_member(system)
        mem = self.conv_GiB_to_MiB(sys.memory_summary.size_gib) - 512
        proc = sys.processors.summary.count
        flav_id = str(mem) + 'MB-' + str(proc) + 'vcpus'
        res = fields.ResourceClass.normalize_name(flav_id)
        return {
             res: {
                'total': 1,
                'reserved': 0,
                'min_unit': 1,
                'max_unit': 1,
                'step_size': 1,
                'allocation_ratio': 1,
             }
        }

    def check_chassis_systems(self, chassis):
        """Check the chassis for linked systems."""
        systems = chassis.json['Links']['ComputerSystems']
        cha_sys = []
        for s in systems:
            cha_sys += s.values()
        return cha_sys

    def _create_flavors(self):
        """Auto-generate the flavors for the compute systems available."""
        SYSTEM_COL = self.driver.PODM.get_system_collection()
        for s in SYSTEM_COL.members_identities:
            sys = SYSTEM_COL.get_member(s)
            mem = self.conv_GiB_to_MiB(sys.memory_summary.size_gib) - 512
            proc = sys.processors.summary.count
            flav_id = str(mem) + 'MB-' + str(proc) + 'vcpus'
            res = fields.ResourceClass.normalize_name(flav_id)
            spec = 'resources:' + res
            values = {
                'name': 'RSD-' + flav_id,
                'flavorid': flav_id,
                'memory_mb': mem,
                'vcpus': proc,
                'root_gb': 0,
                'extra_specs': {
                    spec: '1'}
            }
            if sys.identity not in self.rsd_flavors:
                try:
                    LOG.debug("New flavor for system: %s", sys.identity)
                    rsd_flav = flavor._flavor_create(
                       context.get_admin_context(), values)
                    self.rsd_flavors[flav_id] = {
                            'id': rsd_flav['id'],
                            'rsd_systems': [sys.identity]
                            }
                except Exception as ex:
                    LOG.debug(
                        "A flavor already exists for this rsd system: %s", ex)
                    ex_flav = flavor.Flavor._flavor_get_by_flavor_id_from_db(
                        context.get_admin_context(), flav_id)
                    if flav_id not in self.rsd_flavors.keys():
                        self.rsd_flavors[flav_id] = {
                                'id': ex_flav['id'],
                                'rsd_systems': [sys.identity]
                                }
                    else:
                        sys_list = self.rsd_flavors[flav_id]['rsd_systems']
                        sys_list.append(sys.identity)
                        self.rsd_flavors[flav_id]['rsd_systems'] = sys_list

    def check_flavors(self, collection, systems):
        """Check if flavors should be deleted based on system removal."""
        sys_ids = []
        flav_ids = []
        LOG.debug("Checking existing flavors.")
        for s in systems:
            sys = collection.get_member(s)
            sys_ids.append(sys.identity)
            mem = self.conv_GiB_to_MiB(sys.memory_summary.size_gib) - 512
            proc = sys.processors.summary.count
            flav_id = str(mem) + 'MB-' + str(proc) + 'vcpus'
            flav_ids.append(flav_id)

        f_list = objects.FlavorList.get_all(context.get_admin_context())
        for f in f_list:
            if 'RSD' in f.name:
                if f.flavorid not in flav_ids:
                    try:
                        flavor._flavor_destroy(
                                context.get_admin_context(),
                                flavor_id=f.flavorid)
                    except exception.FlavorNotFound as ex:
                        LOG.warn("Flavor not found exception: %s", ex)

        for k in list(self.rsd_flavors):
            sys_list = self.rsd_flavors[k]['rsd_systems']
            for s in sys_list:
                if s not in sys_ids:
                    rsd_id = self.rsd_flavors[k]['id']
                    flavor._flavor_destroy(context.get_admin_context(), rsd_id)
                    LOG.debug("Deleting flavor for removed systems: %s", k)
                    del self.rsd_flavors[k]
        return
