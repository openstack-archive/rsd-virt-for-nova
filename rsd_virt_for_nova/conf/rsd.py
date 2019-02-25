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
"""Additional configuration opentions for the rsd-virt driver."""

from oslo_config import cfg

CONF = cfg.CONF

rsd_group = cfg.OptGroup(
    'rsd',
    title='RSD Options')


rsd_opts = [
    cfg.StrOpt('podm_ip',
               default='localhost',
               help='Specifying the IP address of the PODM which is talking '
                    'to the appropriate PSME. Defaults to localhost, '
                    'assuming PODM is running on the same machine as '
                    'OpenStack. '),
    cfg.StrOpt('podm_user',
               default='admin',
               help='Specifying the username for communication with the '
                    'PODM. '),
    cfg.StrOpt('podm_password',
               default='admin',
               help='Specifying the password for communication with the '
                    'PODM. '),
    cfg.IntOpt('podm_port',
               default=8443,
               help='Specifying port on PODM for communication. ')
]

STATIC_OPTIONS = (rsd_opts)


def register_opts(conf):
    """Register the new configuration options for RSD."""
    conf.register_group(rsd_group)
    conf.register_opts(STATIC_OPTIONS, group=rsd_group)
