#!/usr/bin/env python

ANSIBLE_METADATA = {
    'metadata_version': '1.0',
    'supported_by': 'community',
    'status': ['preview']
        }

DOCUMENTATION = '''
---
module: ovh_volume
short_description: Manage OVH Cloud Volumes
description:
    - Add/Delete/Modify Volumes in OVH Public Cloud
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
        description: The name of volume
    cloud_name:
        required: true
        description: The name of the cloud where volume has to be created
    state:
        required: false
        default: present
        choices: ['present', 'absent', 'attached', 'detached', 'snapshot']
        description:
            - Determines whether the volume has to be created, modified, deleted, attached or detached
    size:
        required: true
        description:
            - Size of the volume
    region:
        required: true
        description:
            - The region to create volume
    type:
        required: false
        default: 'classic'        
        description:
            - Volume type : "classic" or "high-speed"   
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

from ansible.module_utils.ovh_utils import HAS_OVH, get_ovh_client, get_cloud_id, get_volume, APIError, get_instance_id

# For Ansible < 2.1
# Still works on Ansible 2.2.0
from ansible.module_utils.basic import *

# For Ansible >= 2.1
# bug: doesn't work with ansible 2.2.0
# from ansible.module_utils.basic import AnsibleModule

def main():
    module = AnsibleModule(
            argument_spec=dict(
                state=dict(default='present', choices=['present', 'absent', 'attached', 'detached']),
                name=dict(required=True),
                cloud_name=dict(required=True),
                size=dict(required=False),
                region=dict(required=False),
                type=dict(required=False, default='classic'),
                instance_name=dict(required=False, default='None'),
                endpoint=dict(required=False, default='None'),
                application_key=dict(required=False, default='None', no_log=True),
                application_secret=dict(required=False, default='None', no_log=True),
                consumer_key=dict(required=False, default='None', no_log=True),
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
    existing_volume = get_volume(client, module, cloud_id, module.params['name'])
    changed = False
    if existing_volume is None:
        if module.params['state'] == 'absent':
            module.exit_json(changed=False)
        else:
            if module.check_mode:
                module.exit_json(changed=False, msg="Volume has to be created")            
            else:
                if not (module.params['size'] and module.params['region']):
                    module.fail_json(changed=False, msg="size and region are needed to create a volume")               
                try:
                    existing_volume = client.post('/cloud/project/%s/volume' % cloud_id,
    # description=None, // Volume description (type: string)
    # imageId=None, // Id of image to create a bootable volume (type: string)
    # name=None, // Volume name (type: string)
    # region=None, // Volume region (type: string)
    # size=None, // Volume size (in GiB) (type: long)
    # snapshotId=None, // Source snapshot id (type: string)
    # type=None, // Volume type (type: cloud.volume.VolumeTypeEnum)                    
                        name=module.params['name'],
                        size=module.params['size'],
                        type=module.params['type'],
                        region=module.params['region'],
                    )
                    changed = True
                    #module.exit_json(changed=True, msg="Volume %s created" % module.params['name'])            
                except APIError as apiError:
                    module.fail_json(changed=False, msg="Failed to call OVH API on creation: {0}".format(apiError))                        
    else:
        if module.params['state'] == 'absent':
            if module.check_mode:
                module.exit_json(changed=False, msg="Key has to be deleted")            
            else:       
                try:
                    client.delete('/cloud/project/%s/volume/%s' % (cloud_id, existing_volume['id']))         
                    module.exit_json(changed=True, msg="Volume %s deleted" % module.params['name'])        
                except APIError as apiError:
                    module.fail_json(changed=False, msg="Failed to call OVH API on delete: {0}".format(apiError))       
        else:
            if existing_volume['size'] != module.params['size']:
                if module.check_mode:
                    module.exit_json(changed=False, msg="Volume has to be changed")                            
                else:
                    changed = True
                try:
                    client.post('/cloud/project/%s/volume/%s/upsize' % (cloud_id, existing_volume['id']), size=module.params['size'])                             
                except APIError as apiError:
                    module.fail_json(changed=False, msg="Failed to call OVH API on change: {0}".format(apiError))                           
    if module.params['state'] in ['attached', 'detached']:
        if not module.params['instance_name']:
            module.fail_json(changed=False, msg="instance_name is needed to attach or detach a volume")                       
        instance_id = get_instance_id(client, module, cloud_id, module.params['instance_name'])
        if instance_id in existing_volume['attachedTo']:
            if module.params['state'] == 'detached':
                if module.check_mode:
                    module.exit_json(changed=False, msg="Volume has to be detached")                            
                try:
                    changed = True
                    client.post('/cloud/project/%s/volume/%s/detach' % (cloud_id, existing_volume['id']), instanceId=instance_id)                             
                except APIError as apiError:
                    module.fail_json(changed=False, msg="Failed to call OVH API on detach: {0}".format(apiError))                                               
        elif module.params['state'] == 'attached':
            try:
                if module.check_mode:
                    module.exit_json(changed=False, msg="Volume has to be attached")                                            
                changed = True
                client.post('/cloud/project/%s/volume/%s/attach' % (cloud_id, existing_volume['id']), instanceId=instance_id)                             
            except APIError as apiError:
                module.fail_json(changed=False, msg="Failed to call OVH API on attach: {0}".format(apiError))                                                           
    module.exit_json(changed=changed, msg="Volume %s changed" % module.params['name'])        


    

if __name__ == '__main__':
        main()
