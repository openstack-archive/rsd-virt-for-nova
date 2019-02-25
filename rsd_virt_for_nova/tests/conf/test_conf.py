# 2017 - 2018 Intel Corporation. All rights reserved.
#
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

"""Tests for the RSD configuration options."""

from nova import test

from rsd_virt_for_nova import conf as cfg

CONF = cfg.CONF


class TestConf(test.NoDBTestCase):
    """Test class for configurations."""

    def setUp(self):
        """Initialize configuration test class."""
        super(TestConf, self).setUp()

    def test_conf(self):
        """Test the default rsd config values."""
        # Try an option from each grouping of static options

        # PODM IP
        self.assertEqual('localhost', CONF.rsd.podm_ip)
        # PODM username
        self.assertEqual('admin', CONF.rsd.podm_user)
        # PODM password
        self.assertEqual('admin', CONF.rsd.podm_password)
        # PODM port
        self.assertEqual(8443, CONF.rsd.podm_port)
