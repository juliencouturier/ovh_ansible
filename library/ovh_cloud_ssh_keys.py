#!/usr/bin/env python

ANSIBLE_METADATA = {
    'metadata_version': '1.0',
    'supported_by': 'community',
    'status': ['preview']
        }

DOCUMENTATION = '''
---
module: ovh_cloud_ssh_keys
short_description: Manage OVH Cloud SSH Keys
description:
    - Add/Delete/Modify SSH Keys in OVH Public Cloud
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
    cloud_name:
        required: true
        description: The name of the cloud where ssh key has to be created
    state:
        required: false
        default: present
        choices: ['present', 'absent']
        description:
            - Determines whether the ssh key has to be created/modified or deleted
    publicKey:
        required: false
        description:
            - Public SSH Key to declare on OVH Cloud
    region:
        required: false
        default: None
        description:
            - The region to create SSH Key
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

from ansible.module_utils.ovh_utils import HAS_OVH, get_ovh_client, get_cloud_id, get_sshkey, APIError

# For Ansible < 2.1
# Still works on Ansible 2.2.0
from ansible.module_utils.basic import *

# For Ansible >= 2.1
# bug: doesn't work with ansible 2.2.0
# from ansible.module_utils.basic import AnsibleModule

def main():
    module = AnsibleModule(
            argument_spec=dict(
                state=dict(default='present', choices=['present', 'absent']),
                name=dict(required=True),
                cloud_name=dict(required=True),
                publicKey=dict(required=False, default=None),
                region=dict(required=False, default=None),
                endpoint=dict(required=False, default=None),
                application_key=dict(required=False, default=None, no_log=True),
                application_secret=dict(required=False, default=None, no_log=True),
                consumer_key=dict(required=False, default=None, no_log=True),
                ),
            supports_check_mode=True
            )
    if not HAS_OVH:
        module.fail_json(msg='OVH Api wrapper not installed')
    try:
        client = get_ovh_client(module)
    except APIError as apiError:
        module.fail_json(
            changed=False, msg="Failed to call OVH API on initialization: {0}".format(apiError))
    if module.params['state'] == 'present' and not module.params['publicKey']:
        module.fail_json(changed=False, msg="publicKey is needed to create a key")               
    cloud_id = get_cloud_id(client, module, module.params['cloud_name'])
    existing_key = get_sshkey(client, module, cloud_id, module.params['name'])
    if existing_key is None:
        if module.params['state'] == 'absent':
            module.exit_json(changed=False)
        elif module.params['state'] == 'present':
            if module.check_mode:
                module.exit_json(changed=False, msg="Key has to be created")            
            else:
                try:
                    client.post('/cloud/project/%s/sshkey' % cloud_id,
                        name=module.params['name'],
                        publicKey=module.params['publicKey'],
                        region=module.params['region'],
                    )
                    module.exit_json(changed=True, msg="Key %s created" % module.params['name'])            
                except APIError as apiError:
                    module.fail_json(changed=False, msg="Failed to call OVH API on key creation: {0}".format(apiError))                        
    else:
        if module.params['state'] == 'absent':
            if module.check_mode:
                module.exit_json(changed=False, msg="Key has to be deleted")            
            else:       
                try:
                    client.delete('/cloud/project/%s/sshkey/%s' % (cloud_id, existing_key['id']))         
                    module.exit_json(changed=True, msg="Key %s deleted" % module.params['name'])        
                except APIError as apiError:
                    module.fail_json(changed=False, msg="Failed to call OVH API on key delete: {0}".format(apiError))       
        elif module.params['state'] == 'present':
            if existing_key['publicKey'] == module.params['publicKey']:
                module.exit_json(changed=False, msg="Key %s already exists" % module.params['name'])                    
            else:
                if module.check_mode:
                    module.exit_json(changed=False, msg="Key has to be changed")            
                else:       
                    try:
                        client.delete('/cloud/project/%s/sshkey/%s' % (cloud_id, existing_key['id']))         
                        client.post('/cloud/project/%s/sshkey' % cloud_id,
                            name=module.params['name'],
                            publicKey=module.params['publicKey'],
                            region=module.params['region'],
                        )                        
                        module.exit_json(changed=True, msg="Key %s changed" % module.params['name'])        
                    except APIError as apiError:
                        module.fail_json(changed=False, msg="Failed to call OVH API on key change: {0}".format(apiError))       
    

if __name__ == '__main__':
        main()
