#!/usr/bin/env python

try:
    import ovh
    import ovh.exceptions
    from ovh.exceptions import APIError
    HAS_OVH = True
except ImportError:
    HAS_OVH = False

from time import sleep


def get_ovh_client(module):
    if module.params['endpoint'] and module.params['application_key'] and module.params['application_secret'] and module.params['consumer_key']:
        return ovh.Client(
            endpoint=module.params['endpoint'],
            application_key= module.params['application_key'],
            application_secret=module.params['application_secret'],
            consumer_key=module.params['consumer_key']
        )        
    else:
        return ovh.Client()        

def get_cloud(ovhclient, module, cloud_name):
    try:
        for acloud_id in ovhclient.get('/cloud/project'):
            cloud_desc = ovhclient.get('/cloud/project/%s' % acloud_id)
            if cloud_name == cloud_desc['description']:
                return cloud_desc
        return None
    except APIError as apiError:
        module.fail_json(changed=False, msg="Failed to call OVH API on get_cloud: {0}".format(apiError))   

def get_cloud_id(ovhclient, module, cloud_name):
    my_cloud = get_cloud(ovhclient, module, cloud_name)
    if my_cloud is None:
        module.fail_json(changed=False, msg="Cloud specified does not exist")
    else:
        return my_cloud['project_id']      
        
def get_flavor_id(ovhclient, module, cloud_id, region, flavor_name):
    try:
        flavor_list = []
        for aflavor in ovhclient.get('/cloud/project/%s/flavor' % cloud_id, region=region):
            if flavor_name == aflavor['name']:
                return aflavor['id']
            flavor_list.append(aflavor['name'])
        module.fail_json(changed=False, msg="Flavor specified does not exist. Flavors available : %s" % ', '.join(flavor_list))
    except APIError as apiError:
        module.fail_json(changed=False, msg="Failed to call OVH API on get_flavor_id: {0}".format(apiError))            

def get_image_id(ovhclient, module, cloud_id, region, image_name):
    try:
        image_list = []
        for animage in ovhclient.get('/cloud/project/%s/image' % cloud_id, region=region):
            if image_name == animage['name']:
                return animage['id']
            image_list.append(animage['name'])
        module.fail_json(changed=False, msg="Image specified does not exist. Images available : %s" % ', '.join(image_list))
    except APIError as apiError:
        module.fail_json(changed=False, msg="Failed to call OVH API on get_image_id: {0}".format(apiError))                

def get_sshkey(ovhclient, module, cloud_id, key_name, sshkey_list = []):
    try:
        for sshkey in ovhclient.get('/cloud/project/%s/sshkey' % cloud_id):
            if key_name == sshkey['name']:
                return sshkey
            sshkey_list.append(sshkey['name'])
        return None
    except APIError as apiError:
        module.fail_json(changed=False, msg="Failed to call OVH API on get_sshkey: {0}".format(apiError))      

def get_sshkey_id(ovhclient, module, cloud_id, key_name):
    sshkey_list = []
    ssh_key = get_sshkey(ovhclient, module, cloud_id, key_name, sshkey_list)
    if ssh_key is None:
        module.fail_json(changed=False, msg="SSH key specified does not exist. SSH keys available : %s" % ', '.join(sshkey_list))
    else:
        return ssh_key['id']

def get_private_network(ovhclient, module, cloud_id, network_name, network_list = []):
    try:        
        for annetwork in ovhclient.get('/cloud/project/%s/network/private' % cloud_id):
            if network_name == annetwork['name']:
                return annetwork
            network_list.append(annetwork['name'])
        return None
    except APIError as apiError:
        module.fail_json(changed=False, msg="Failed to call OVH API on get_private_network: {0}".format(apiError))            

def get_private_network_id(ovhclient, module, cloud_id, network_name):
    network_list = []
    network = get_private_network(ovhclient, module, cloud_id, network_name, network_list)
    if network is None:
        module.fail_json(changed=False, msg="Network specified does not exist. Networks available : %s" % ', '.join(network_list))
    else:
        return network['network']


