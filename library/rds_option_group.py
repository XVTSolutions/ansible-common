#!/usr/bin/python
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

ANSIBLE_METADATA = {'metadata_version': '1.0',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''
module: rds_option_group
short_description: Manages RDS Option Groups
description:
  -Manages the creation, modification, deletion of RDS option groups.
version_added: "2.4"
author: "Nick Aslanidis (@naslanidis)"
options:
  option_group_name:
    description:
      - Specifies the name of the option group to be created.
    required: true
    default: null
  engine_name:
    description:
      - Specifies the name of the engine that this option group should be associated with.
    required: true
    default: null
  major_engine_version:
    description:
      - Specifies the major version of the engine that this option group should be associated with.
    required: true
    default: null
  option_group_description:
    description:
      - The description of the option group.
    required: true
    default: null
  apply_immediately:
    description:
      - Indicates whether the changes should be applied immediately, or during the next maintenance window
    required: false
    default: false
  options:
    description:
      - Options in this list are added to the option group.
      - If already present, the specified configuration is used to update the existing configuration.
      - If none are supplied, any existing options are removed.
extends_documentation_fragment:
  - aws
  - ec2
'''

EXAMPLES = '''
# Create an RDS Mysql Option group
- name: Create an RDS Mysql Option group
  rds_option_group:
    region: ap-southeast-2
    profile: production
    state: present
    option_group_name: test-mysql-option-group
    engine_name: mysql
    major_engine_version: 5.6
    option_group_description: test mysql option group
    apply_immediately: true
    options:
      - OptionName: MEMCACHED
        Port: 11211
        VpcSecurityGroupMemberships:
          - sg-d188c123
        OptionSettings:
          - Name: MAX_SIMULTANEOUS_CONNECTIONS
            Value: '20'
          - Name: CHUNK_SIZE_GROWTH_FACTOR
            Value: '1.25'
  register: new_rds_mysql_option_group

# Remove currently configured options for an option group by removing options argument
- name: Create an RDS Mysql Option group
  rds_option_group:
    region: ap-southeast-2
    profile: production
    state: present
    option_group_name: test-mysql-option-group
    engine_name: mysql
    major_engine_version: 5.6
    option_group_description: test mysql option group
    apply_immediately: true
  register: rds_mysql_option_group

# Delete an RDS Mysql Option group
- name: Create an RDS Mysql Option group
  rds_option_group:
    region: ap-southeast-2
    profile: production
    state: absent
    option_group_name: test-mysql-option-group
  register: deleted_rds_mysql_option_group
'''

RETURN = '''
allows_vpc_and_non_vpc_instance_memberships:
  description: Specifies the allocated storage size in gigabytes (GB).
  returned: when state=present
  type: boolean
  sample: false
engine_name:
  description: Indicates the name of the engine that this option group can be applied to.
  returned: when state=present
  type: string
  sample: "mysql"
major_engine_version:
  description: Indicates the major engine version associated with this option group.
  returned: when state=present
  type: string
  sample: "5.6"
option_group_description:
  description: Provides a description of the option group.
  returned: when state=present
  type: string
  sample: "test mysql option group"
option_group_name:
  description: Specifies the name of the option group.
  returned: when state=present
  type: string
  sample: "test-mysql-option-group"
options:
  description: Indicates what options are available in the option group.
  returned: when state=present
  type: list
  sample: []
vpc_id:
  description: If present, this option group can only be applied to instances that are in the VPC indicated by this field.
  returned: when state=present
  type: string
  sample: "vpc-aac12acf"
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.ec2 import boto3_conn, ec2_argument_spec, get_aws_connection_info
from ansible.module_utils.ec2 import HAS_BOTO3, camel_dict_to_snake_dict

import traceback

try:
    import botocore
except ImportError:
    pass  # caught by imported HAS_BOTO3


def get_option_group(client, module):
    params = dict()
    params['OptionGroupName'] = module.params.get('option_group_name')

    try:
        response = client.describe_option_groups(**params)

    except client.exceptions.OptionGroupNotFoundFault:
      response = {'OptionGroupsList': list([None])}

    except botocore.exceptions.ClientError as e:
        if 'OptionGroupNotFound' not in e.message:
            module.fail_json(msg=str(e), exception=traceback.format_exc(),
                             **camel_dict_to_snake_dict(e.response))
        else:
            response = None

    results = response['OptionGroupsList'][0]
    return results


def create_option_group_options(client, module):
    changed = True
    params = dict()
    params['OptionGroupName'] = module.params.get('option_group_name')
    params['OptionsToInclude'] = module.params.get('options')

    if module.params.get('apply_immediately'):
        params['ApplyImmediately'] = module.params.get('apply_immediately')

    try:
        response = client.modify_option_group(**params)
    except botocore.exceptions.ClientError as e:
        module.fail_json(msg=str(e), exception=traceback.format_exc(),
                         **camel_dict_to_snake_dict(e.response))

    results = response['OptionGroup']
    return changed, results


def remove_option_group_options(client, module, options_to_remove):
    changed = True
    params = dict()
    params['OptionGroupName'] = module.params.get('option_group_name')
    params['OptionsToRemove'] = options_to_remove

    if module.params.get('apply_immediately'):
        params['ApplyImmediately'] = module.params.get('apply_immediately')

    try:
        response = client.modify_option_group(**params)
    except botocore.exceptions.ClientError as e:
        module.fail_json(msg=str(e), exception=traceback.format_exc(),
                         **camel_dict_to_snake_dict(e.response))

    results = response['OptionGroup']
    return changed, results


def create_option_group(client, module):
    changed = True
    params = dict()
    params['OptionGroupName'] = module.params.get('option_group_name')
    params['EngineName'] = module.params.get('engine_name')
    params['MajorEngineVersion'] = str(module.params.get('major_engine_version'))
    params['OptionGroupDescription'] = module.params.get('option_group_description')

    try:
        response = client.create_option_group(**params)
    except botocore.exceptions.ClientError as e:
        module.fail_json(msg=str(e), exception=traceback.format_exc(),
                         **camel_dict_to_snake_dict(e.response))

    results = response['OptionGroup']
    return changed, results


def match_option_group_options(client, module):
    requires_update = False
    new_options = module.params.get('options')

    # Get existing option groups and compare to our new options spec
    current_option_group = get_option_group(client, module)
    if current_option['Options'] == []:
        requires_update = True
    else:
        for option in current_option['Options']:
            for setting_name in new_options:
                if setting_name['OptionName'] == option['OptionName']:
                    for name in iter(setting_name):
                        # Security groups need to be handled separately due to different keys on request and what is
                        # returned by the API
                        if name in iter(option) and name != 'OptionSettings' and name != 'VpcSecurityGroupMemberships':
                            if setting_name[name] != option[name]:
                                requires_update = True
                        if name in iter(option) and name == 'VpcSecurityGroupMemberships':
                            for groups in option[name]:
                                if groups['VpcSecurityGroupId'] not in setting_name[name]:
                                    requires_update = True

                for new_option in new_options:
                    if option['OptionName'] == new_option['OptionName']:
                        for current_option_setting in option['OptionSettings']:
                            for new_option_setting in new_option['OptionSettings']:
                                if new_option_setting['Name'] == current_option_setting['Name']:
                                    if new_option_setting['Value'] != current_option_setting['Value']:
                                        requires_update = True

    return requires_update


def compare_option_group(client, module):
    current_option_group = get_option_group(client, module)
    new_options = module.params.get('options')
    to_be_added = None
    to_be_removed = None
    for current_option in current_option_group['OptionGroupsList']:
        # Catch new settings you've provided that aren't in the current settings
        old_settings = []
        new_settings = []
        new_settings = set([item['OptionName'] for item in new_options])
        old_settings = set([item['OptionName'] for item in current_option['Options']])
        if new_settings != old_settings:
            to_be_added = list(new_settings - old_settings)
            to_be_removed = list(old_settings - new_settings)

        return to_be_added, to_be_removed


def setup_rds_option_group(client, module):
    results = []
    changed = False

    # Check if there is an existing options group
    existing_option_group = get_option_group(client, module)

    if existing_option_group:
        results = existing_option_group
        if module.params.get('options'):
            # Check if existing options require updating
            update_required = match_option_group_options(client, module)
            # Check if there are options to be added or removed
            to_be_added, to_be_removed = compare_option_group(client, module)
            if to_be_added or update_required:
                changed, new_option_group_options = create_option_group_options(client, module)
            if to_be_removed:
                changed, removed_option_group_options = remove_option_group_options(client, module, to_be_removed)
            # If changed, get updated version of option group
            if changed:
                results = get_option_group(client, module)

        else:
            # No options were supplied. If options exist, remove them
            current_option_group = get_option_group(client, module)
            if current_option_group['Options'] != []:
                # Here we would call our remove options function
                options_to_remove = []
                for option in current_option_group['Options']:
                    options_to_remove.append(option['OptionName'])

                changed, removed_option_group_options = remove_option_group_options(client, module, options_to_remove)
                # If changed, get updated version of option group
                if changed:
                    results = get_option_group(client, module)

    else:
        changed, new_option_group = create_option_group(client, module)

        if module.params.get('options'):
            changed, new_option_group_options = create_option_group_options(client, module)
        results = get_option_group(client, module)

    return changed, results


def remove_rds_option_group(client, module):
    changed = False
    params = dict()
    params['OptionGroupName'] = module.params.get('option_group_name')

    # Check if there is an existing options group
    existing_option_group = get_option_group(client, module)

    if existing_option_group:
        changed = True
        try:
            client.delete_option_group(**params)
        except botocore.exceptions.ClientError as e:
            module.fail_json(msg=str(e), exception=traceback.format_exc(),
                             **camel_dict_to_snake_dict(e.response))
    return changed, None


def main():
    argument_spec = ec2_argument_spec()
    argument_spec.update(
        dict(
            option_group_name=dict(required=True),
            engine_name=dict(),
            major_engine_version=dict(),
            option_group_description=dict(),
            options=dict(type='list'),
            apply_immediately=dict(type='bool'),
            state=dict(default='present', choices=['present', 'absent']),
        ),
    )
    module = AnsibleModule(argument_spec=argument_spec)

    if not HAS_BOTO3:
        module.fail_json(msg='boto3 and botocore are required.')
    state = module.params.get('state')
    try:
        region, ec2_url, aws_connect_kwargs = get_aws_connection_info(module, boto3=True)
        client = boto3_conn(module, conn_type='client', resource='rds', region=region, endpoint=ec2_url, **aws_connect_kwargs)
    except botocore.exceptions.NoCredentialsError as e:
        module.fail_json(msg="Can't authorize connection - " + str(e))

    invocations = {
        "present": setup_rds_option_group,
        "absent": remove_rds_option_group
    }

    changed, results = invocations[state](client, module)
    module.exit_json(changed=changed, **camel_dict_to_snake_dict(results))


if __name__ == '__main__':
    main()
