#!/usr/bin/python
#
# Copyright (c) 2018 Yunge Zhu, <yungez@microsoft.com>
#
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}


DOCUMENTATION = '''
---
module: azure_rm_appserviceplan
version_added: "2.7"
short_description: Manage App Service Plan
description:
    - Create, update and delete instance of App Service Plan.

options:
    resource_group:
        description:
            - Name of the resource group to which the resource belongs.
        required: True

    name:
        description:
            - Unique name of the app service plan to create or update.
        required: True

    location:
        description:
            - Resource location. If not set, location from the resource group will be used as default.

    sku:
        description:
            - "The pricing tiers, e.g., F1(Free), D1(Shared), B1(Basic Small), B2(Basic Medium), B3(Basic Large), S1(Standard Small), P1(Premium Small), P1V2(Premium V2 Small) etc."
            - Please see https://azure.microsoft.com/en-us/pricing/details/app-service/plans/ for more detail.
            - For linux app service plan, please see https://azure.microsoft.com/en-us/pricing/details/app-service/linux/ for more detail.

    is_linux:
        description:
            - Descirbe whether to host webapp on Linux worker.
        type: bool
        default: false

    number_of_workers:
        description:
            - Describe number of workers to be allocated.

    admin_site_name:
        description:
            - The name of the admin web app.
            - Only used in update operation.

    state:
      description:
        - Assert the state of the app service plan.
        - Use 'present' to create or update an app service plan and 'absent' to delete it.
      default: present
      choices:
        - absent
        - present

extends_documentation_fragment:
    - azure
    - azure_tags

author:
    - "Yunge Zhu(@yungezz)"

'''

EXAMPLES = '''
    - name: Create a windows web app with non-exist app service plan
      azure_rm_webapp:
        resource_group: myresourcegroup
        name: mywinwebapp
        plan:
          resource_group: myappserviceplan_rg
          name: myappserviceplan
          is_linux: false
          sku: S1

    - name: Create a docker web app with some app settings, with docker image
      azure_rm_webapp:
        resource_group: myresourcegroup
        name: mydockerwebapp
        plan:
          resource_group: appserviceplan_test
          name: myappplan
          is_linux: true
          sku: S1
          number_of_workers: 2
        app_settings:
          testkey: testvalue
          testkey2: testvalue2
        container_settings:
          name: ansible/ansible:ubuntu1404

    - name: Create a docker web app with private acr registry
      azure_rm_webapp:
        resource_group: myresourcegroup
        name: mydockerwebapp
        plan: myappplan
        app_settings:
          testkey: testvalue
        container_settings:
          name: ansible/ubuntu1404
          registry_server_url: myregistry.io
          registry_server_user: user
          registry_server_password: pass

    - name: Create a linux web app with Node 6.6 framework
      azure_rm_webapp:
        resource_group: myresourcegroup
        name: mylinuxwebapp
        plan:
          resource_group: appserviceplan_test
          name: myappplan
        app_settings:
          testkey: testvalue
        linux_framework:
          name: node
          version: 6.6
'''

RETURN = '''
azure_webapp:
    description: Facts about the current state of the web app.
    returned: always
    type: dict
    sample: {
        "availability_state": "Normal",
        "client_affinity_enabled": true,
        "client_cert_enabled": false,
        "container_size": 0,
        "daily_memory_time_quota": 0,
        "default_host_name": "ansiblewindowsaaa.azurewebsites.net",
        "enabled": true,
        "enabled_host_names": [
            "ansiblewindowsaaa.azurewebsites.net",
            "ansiblewindowsaaa.scm.azurewebsites.net"
        ],
        "host_name_ssl_states": [
            {
                "host_type": "Standard",
                "name": "ansiblewindowsaaa.azurewebsites.net",
                "ssl_state": "Disabled"
            },
            {
                "host_type": "Repository",
                "name": "ansiblewindowsaaa.scm.azurewebsites.net",
                "ssl_state": "Disabled"
            }
        ],
        "host_names": [
            "ansiblewindowsaaa.azurewebsites.net"
        ],
        "host_names_disabled": false,
        "id": "/subscriptions/<subscription_id>/resourceGroups/ansiblewebapp1/providers/Microsoft.Web/sites/ansiblewindowsaaa",
        "kind": "app",
        "last_modified_time_utc": "2018-05-14T04:50:54.473333Z",
        "location": "East US",
        "name": "ansiblewindowsaaa",
        "outbound_ip_addresses": "52.170.7.25,52.168.75.147,52.179.5.98,52.179.1.81,52.179.4.232",
        "repository_site_name": "ansiblewindowsaaa",
        "reserved": false,
        "resource_group": "ansiblewebapp1",
        "scm_site_also_stopped": false,
        "server_farm_id": "/subscriptions/<subscription_id>/resourceGroups/test/providers/Microsoft.Web/serverfarms/plan1",
        "state": "Running",
        "tags": {},
        "type": "Microsoft.Web/sites",
        "usage_state": "Normal"
    }
'''

import time
from ansible.module_utils.azure_rm_common import AzureRMModuleBase

try:
    from msrestazure.azure_exceptions import CloudError
    from msrestazure.azure_operation import AzureOperationPoller
    from msrest.serialization import Model
    from azure.mgmt.web.models import (
        app_service_plan, AppServicePlan, SkuDescription, NameValuePair
    )
except ImportError:
    # This is handled in azure_rm_common
    pass

def _normalize_sku(sku):
    if sku is None:
        return sku

    sku = sku.upper()
    if sku == 'FREE':
        return 'F1'
    elif sku == 'SHARED':
        return 'D1'
    return sku


