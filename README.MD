# OVH Modules for Ansible
Few Modules for managing OVH public cloud and OVH DNS.
It is also very usefull to create certificate signed by let's encrypt.

## Modules
* ovh_cloud : Manage OVH Cloud Project
* ovh_cloud_ssh_key : Manage SSH keys saved in the cloud project
* ovh_cloud_network : Manage private networks in the public cloud
* ovh_cloud_instance : Manage instance in the public cloud (Create, remove, upgrade)
* ovh_cloud_volume : Manage volumes
* ovh_vrack : Create vrack that is needed to use private networks
* ovh_dns : Manage OVH DNS. It is the Albin Kerouanton modules (https://github.com/NiR-/ansible-ovh-dns)

## Playbooks
2 playbooks to show how the modules works:
* `infrastructure_create.yml` : create all the infra based on inventory
	** Create cloud project
	** Attach vrack
	** Add SSH Key
	** Create instances
	** Add private network to instances
	** Create DNS
	** Import SSH Keys to be able to connect
	** Configure private network on instances
* `infrastructure_clear.yml` : clear instances based on inventory

## Reusable task
`tasks/create_certificate.yml` is a very usefull task that create signed certificate using Let's encrypt and OVH DNS on ansible runner ==> No need to install openssl or cerbot on your hosts

## Requirements
`ovh` module is needed
To create certificate `pyopenssl` is also needed.