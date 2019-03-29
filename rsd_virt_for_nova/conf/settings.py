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
"""Configuration"""

from __future__ import unicode_literals

from rsd_virt_for_nova.conf.singleton import Singleton
from collections import namedtuple
import logging
import six

LOGGER = logging.getLogger(__name__)


class BadConfigError(Exception):
    """Configuration exception"""
    pass


class CfgParam(namedtuple('CfgParam', ['key', 'default', 'data_type'])):
    """Configuration parameter definition"""

    def value(self, data):
        """Convert a string to the parameter type"""

        try:
            return self.data_type(data)
        except (ValueError, TypeError) as exc:
            LOGGER.info('Config value exception: %s', six.text_type(exc))
            raise BadConfigError(
                'Invalid value "%s" for configuration parameter "%s"' % (
                    data, self.key))


@Singleton
class Config(object):
    """Plugin confguration"""

    _configuration = [
        CfgParam('OS_AUTH_URL', None, six.text_type),
        CfgParam('OS_IDENTITY_API_VERSION', '3', six.text_type),
        CfgParam('OS_USERNAME', None, six.text_type),
        CfgParam('OS_PASSWORD', None, six.text_type),
        CfgParam('OS_TENANT_NAME', None, six.text_type),
        CfgParam('VERBOSE', False, bool),
    ]

    _config_dict = {cfg.key: cfg for cfg in _configuration}
    _config_keys = _config_dict.keys()

    def __init__(self):
        """Set the default values"""

        # init all parameters to default values
        for cfg in self._configuration:
            setattr(self, cfg.key, cfg.default)

    def read(self, cfg):
        """Read the configuration."""
        LOGGER.info('Reading the OS plugin configuration')
        assert 'MODULE' == cfg.key.upper()
        self._read_node(cfg)

        # verify the configuration
        error = False
        for key in self._config_keys:
            if getattr(self, key, None) is None:
                LOGGER.error('Configuration parameter %s not set.', key)
                error = True
        if error:
            LOGGER.error(
                'Collectd plugin will not work properly')
        else:
            LOGGER.info('Configuration OK')
