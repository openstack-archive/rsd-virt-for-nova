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

import mock

import requests

from nova import test

from rsd_virt_for_nova.conf.keystone_light import ClientV3
from rsd_virt_for_nova.conf.keystone_light import MissingServices


class TestClientV3(test.NoDBTestCase):
    """Test class for configurations."""

    def setUp(self):
        """Initialize configuration test class."""
        super(TestClientV3, self).setUp()

        self.client = ClientV3("my_auth_url", "user", "pass", "tenant")
        self.test_authtoken = "c5bbb1c9a27e470fb482de2a718e08c2"
        self.test_public_endpoint = "http://public_endpoint"
        self.test_internal_endpoint = "http://internal_endpoint"
        self.test_region = "RegionOne"

        response = {"token": {
            "is_domain": 'false',
            "methods": [
                "password"
            ],
            "roles": [
                {
                    "id": "eacf519eb1264cba9ad645355ce1f6ec",
                    "name": "ResellerAdmin"
                },
                {
                    "id": "63e481b5d5f545ecb8947072ff34f10d",
                    "name": "admin"
                }
            ],
            "is_admin_project": 'false',
            "project": {
                "domain": {
                    "id": "default",
                    "name": "Default"
                },
                "id": "97467f21efb2493c92481429a04df7bd",
                "name": "service"
            },
            "catalog": [
                {
                    "endpoints": [
                        {
                            "url": self.test_public_endpoint + '/',
                            "interface": "public",
                            "region": self.test_region,
                            "region_id": self.test_region,
                            "id": "5e1d9a45d7d442ca8971a5112b2e89b5"
                        },
                        {
                            "url": "http://127.0.0.1:8777",
                            "interface": "admin",
                            "region": self.test_region,
                            "region_id": self.test_region,
                            "id": "5e8b536fde6049d381ee540c018905d1"
                        },
                        {
                            "url": self.test_internal_endpoint + '/',
                            "interface": "internal",
                            "region": self.test_region,
                            "region_id": self.test_region,
                            "id": "db90c733ddd9466696bc5aaec43b18d0"
                        }
                    ],
                    "type": "compute",
                    "id": "f6c15a041d574bc190c70815a14ab851",
                    "name": "nova"
                }
            ]
            }
        }

        self.mock_response = mock.Mock()
        self.mock_response.json.return_value = response
        self.mock_response.headers = {
            'X-Subject-Token': "c5bbb1c9a27e470fb482de2a718e08c2"
        }

    def test_ClientV3_init(self):
        """Test initialising keystone clientv3."""
        self.assertEqual(self.client.auth_url, "my_auth_url")
        self.assertEqual(self.client.username, "user")
        self.assertEqual(self.client.password, "pass")
        self.assertEqual(self.client.tenant_name, "tenant")
        self.assertEqual(self.client._auth_token, '')
        self.assertEqual(self.client._services, ())
        self.assertEqual(self.client._services_by_name, {})

    @mock.patch.object(requests, "post")
    def test_refresh(self, post_req):
        """Test the refresh function for auth tokens."""
        resp = self.client.refresh()

        url = self.client.auth_url.rstrip('/') + '/auth/tokens'
        params = {
            'auth': {
                'identity': {
                    'methods': ['password'],
                    'password': {
                        'user': {
                            'name': self.client.username,
                            'domain': {'id': 'default'},
                            'password': self.client.password
                        }
                    }
                },
                'scope': {
                    'project': {
                        'name': self.client.tenant_name,
                        'domain': {'id': 'default'}
                    }
                }
            }
        }
        headers = {'Accept': 'application/json'}
        post_req.assert_called_once_with(url, json=params, headers=headers)

        self.assertEqual(resp, post_req.return_value.json()['token'])

    @mock.patch.object(requests, 'post')
    def test_getservice_endpoint(self, mock_post):
        """Test get_service_endpoint"""

        mock_post.return_value = self.mock_response

        client = ClientV3("test_auth_url", "test_username",
                          "test_password", "test_tenant")
        client.refresh()

        endpoint = client.get_service_endpoint('nova')
        self.assertEqual(endpoint, self.test_public_endpoint)

        self.assertRaises(MissingServices,
                client.get_service_endpoint, 'badname')

    @mock.patch.object(requests, 'post')
    def test_getservice_endpoint_error(self, mock_post):
        """Test get service endpoint error"""

        response = {"token": {
            "is_domain": 'false',
            "methods": [
                "password"
            ],
            "roles": [
                {
                    "id": "eacf519eb1264cba9ad645355ce1f6ec",
                    "name": "ResellerAdmin"
                },
                {
                    "id": "63e481b5d5f545ecb8947072ff34f10d",
                    "name": "admin"
                }
            ],
            "is_admin_project": 'false',
            "project": {
                "domain": {
                    "id": "default",
                    "name": "Default"
                },
                "id": "97467f21efb2493c92481429a04df7bd",
                "name": "service"
            },
            "catalog": [
                {
                    "endpoints": [],
                    "type": "compute",
                    "id": "f6c15a041d574bc190c70815a14ab851",
                    "name": "badname"
                }
            ]
            }
        }

        self.mock_response = mock.Mock()
        self.mock_response.json.return_value = response
        self.mock_response.headers = {
            'X-Subject-Token': "c5bbb1c9a27e470fb482de2a718e08c2"
        }
        mock_post.return_value = self.mock_response

        client = ClientV3("test_auth_url", "test_username",
                          "test_password", "test_tenant")

        client.refresh()

        self.assertRaises(MissingServices, client.get_service_endpoint, 'nova')
