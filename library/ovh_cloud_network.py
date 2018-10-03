#!/usr/bin/env python

ANSIBLE_METADATA = {
    'metadata_version': '1.0',
    'supported_by': 'community',
    'status': ['preview']
        }

DOCUMENTATION = '''
---
module: ovh_cloud_network
short_description: Manage OVH Cloud SSH Keys
description:
    - Add/Delete/Modify Networks in OVH Public Cloud
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
        description: The network name
    cloud_name:
        required: true
        description: The name of the cloud where network has to be created
    state:
        required: false
        default: present
        choices: ['present', 'absent']
        description:
            - Determines whether the network has to be created/modified or deleted
    vlanid:
        required: false
        description:
            - Vland id, between 0 and 4000. 0 value means no vlan. (type: long)
    regions:
        required: false
        default: None
        description:
            - Region where to activate private network. No parameters means all region (type: string[])
    # subnets:
    #     required: false
    #     default: []
    #     description:
    #         - Subnet list whith this format : 
    #             dhcp=False, // Enable DHCP (type: boolean)
    #             end=None, // Last IP for this region (eg: 192.168.1.24) (type: ip)
    #             network=None, // Global network with cidr (eg: 192.168.1.0/24) (type: ipBlock)
    #             noGateway=False, // Set to true if you don't want to set a default gateway IP (type: boolean)
    #             region=None, // Region where this subnet will be created (type: string)
    #             start=None, // First IP for this region (eg: 192.168.1.12) (type: ip)
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

from ansible.module_utils.ovh_utils import HAS_OVH, get_ovh_client, get_cloud_id, get_private_network, APIError, get_instance, get_interface

# For Ansible < 2.1
# Still works on Ansible 2.2.0
from ansible.module_utils.basic import *

# For Ansible >= 2.1
# bug: doesn't work with ansible 2.2.0
#from ansible.module_utils.basic import AnsibleModule
         

def manage_subnets(ovhclient, module, cloud_id, network_id):
    changed = False
    try:
        existing_subnets = ovhclient.get('/cloud/project/%s/network/private/%s/subnet' % (cloud_id, network_id))
    except APIError as apiError:
        module.fail_json(changed=False, msg="Failed to call OVH API on get_subnet: {0}".format(apiError))                                       
    if len(module.params['subnets']) > 0:
        existing_subnets_dict = {}
        for asubnet in existing_subnets:
            for apool in asubnet['ipPools']:
                existing_subnets_dict[apool['region']] = apool
                existing_subnets_dict[apool['region']]['id'] = asubnet['id']
        asked_subnets_dict = {asubnet['region'] : asubnet for asubnet in module.params['subnets']}
        #Suppression des subnets en trop
        for region, subnet in existing_subnets_dict.items():
            if region not in asked_subnets_dict:
                if module.check_mode:
                    module.exit_json(changed=False, msg="Subnet has to be deleted")            
                else:          
                    try:      
                        ovhclient.delete('/cloud/project/%s/network/private/%s/subnet/%s' % (cloud_id, network_id, existing_subnets_dict[asubnet]['id']))
                    except APIError as apiError:
                        module.fail_json(changed=False, msg="Failed to call OVH API on delete: {0}".format(apiError))                               
                    changed = True
        #Mise a jour / creation des subnets
        for region, subnet in asked_subnets_dict.items():
            if region in existing_subnets_dict:
                exist_subnet = existing_subnets_dict[region]
                if subnet['start'] != exist_subnet['start'] or subnet['end'] != exist_subnet['end'] or subnet['dhcp'] != exist_subnet['dhcp'] or subnet['network'] != exist_subnet['network']:
                    if module.check_mode:
                        module.exit_json(changed=False, msg="Subnet has to be changed")            
                    else:          
                        try:      
                            ovhclient.delete('/cloud/project/%s/network/private/%s/subnet/%s' % (cloud_id, network_id, exist_subnet['id']))
                            ovhclient.post('/cloud/project/%s/network/private/%s/subnet' % (cloud_id, network_id), **subnet)
                        except APIError as apiError:
                            module.fail_json(changed=False, msg="Failed to call OVH API on update: {0}".format(apiError))                               
                        changed = True                    
            else:
                if module.check_mode:
                    module.exit_json(changed=False, msg="Subnet has to be created")            
                else:          
                    try:      
                        ovhclient.post('/cloud/project/%s/network/private/%s/subnet' % (cloud_id, network_id), **subnet)
                    except APIError as apiError:
                        module.fail_json(changed=False, msg="Failed to call OVH API on create: {0}".format(apiError))                               
                    changed = True                                    
    return changed
    



def main():
    module = AnsibleModule(
            argument_spec = dict(
                state = dict(default='present', choices=['present', 'absent', 'attached', 'detached']),
                name  = dict(required=True),
                cloud_name = dict(required=True),
                vlanid = dict(required=False, default=0),
                regions   = dict(required=False, default=[], type='list'),
                subnets  = dict(required=False, default=[], type='list'),
                instance  = dict(required=False, default=None),
                instance_ip  = dict(required=False, default=None),
                endpoint = dict(required=False, default=None),                
                application_key = dict(required=False, default=None, no_log=True),
                application_secret = dict(required=False, default=None, no_log=True),
                consumer_key = dict(required=False, default=None, no_log=True),
                ),
            supports_check_mode=True
            )
    changed = False
    if not HAS_OVH:
        module.fail_json(msg='OVH Api wrapper not installed')
    try:
        client = get_ovh_client(module)
    except APIError as apiError:
        module.fail_json(changed=False, msg="Failed to call OVH API: {0}".format(apiError))
    cloud_id = get_cloud_id(client, module, module.params['cloud_name'])
    existing_network = get_private_network(client, module, cloud_id, module.params['name'])
    if existing_network is None:
        if module.params['state'] in ['absent', 'detached']:
            module.exit_json(changed=False)
        elif module.params['state'] in ['present', 'attached']:
            if module.check_mode:
                module.exit_json(changed=False, msg="Network has to be created")            
            else:
                try:
                    existing_network = client.post('/cloud/project/%s/network/private' % cloud_id,
                        name=module.params['name'],
                        regions=module.params['regions'],
                        vlanId=int(module.params['vlanid']),                        
                    )
                    changed=True
                    #module.exit_json(changed=True, msg="Network %s created" % module.params['name'])            
                except APIError as apiError:
                    module.fail_json(changed=False, msg="Failed to call OVH API: {0}".format(apiError))                        
    else:
        if module.params['state'] == 'absent':
            if module.check_mode:
                module.exit_json(changed=False, msg="Network has to be deleted")            
            else:       
                try:
                    client.delete('/cloud/project/%s/network/private/%s' % (cloud_id, existing_network['id']))     
                    changed = True    
                    #module.exit_json(changed=True, msg="Key %s deleted" % module.params['name'])        
                except APIError as apiError:
                    module.fail_json(changed=False, msg="Failed to call OVH API: {0}".format(apiError))       
    
    if module.params['state'] in ['present', 'attached']:
        network_regions = set([aregion['region'] for aregion in existing_network['regions']])
        asked_region = set(module.params['regions'])
        new_region = asked_region.difference(network_regions)
        if len(new_region) > 0:
            if module.check_mode:
                module.exit_json(changed=False, msg="Network has to be changed")            
            else:       
                try:
                    for aregion in new_region:
                        client.post('/cloud/project/%s/network/private/%s/region' % (cloud_id, existing_network['id']), region = aregion)               
                    module.exit_json(changed=True, msg="Network %s changed" % module.params['name'])        
                except APIError as apiError:
                    module.fail_json(changed=False, msg="Failed to call OVH API: {0}".format(apiError))       
    # ovhclient, module, cloud_id, network_id
    if manage_subnets(client, module, cloud_id, existing_network['id']):
        changed = True
    if module.params['state'] in ['detached', 'attached']:
        if module.params['instance'] is None:
            module.fail_json(changed=False, msg="Instance is needed to attach or detach an instance from a network")       
        instance = get_instance(client, module, cloud_id, module.params['instance'])
        if existing_network['id'] in [aninterface['networkId'] for aninterface in instance['ipAddresses']]:
            if module.params['state'] == 'detached':
                if module.check_mode:
                    module.exit_json(changed=False, msg="Network has to be detached")                            
                else:
                    try:
                        changed=True
                        interface = get_interface(client, module, cloud_id, instance['id'], existing_network['id'])
                        client.delete('/cloud/project/%s/instance/%s/interface/%s' % (cloud_id, instance['id'], interface['id']))               
                    except APIError as apiError:
                        module.fail_json(changed=False, msg="Failed to call OVH API: {0}".format(apiError))                               
        else:
            if module.params['state'] == 'attached':
                if module.check_mode:
                    module.exit_json(changed=False, msg="Network has to be attached")                            
                else:
                    try:
                        changed=True
                        client.post('/cloud/project/%s/instance/%s/interface' % (cloud_id, instance['id']), ip = module.params['instance_ip'], networkId = existing_network['id'])               
                    except APIError as apiError:
                        module.fail_json(changed=False, msg="Failed to call OVH API: {0}".format(apiError))                                                   
    module.exit_json(changed=changed, network=existing_network)  




    

if __name__ == '__main__':
        main()