def get_volume(ovhclient, module, cloud_id, volume_name, region=None, volume_list = []):
    try:        
        for avolume in ovhclient.get('/cloud/project/%s/volume' % cloud_id, region=region):
            if volume_name == avolume['name']:
                return avolume
            volume_list.append(avolume['name'])
        return None
    except APIError as apiError:
        module.fail_json(changed=False, msg="Failed to call OVH API on get_volume: {0}".format(apiError))            

def get_volume_id(ovhclient, module, cloud_id, volume_name, region=None):
    volume_list = []
    volume = get_volume(ovhclient, module, cloud_id, volume_name, region, volume_list)
    if volume is None:
        module.fail_json(changed=False, msg="Volume specified does not exist. volumes available : %s" % ', '.join(volume_list))
    else:
        return volume['id']

def get_instance(ovhclient, module, cloud_id, instance_name, instance_list = []):
    try:        
        for aninstance in ovhclient.get('/cloud/project/%s/instance' % cloud_id):
            if instance_name == aninstance['name']:
                return aninstance
            instance_list.append(aninstance['name'])
        return None
    except APIError as apiError:
        module.fail_json(changed=False, msg="Failed to call OVH API on get_instance: {0}".format(apiError))            

def get_instance_id(ovhclient, module, cloud_id, instance_name):
    instance_list = []
    instance = get_instance(ovhclient, module, cloud_id, instance_name, instance_list)
    if instance is None:
        module.fail_json(changed=False, msg="Instance specified does not exist. Instances available : %s" % ', '.join(instance_list))
    else:
        return instance['id']        



def get_interface(ovhclient, module, cloud_id, instance_id, network_id):
    try:        
        for aninterface in ovhclient.get('/cloud/project/%s/instance/%s/interface' % (cloud_id, instance_id)):
            if network_id == aninterface['networkId']:
                return aninterface
        return None
    except APIError as apiError:
        module.fail_json(changed=False, msg="Failed to call OVH API on get_interface: {0}".format(apiError))            


def get_vrack(ovhclient, module, vrack_name, vrack_list = []):
    try:        
        for avrack in ovhclient.get('/vrack'):
            vrack_info = ovhclient.get('/vrack/%s' % avrack)
            if vrack_name == vrack_info['name']:
                vrack_info['id'] = avrack
                return vrack_info
            vrack_list.append(vrack_info['name'])
        return None
    except APIError as apiError:
        module.fail_json(changed=False, msg="Failed to call OVH API on get_vrack: {0}".format(apiError))   

def get_vrack_id(ovhclient, module, vrack_name):
    vrack_list = []
    vrack_info = get_vrack(ovhclient, module, vrack_name, vrack_list)
    if vrack_info is None:
        module.fail_json(changed=False, msg="Vrack specified does not exist. Vracks available : %s" % ', '.join(vrack_list))
    else:
        return vrack_info['id']          

def create_new_vrack(ovhclient, module, name, description=''):
    try:
        vrack_order = ovhclient.post('/order/vrack/new')
        ovhclient.post('/me/order/%s/payWithRegisteredPaymentMean' % vrack_order['orderId'], paymentMean='fidelityAccount')
        vrack_order_status = 'checking'
        while vrack_order_status in ['checking', 'delivering']:
            sleep(5)
            vrack_order_status = ovhclient.get('/me/order/%s/status' % vrack_order['orderId'])
        if vrack_order_status != 'delivered':
            module.fail_json(changed=False, msg="Order of vrack failed with status %s" % vrack_order_status)            
        for adetail in ovhclient.get('/me/order/%s/details' % vrack_order['orderId']):
            vrack_order_details = ovhclient.get('/me/order/%s/details/%s' % (vrack_order['orderId'], adetail)) 
            ovhclient.put('/vrack/%s' % (vrack_order_details['domain']), description=description, name=name) 
            vrack_info = ovhclient.get('/cloud/vrack/%s' % vrack_order_details['domain'])
            vrack_info['id'] = vrack_order_details['domain']
            return vrack_info
    except APIError as apiError:
        module.fail_json(changed=False, msg="Failed to call OVH API on create_new_vrack: {0}".format(apiError))   