def get_sku_name(tier):
    tier = tier.upper()
    if tier == 'F1' or tier == "FREE":
        return 'FREE'
    elif tier == 'D1' or tier == "SHARED":
        return 'SHARED'
    elif tier in ['B1', 'B2', 'B3', 'BASIC']:
        return 'BASIC'
    elif tier in ['S1', 'S2', 'S3']:
        return 'STANDARD'
    elif tier in ['P1', 'P2', 'P3']:
        return 'PREMIUM'
    elif tier in ['P1V2', 'P2V2', 'P3V2']:
        return 'PREMIUMV2'
    else:
        return None


class AzureRMAppServicePlans(AzureRMModuleBase):
    """Configuration class for an Azure RM App Service Plan resource"""

    def __init__(self):
        self.module_arg_spec = dict(
            resource_group=dict(
                type='str',
                required=True
            ),
            name=dict(
                type='str',
                required=True
            ),
            location=dict(
                type='str'
            ),
            sku=dict(
                type='str'
            ),
            is_linux=dict(
                type='bool',
                default=False
            ),
            number_of_workers=dict(
                type='str'
            ),
            admin_site_name=dict(
                type='str'
            ),
            state=dict(
                type='str',
                default='present',
                choices=['present', 'absent']
            )
        )

        self.resource_group = None
        self.name = None
        self.location = None

        self.sku = None
        self.is_linux = None
        self.number_of_workers = None
        self.admin_site_name = None

        self.results = dict(
            changed=False,
            ansible_facts=dict(azure_appserviceplan=None)
        )
        self.state = None

        super(AzureRMAppServicePlans, self).__init__(derived_arg_spec=self.module_arg_spec,
                                                     supports_check_mode=True,
                                                     supports_tags=True)

    def exec_module(self, **kwargs):
        """Main module execution method"""

        for key in list(self.module_arg_spec.keys()) + ['tags']:
            if kwargs[key]:
                setattr(self, key, kwargs[key])

        old_response = None
        response = None
        to_be_updated = False

        # set location
        resource_group = self.get_resource_group(self.resource_group)
        if not self.location:
            self.location = resource_group.location

        # get app service plan
        old_response = self.get_app_service_plan()

        # if not existing
        if not old_response:
            self.log("App Service plan doesn't exist")

            if self.state == "present":
                to_be_updated = True

                if not self.sku:
                    self.fail('Please specify sku in plan when creation')

        else:
            # existing web app, do update
            self.log("App Service Plan already exists")

            if self.state == 'present':
                self.log('Result: {0}'.format(old_response))

                update_tags, old_response['tags'] = self.update_tags(
                    old_response.get('tags', dict()))

                if update_tags:
                    to_be_updated = True

                # check if sku changed
                if self.sku and get_sku_name(_normalize_sku(self.sku)) != old_response.sku:
                    to_be_updated = True

                # check if number_of_workers changed
                if self.number_of_workers and self.number_of_workers != old_response.number_of_workers:
                    to_be_updated = True

                # check if admin_site_name changed
                if self.admin_site_name and self.admin_site_name != old_response.admin_site_name:
                    to_be_updated = True
\
                if self.is_linux and self.is_linux != old_response.reserved:
                    self.fail("Operation not allowed: cannot update is_linux of app service plan.")
            
        if old_response:
            self.results['ansible_facts']['azure_appserviceplan'] = old_response

        if to_be_updated:
            self.log('Need to Create/Update app service plan')
            self.results['changed'] = True

            if self.check_mode:
                return self.results

            response = self.create_or_update_plan()
            self.results['ansible_facts']['azure_appserviceplan'] = response

        if self.state == 'absent' and old_response:
            self.log("Delete Web App instance")
            self.results['changed'] = True

            if self.check_mode:
                return self.results

            self.delete_webapp()

            self.log('Web App instance deleted')

        return self.results

    def get_plan(self):
        '''
        Gets app service plan
        :return: deserialized app service plan dictionary
        '''
        self.log("Get App Service Plan {0}".format(self.name))

        try:
            response = self.web_client.app_service_plans.get(self.resource_group, self.name)
            self.log("Response : {0}".format(response))
            self.log("App Service Plan : {0} found".format(response.name))

            return response.as_dict()
        except CloudError as ex:
            self.log("Didn't find app service plan {0} in resource group {1}".format(self.name, self.resource_group))

        return False

    def create_or_update_plan(self):
        '''
        Creates app service plan
        :return: deserialized app service plan dictionary
        '''
        self.log("Create App Service Plan {0}".format(self.name))

        try:
            # normalize sku
            sku = _normalize_sku(self.sku)

            sku_def = SkuDescription(tier=get_sku_name(
                sku), name=sku, capacity=(self.get('number_of_workers', None)))
            plan_def = AppServicePlan(
                location=self.location, app_service_plan_name=self.name, sku=sku_def, reserved=(self.is_linux, None)))

            if self.admin_site_name:
                plan_def.admin_site_name = self.admin_site_name

            poller = self.web_client.app_service_plans.create_or_update(self.resource_group, self.name, plan_def)

            if isinstance(poller, AzureOperationPoller):
                response = self.get_poller_result(poller)

            self.log("Response : {0}".format(response))

            return response.as_dict()
        except CloudError as ex:
            self.fail("Failed to create app service plan {0} in resource group {1}: {2}".format(self.name, self.resource_group, str(ex)))



def main():
    """Main execution"""
    AzureRMWebApps()


if __name__ == '__main__':
    main()
