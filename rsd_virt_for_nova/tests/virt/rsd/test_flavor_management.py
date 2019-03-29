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
"""Unit tests for the RSD flavor management class."""

import mock

from rsd_virt_for_nova.conf import rsd as cfg

from rsd_virt_for_nova.virt.rsd import flavor_management
from rsd_virt_for_nova.conf import keystone_light

from oslotest import base


CONF = cfg.CONF


class TestFlavorManager(base.BaseTestCase):
    """A test class for the flavor manager class."""

    def setUp(self):
        """Initial setup of mocks for all of the unit tests."""
        super(TestFlavorManager, self).setUp()
        self.flav_man = flavor_management.FlavorManager()

    def test_init(self):
        """Test the initialisation of a flavor manager instance."""
        self.assertEqual(self.flav_man._url_base, None)
        self.assertEqual(self.flav_man._keystone, None)
        self.assertEqual(self.flav_man._auth_token, None)
        self.assertEqual(self.flav_man.headers, None)

    def test_keystone_req(self):
        """Test a successful keystone request."""
        # TODO(helenam100): write successful and failed versions of test

    @mock.patch.object(flavor_management.FlavorManager, "_get_endpoint")
    def test_get_base_url(self, get_endpoint):
        """Test authentication functionality."""
        url = self.flav_man._get_base_url()

        get_endpoint.assert_called_once_with("nova")
        self.assertEqual(self.flav_man._url_base,
                "{}/flavors".format(get_endpoint.return_value))
        self.assertEqual(url, self.flav_man._url_base)

    @mock.patch.object(keystone_light, "ClientV3")
    def test_get_endpoint_success(self, client):
        """Test getting a valid endpoint for flavor creation."""
        self.flav_man._keystone = client.return_value
        endpoint = self.flav_man._get_endpoint("nova")

        self.flav_man._keystone.get_service_endpoint.assert_called_with("nova")
        self.assertEqual(endpoint,
                self.flav_man._keystone.get_service_endpoint.return_value)

    @mock.patch.object(keystone_light.ClientV3, "get_service_endpoint")
    def test_get_endpoint_failure(self, serv_endpoint):
        """Failed test for getting an endpoint for flavor create."""
        # No valid keystone test
        self.assertRaises(AttributeError, self.flav_man._get_endpoint, "nova")

    @mock.patch.object(flavor_management.FlavorManager, "_get_endpoint")
    def test_create_request_url_delete(self, get_end):
        """Testing creation of a request url for flavor management."""
        url = self.flav_man._create_request_url("flav_id", "delete")

        get_end.assert_called_once_with("nova")
        self.assertEquals(url,
                "{}/flavors/flav_id".format(get_end.return_value))

    @mock.patch.object(flavor_management.FlavorManager, "_get_endpoint")
    def test_create_request_url_update(self, get_end):
        """Testing creation of a request url for flavor management."""
        url = self.flav_man._create_request_url("flav_id", "update")

        get_end.assert_called_once_with("nova")
        self.assertEquals(url,
                "{}/flavors/flav_id/os-extra_specs".format(
                    get_end.return_value))

    @mock.patch.object(flavor_management.FlavorManager, "_get_endpoint")
    def test_create_request_url_invalid(self, get_end):
        """Testing creation of a request url for flavor management."""
        url = self.flav_man._create_request_url("flav_id", "invalid")

        get_end.assert_called_once_with("nova")
        self.assertEquals(url, '')

    def test_get_headers(self):
        """Testing getting headers for requests."""
        headers = self.flav_man.get_headers("my_auth_token")

        self.assertEquals(headers, self.flav_man.headers)
        self.assertEquals(headers,
                 {'X-Auth-Token': "my_auth_token",
                  'Content-type': 'application/json'})
