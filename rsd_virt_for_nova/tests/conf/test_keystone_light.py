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

"""Tests for the RSD keystone_light authentication."""

from nova import test

from rsd_virt_for_nova.conf.keystone_light import ClientV3


class TestClientV3(test.NoDBTestCase):
    """Test class for configurations."""

    def setUp(self):
        """Initialize configuration test class."""
        super(TestClientV3, self).setUp()

        self.client = ClientV3("my_auth_url", "user", "pass", "tenant")

    def test_ClientV3_init(self):
        """Test initialising keystone clientv3."""
        self.assertEqual(self.client.auth_url, "my_auth_url")
        self.assertEqual(self.client.username, "user")
        self.assertEqual(self.client.password, "pass")
        self.assertEqual(self.client.tenant_name, "tenant")
        self.assertEqual(self.client._auth_token, '')
        self.assertEqual(self.client._services, ())
        self.assertEqual(self.client._services_by_name, {})
