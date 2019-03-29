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
A class + functions for managing RSD flavors

Requires the authentication to keystone to perform request to the nova-api's.
This allows the management and creation of RSD specific flavors.
"""

from rsd_virt_for_nova.conf import rsd as cfg

from rsd_virt_for_nova.conf.keystone_light import ClientV3

from oslo_log import log as logging

CONF = cfg.CONF

LOG = logging.getLogger(__name__)


class FlavorManager(object):
    """Implementation of nova compute driver to compose RSD nodes from nova."""

    def __init__(self):
        """Initialize the RSDDriver."""
        self._url_base = None
        self._keystone = None
        self._auth_token = None
        self.headers = None

    def keystone_req(self):
        """Authenticate to keystone."""
        keystone_url = ''
        OS_USERNAME = CONF.rsd.username
        OS_PASSWORD = CONF.rsd.auth_password
        OS_TENANT_NAME = CONF.rsd.tenant_name
        OS_AUTH_URL = CONF.rsd.auth_url
        OS_IDENTITY_VERSION = CONF.rsd.identity_version

        keystone_url = OS_AUTH_URL + '/v' + str(OS_IDENTITY_VERSION)

        self._keystone = ClientV3(
                        auth_url=str(keystone_url),
                        username=OS_USERNAME,
                        password=OS_PASSWORD,
                        tenant_name=OS_TENANT_NAME
                    )
        self._auth_token = self._keystone.auth_token

        return self._keystone

    def _get_base_url(self):
        # get the uri of service endpoint
        endpoint = self._get_endpoint("nova")

        self._url_base = "{}/flavors".format(endpoint)

        return self._url_base

    def _get_endpoint(self, service):
        # get the uri of service endpoint
        endpoint = self._keystone.get_service_endpoint(service)
        return endpoint

    def _create_request_url(self, flavorid, req_type):
        endpoint = self._get_endpoint("nova")
        url = ''
        if req_type == 'delete':
            url = "{}/flavors/%s".format(endpoint) % (flavorid)
        elif req_type == 'update':
            url = "{}/flavors/%s/os-extra_specs".format(endpoint) % (flavorid)
        return url

    def get_headers(self, auth_token):
        self.headers = {'X-Auth-Token': auth_token,
                        'Content-type': 'application/json'}
        return self.headers
