# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""Initialize the rsd virt driver."""

from rsd_virt_for_nova.conf import rsd as cfg

from oslo_log import log as logging

import rsd_lib

CONF = cfg.CONF

LOG = logging.getLogger(__name__)


class PODM_connection(object):
    """A class to make the connection to the PODM."""

    def __init__(self):
        """Initialize class and connection."""
        self.PODM = None
        self._RSD_NODES = list()
        self.composed_nodes = {}
        self.PODM_UUID = None

    def podm_connection(self):
        """Establish/Refresh the connection to the PODM."""
        PODM_IP = CONF.rsd.podm_ip
        PODM_PORT = str(CONF.rsd.podm_port)
        PODM_URI = str('https://' + PODM_IP + ':' + PODM_PORT + '/redfish/v1')
        self.PODM = rsd_lib.RSDLib(PODM_URI, username=CONF.rsd.podm_user,
                                   password=CONF.rsd.podm_password,
                                   verify=False).factory()

        podm_info = self.PODM.json
        if "UUID" in podm_info.keys():
            self.PODM_UUID = podm_info["UUID"]

        # Gets the RSD compute systems to create compute agents from
        SYS_COL = self.PODM.get_system_collection()
        SYSTEMS = SYS_COL.members_identities

        COMPOSED_NODE_COL = self.PODM.get_node_collection()

        for s in SYSTEMS:
            # Allocate the resources for all of the systems availablea
            try:
                node = COMPOSED_NODE_COL.compose_node()
            except Exception as ex:
                LOG.warn("Node is already allocated: %s", ex)

        # Set up the rsd hypervisor nodes.
        COMPOSED_NODE_COL = self.PODM.get_node_collection()
        COMPOSED_NODES = COMPOSED_NODE_COL.members_identities
        for cn in COMPOSED_NODES:
            # Assemble all the composed nodes
            try:
                node_inst = self.PODM.get_node(cn)
                node_inst.assemble_node()
            except Exception as a_ex:
                LOG.warn("Failed to assemble node: %s", a_ex)

            try:
                node = COMPOSED_NODE_COL.get_member(cn)
                if node.system.identity not in self._RSD_NODES:
                    self._RSD_NODES.append(node.system.identity)
                    self.composed_nodes[node.system.identity] = cn

            except Exception as ce:
                LOG.warn("Failed to establish a connection to the PODM.%s", ce)
                if cn in self.composed_nodes.keys():
                    key = self.composed_nodes[cn]
                    del self.composed_nodes[cn]
                    self._RSD_NODES.remove(key)
