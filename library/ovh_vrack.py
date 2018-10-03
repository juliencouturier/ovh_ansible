#!/usr/bin/env python

ANSIBLE_METADATA = {
    'metadata_version': '1.0',
    'supported_by': 'community',
    'status': ['preview']
        }

DOCUMENTATION = '''
---
module: ovh_cloud
short_description: Manage OVH Cloud
description:
    - Add/Delete/Modify OVH Public Cloud
author: Julien Couturier
notes:
    - In /etc/ovh.conf (on host that executes module), you should add your
      OVH API credentials like:
      [default]
      ; general configuration: default endpoint
      endpoint=ovh-eu

      [ovh-eu]
      ; configuration specific to 'ovh-eu' endpoint
      application_key=<YOUR APPLICATION KEY>
      application_secret=<YOUR APPLICATIOM SECRET>
      consumer_key=<YOUR CONSUMER KEY>
    - It is also possible to put those conf in ansible variables
requirements:
    - ovh > 0.3.5
options:
    name:
        required: true
        description: The name of ssh key
    state:
        required: false
        default: present
        choices: ['present', 'absent']
        description:
            - Determines whether the ssh key has to be created/modified or deleted
    endpoint:
        required: false
        default: None
        description:
            - EndPoint for ovh API (if not present /etc/ovh.conf is used)
    application_key:
        required: false
        default: None
        description:
            - application_key for ovh API (if not present /etc/ovh.conf is used)
    application_secret
        required: false
        default: None
        description:
            - application_secret for ovh API (if not present /etc/ovh.conf is used)
    consumer_key
        required: false
        default: None
        description:
            - consumer_key for ovh API (if not present /etc/ovh.conf is used)
'''

EXAMPLES = '''
# Add/modifed a key
- name: Add a key
  ovh_cloud_ssh_keys: name='ssh-rsa *****' publicKey='VRACK ID' state='present' cloud_name='MyCloud'

# Add/modifed a key on a region
- name: Add a key
  ovh_cloud_ssh_keys: name='ssh-rsa *****' publicKey='VRACK ID' state='present' region='GRA3' cloud_name='MyCloud'

# Add/modifed a key
- name: Remove a key
  ovh_cloud_ssh_keys: name='ssh-rsa *****' publicKey='VRACK ID' state='absent' cloud_name='MyCloud'
'''

RETURN = ''' # '''

import ast
import yaml

try:
    import json
except ImportError:
    import simplejson as json

from ansible.module_utils.ovh_utils import HAS_OVH, get_ovh_client, get_cloud_id, APIError, get_vrack, create_new_vrack

# For Ansible < 2.1
# Still works on Ansible 2.2.0
from ansible.module_utils.basic import *

# For Ansible >= 2.1
# bug: doesn't work with ansible 2.2.0
# from ansible.module_utils.basic import AnsibleModule

def main():
    module = AnsibleModule(
            argument_spec=dict(
                state=dict(default='present', choices=['present', 'attached', 'absent', 'detached']),
                name=dict(required=True),
                description=dict(required=False, default=''),
                cloud=dict(required=False, default=None),
                endpoint=dict(required=False, default=None),
                application_key=dict(required=False, default=None, no_log=True),
                application_secret=dict(required=False, default=None, no_log=True),
                consumer_key=dict(required=False, default=None, no_log=True),
                ),
            supports_check_mode=True
            )
    if not HAS_OVH:
        module.fail_json(msg='OVH Api wrapper not installed')
    result = {'changed' : False, 'msg':''}
    try:
        client = get_ovh_client(module)
    except APIError as apiError:
        module.fail_json(
            changed=False, msg="Failed to call OVH API on initialization: {0}".format(apiError))       
    existing_vrack = get_vrack(client, module, module.params['name'])
    if existing_vrack is None:
        if module.params['state'] in ['absent', 'detached']:
            module.exit_json(changed=False)
        elif module.params['state'] in ['present', 'attached']:
            if module.check_mode:
                module.exit_json(changed=False, msg="Vrack has to be created")            
            else:
                result['changed'] = True
                result['msg'] += 'VRack created. '
                existing_vrack = create_new_vrack(client, module, module.params['name'], module.params['description'])
    else:
        if module.params['state'] == 'absent':
            if module.check_mode:
                module.exit_json(changed=False, msg="Vrack has to be deleted")            
            else:       
                try:
                    #client.post('/cloud/project/%s/terminate' % (existing_cloud['project_id']))         
                    result['changed'] = True
                    result['msg'] += 'VRack deleted. '
                except APIError as apiError:
                    module.fail_json(changed=False, msg="Failed to call OVH API on delete: {0}".format(apiError))       
    if module.params['state'] in ['attached', 'detached']:
        if module.params['cloud']:
            cloud_id = get_cloud_id(client, module,module.params['cloud'])
            cloud_attached = client.get('/vrack/%s/cloudProject' % existing_vrack['id'])
            if cloud_id in cloud_attached:
                if module.params['state'] == 'detached':
                    try:
                        client.delete('/vrack/%s/cloudProject/%s' % (existing_vrack['id'], cloud_id))         
                        result['changed'] = True
                        result['msg'] += 'VRack detached. '
                    except APIError as apiError:
                        module.fail_json(changed=False, msg="Failed to call OVH API on detach: {0}".format(apiError))                           
            else:
                if module.params['state'] == 'attached':
                    try:
                        client.post('/vrack/%s/cloudProject' % (existing_vrack['id']), project=cloud_id)
                        result['changed'] = True
                        result['msg'] += 'VRack attached. '
                    except APIError as apiError:
                        module.fail_json(changed=False, msg="Failed to call OVH API on attach: {0}".format(apiError))                           
        else:
            module.fail_json(changed=False, msg="A cloudProject, dedicatedServer, dedicatedCloud is needed to attach a vrack")       
    module.exit_json(**result)
  
   
    

if __name__ == '__main__':
        main()
