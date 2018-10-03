#!/usr/bin/env python

ANSIBLE_METADATA = {
    'metadata_version': '1.0',
    'supported_by': 'community',
    'status': ['preview']
        }

DOCUMENTATION = '''
---
module: ovh_volume
short_description: Manage OVH Cloud Instances
description:
    - Add/Delete/Modify Instances in OVH Public Cloud
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
        description: The name of instance
    cloud_name:
        required: true
        description: The name of the cloud where instance has to be created
    state:
        required: false
        default: present
        choices: ['present', 'absent', 'reboot', 'reinstall', 'status']
        description:
            - Determines whether the instance has to be created, modified, deleted, reboot, reinstall or if we want its caracteristics
    flavor:
        required: false
        description:
            - Name of the flavor (vm caracteristics)
    image:
        required: false
        description:
            - Name of the image to deploy    
    region:
        required: true
        description:
            - The region to create isntance
    sshKey:
        required: false    
        description:
            - sshKey_Name to enable
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

from ansible.module_utils.ovh_utils import HAS_OVH, get_ovh_client, get_cloud_id, get_flavor_id, get_image_id, get_sshkey_id, get_instance, APIError

# For Ansible < 2.1
# Still works on Ansible 2.2.0
from ansible.module_utils.basic import *

# For Ansible >= 2.1
# bug: doesn't work with ansible 2.2.0
# from ansible.module_utils.basic import AnsibleModule

def main():
    module = AnsibleModule(
            argument_spec=dict(
                state=dict(default='present', choices=['present', 'absent', 'reboot', 'reinstall', 'status']),
                name=dict(required=True),
                cloud_name=dict(required=True),
                flavor=dict(required=False),
                image=dict(required=False),
                sshKey=dict(required=False),
                monthlyBilling=dict(required=False, default='False', choices=['True', 'False']),
                region=dict(required=False),
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
    cloud_id = get_cloud_id(client, module, module.params['cloud_name'])
    existing_instance = get_instance(client, module, cloud_id, module.params['name'])
    changed = False
    if module.params['state'] not in ['absent', 'status']:
        if not (module.params['flavor'] and module.params['image'] and module.params['sshKey'] and module.params['region']):
            module.fail_json(changed=False, msg="flavor, image and sshKey are needed to create an instance")                       
        else:
            flavor_id= get_flavor_id(client, module, cloud_id, module.params['region'], module.params['flavor'])
            image_id= get_image_id(client, module, cloud_id, module.params['region'], module.params['image'])
            sshKey_id = get_sshkey_id(client, module, cloud_id, module.params['sshKey'])      
    if module.params['state'] == 'status':
        module.exit_json(changed=False, instance=existing_instance)
    if existing_instance is None:
        if module.params['state'] == 'absent':
            module.exit_json(changed=False)
        else:
            if module.check_mode:
                module.exit_json(changed=False, msg="Instance has to be created")            
            else:
                try:           
                    existing_instance = client.post('/cloud/project/%s/instance' % cloud_id,
    # flavorId=None, // Instance flavor id (type: string)
    # groupId=None, // Start instance in group (type: string)
    # imageId=None, // Instance image id (type: string)
    # monthlyBilling=False, // Active monthly billing (type: boolean)
    # name=None, // Instance name (type: string)
    # networks=None, // Create network interfaces (type: cloud.instance.NetworkParams[])
    # region=None, // Instance region (type: string)
    # sshKeyId=None, // SSH keypair id (type: string)
    # userData=None, // Configuration information or scripts to use upon launch (type: text)
    # volumeId=None, // Specify a volume id to boot from it (type: string)               
                        flavorId=flavor_id,
                        imageId=image_id,
                        monthlyBilling=module.params['monthlyBilling'] == 'True',
                        name=module.params['name'],
                        region=module.params['region'],
                        sshKeyId=sshKey_id                        
                    )
                    changed = True
                    #module.exit_json(changed=True, msg="Volume %s created" % module.params['name'])            
                except APIError as apiError:
                    module.fail_json(changed=False, msg="Failed to call OVH API on creation: {0}".format(apiError))                        
    else:
        if module.params['state'] == 'absent':
            if module.check_mode:
                module.exit_json(changed=False, msg="Key has to be deleted", instance=existing_instance)            
            else:       
                try:
                    client.delete('/cloud/project/%s/instance/%s' % (cloud_id, existing_instance['id']))         
                    module.exit_json(changed=True, msg="Instance %s deleted" % module.params['name'])        
                except APIError as apiError:
                    module.fail_json(changed=False, msg="Failed to call OVH API on delete: {0}".format(apiError))       
        else:
            if existing_instance['imageId'] != image_id or module.params['state'] == 'reinstall':
                if module.check_mode:
                    module.exit_json(changed=False, msg="Instance has to be reinstalled", instance=existing_instance)                            
                else:
                    changed = True
                try:
                    client.post('/cloud/project/%s/instance/%s/reinstall' % (cloud_id, existing_instance['id']), imageId=image_id)                             
                except APIError as apiError:
                    module.fail_json(changed=False, msg="Failed to call OVH API on reinstall: {0}".format(apiError))                           
            if existing_instance['flavorId'] != flavor_id:
                if module.check_mode:
                    module.exit_json(changed=False, msg="Instance has to be upgraded", instance=existing_instance)                            
                else:
                    changed = True
                try:
                    client.post('/cloud/project/%s/instance/%s/resize' % (cloud_id, existing_instance['id']), flavorId=flavor_id)                             
                except APIError as apiError:
                    module.fail_json(changed=False, msg="Failed to call OVH API on resize: {0}".format(apiError))                                    
            if module.params['state'] == 'reboot':                    
                if module.check_mode:
                    module.exit_json(changed=False, msg="Instance has to be reboot", instance=existing_instance)                            
                else:
                    changed = True
                try:
                    client.post('/cloud/project/%s/instance/%s/reboot' % (cloud_id, existing_instance['id']), type='soft')                             
                except APIError as apiError:
                    module.fail_json(changed=False, msg="Failed to call OVH API on reboot: {0}".format(apiError))                                                                                                         
    module.exit_json(changed=changed, msg="Volume %s changed" % module.params['name'], instance=existing_instance)        


    

if __name__ == '__main__':
        main()
