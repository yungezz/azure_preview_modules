#!/usr/bin/python
#
# Copyright (c) 2018 Yunge Zhu, <yungez@microsoft.com>
#
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'certified'}


DOCUMENTATION = '''
---
module: azure_rm_webapp_facts

version_added: "2.7"

short_description: Get azure web app facts.

description:
    - Get facts for a specific web app.

options:
    name:
        description:
            - Only show results for a specific web app.
    resource_group:
        description:
            - Limit results by resource group.
        required: True
    tags:
        description:
            - Limit results by providing a list of tags. Format tags as 'key' or 'key:value'.
    format:
        description:
            - Format of the data returned.
            - If C(raw) is selected information will be returned in raw format from Azure Python SDK.
            - If C(curated) is selected the structure will be identical to input parameters of azure_rm_webapp module.
            - In Ansible 2.5 and lower facts are always returned in raw format.
        default: 'raw'
        choices:
            - 'curated'
            - 'raw'
    info_level:
        description:
            - A list to describe what information of the web app to return.
            - Only works with C(name) option.
        suboptions:
            level: 
                description:
                    - name of return information level.
                choices:
                    - basic
                    - app_settings
                    - configuration
                    - deployment_slot
                default: basic


extends_documentation_fragment:
    - azure

author:
    - "Yunge Zhu (@yungezz)"
'''

EXAMPLES = '''
    - name: Get facts for one Public IP
      azure_rm_publicip_facts:
        resource_group: Testing
        name: publicip001

    - name: Get facts for all Public IPs within a resource groups
      azure_rm_publicip_facts:
        resource_group: Testing
'''

RETURN = '''
azure_publicipaddresses:
    description: List of public IP address dicts.
    returned: always
    type: list
    example: [{
        "etag": 'W/"a31a6d7d-cb18-40a5-b16d-9f4a36c1b18a"',
        "id": "/subscriptions/XXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXX/resourceGroups/Testing/providers/Microsoft.Network/publicIPAddresses/pip2001",
        "location": "eastus2",
        "name": "pip2001",
        "properties": {
            "idleTimeoutInMinutes": 4,
            "provisioningState": "Succeeded",
            "publicIPAllocationMethod": "Dynamic",
            "resourceGuid": "29de82f4-a7da-440e-bd3d-9cabb79af95a"
        },
        "type": "Microsoft.Network/publicIPAddresses"
    }]
'''
try:
    from msrestazure.azure_exceptions import CloudError
    from azure.common import AzureMissingResourceHttpError, AzureHttpError
except:
    # This is handled in azure_rm_common
    pass

from ansible.module_utils.azure_rm_common import AzureRMModuleBase

AZURE_OBJECT_CLASS = 'WebApp'

info_level_spec = dict(
    level=dict(
        type='str',
        choices=[
            'basic',
            'configuration',
            'app_settings'
        ],
        default='basic'
    )
)


class AzureRMWebAppFacts(AzureRMModuleBase):

    def __init__(self):

        self.module_arg_spec = dict(
            name=dict(type='str'),
            resource_group=dict(
                type='str',
                required=True
            ),
            tags=dict(type='list'),
            format=dict(
                type='str',
                choices=['curated',
                         'raw'],
                default='raw'
            ),
            info_level=dict(
                type='list',
                elements='dict',
                options=info_level_spec
            )
        )

        self.results = dict(
            changed=False,
            ansible_facts=dict(azure_webapps=[])
        )

        self.name = None
        self.resource_group = None
        self.tags = None
        self.info_level = None

        super(AzureRMWebAppFacts, self).__init__(self.module_arg_spec,
                                                   supports_tags=False,
                                                   facts_module=True)

    def exec_module(self, **kwargs):

        for key in self.module_arg_spec:
            setattr(self, key, kwargs[key])

        if self.format == "curated":
            self.fail('Not implemented.')

        if not self.name and self.info_level:
            self.fail('info_level must be specified with name parameter')

        if self.name:
            self.results['ansible_facts']['azure_webapps'] = self.list_by_name()

            if self.info_level:
                for level in self.info_level:
                    if level["level"] == "configuration":
                        self.results['ansible_facts']['azure_webapps'][0]['site_config'] = self.list_webapp_configuration()
                    if level["level"] == "app_settings":
                        self.results['ansible_facts']['azure_webapps'][0]['app_settings'] = self.list_webapp_appsettings()

        elif self.resource_group:
            self.results['ansible_facts']['azure_webapps'] = self.list_by_resource_group()        

        return self.results

    def list_by_name(self):
        self.log('Get web app {0}'.format(self.name))
        item = None
        result = []

        try:
            item = self.web_client.web_apps.get(self.resource_group, self.name)
        except CloudError:
            pass

        if item and self.has_tags(item.tags, self.tags):
            pip = self.serialize_obj(item, AZURE_OBJECT_CLASS)
            pip['name'] = item.name
            pip['type'] = item.type
            result = [pip]

        return result

    def list_by_resource_group(self):
        self.log('List web apps in resource groups {0}'.format(self.resource_group))
        try:
            response = list(self.web_client.web_apps.list_by_resource_group(self.resource_group))
        except CloudError as exc:
            self.fail("Error listing web apps in resource groups {0} - {1}".format(self.resource_group, str(exc)))

        results = []
        for item in response:
            if self.has_tags(item.tags, self.tags):
                pip = self.serialize_obj(item, AZURE_OBJECT_CLASS)
                pip['name'] = item.name
                pip['type'] = item.type
                results.append(pip)
        return results    

    def list_webapp_configuration(self):
        self.log('Get web app {0} configuration'.format(self.name))

        response = []

        try:
            response = self.web_client.web_apps.get_configuration(resource_group_name=self.resource_group, name=self.name)
        except CloudError as ex:
            self.fail('Error getting web app {0} configuration'.format(self.name))
        
        return response.as_dict()

    def list_webapp_appsettings(self):
        self.log('Get web app {0} app settings'.format(self.name))

        response = []

        try:
            response = self.web_client.web_apps.list_application_settings(resource_group_name=self.resource_group, name=self.name)
        except CloudError as ex:
            self.fail('Error getting web app {0} app settings'.format(self.name))
        
        return response.as_dict()



def main():
    AzureRMWebAppFacts()


if __name__ == '__main__':
    main()
