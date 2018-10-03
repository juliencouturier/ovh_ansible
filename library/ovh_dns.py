#!/usr/bin/python
# -*- coding: utf-8 -*-

# ovh_dns, an Ansible module for managing OVH DNS records
# Copyright (C) 2014, Carlos Izquierdo <gheesh@gheesh.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA

DOCUMENTATION = '''
---
module: ovh_dns
author: Albin Kerouanton @NiR-
short_description: Manage OVH DNS records
description:
    - Manage OVH (French European hosting provider) DNS records
version_added: "2.3"
notes:
    - Uses the python OVH Api U(https://github.com/ovh/python-ovh).
      You have to create an application (a key and secret) with a consummer
      key as described into U(https://eu.api.ovh.com/g934.first_step_with_api)
requirements: [ "ovh" ]
options:
    domain:
        required: true
        description:
            - Name of the domain zone
    name:
        required: true
        description:
            - >
              Name of the DNS record. It has to be relative to your domain.
              Example: for a record "db1.clusterX.mydomain.com", you would use "db1.clusterX"
              as name parameter for domain "mydomain.com".
    value:
        required: true
        description:
            - Value of the DNS record (i.e. what it points to).
    type:
        default: A
        choices: ['A', 'AAAA', 'CNAME', 'DKIM', 'LOC', 'MX', 'NAPTR', 'NS', 'PTR', 'SPF', 'SRV', 'SSHFP', 'TXT']
        description:
            - Type of DNS record (A, AAAA, PTR, CNAME, etc.)
    ttl:
        default: 0
        description:
            - Time to live of the DNS record. It's not mandatory for deleting records, but you shall use it otherwise
              (0 is allowed).
    state:
        default: present
        choices: ['present', 'absent']
        description:
            - Determines wether the record is to be created/modified or deleted
    endpoint:
        required: true
        description:
            - The endpoint to use ( for instance ovh-eu)
    application_key:
        required: true
        description:
            - The applicationKey to use
    application_secret:
        required: true
        description:
            - The application secret to use
    consumer_key:
        required: true
        description:
            - The consumer key to use
'''

EXAMPLES = '''
# Create a A record "db1.clusterX.mydomain.com" pointing to "10.10.10.10" with a ttl of 3600s.
- ovh_dns:
    state: present
    domain: mydomain.com
    name: db1.clusterX
    value: 10.10.10.10
    ttl: 3600
    endpoint: ovh-eu
    application_key: yourkey
    application_secret: yoursecret
    consumer_key: yourconsumerkey

# Create a CNAME record
- ovh_dns:
    state: present
    domain: mydomain.com
    name: dbprod
    type: CNAME
    value: db1
    ttl: 3600
    endpoint: ovh-eu
    application_key: yourkey
    application_secret: yoursecret
    consumer_key: yourconsumerkey

# Delete an existing record, must specify all parameters
- ovh_dns:
    state: absent
    domain: mydomain.com
    name: dbprod
    type: CNAME
    value: db1
    endpoint: ovh-eu
    application_key: yourkey
    application_secret: yoursecret
    consumer_key: yourconsumerkey
'''

RETURN='''
'''

ANSIBLE_METADATA = {'status': ['preview'],
                    'supported_by': 'community',
                    'version': '1.0'}

import os
import sys

try:
    import ovh
    from ovh.exceptions import APIError
    HAS_OVH=True
except ImportError:
    HAS_OVH=False

def get_ovh_client(module):
    endpoint = module.params.get('endpoint')
    application_key = module.params.get('application_key')
    application_secret = module.params.get('application_secret')
    consumer_key = module.params.get('consumer_key')

    return ovh.Client(
        endpoint=endpoint,
        application_key=application_key,
        application_secret=application_secret,
        consumer_key=consumer_key
    )


def get_domain_records(client, domain):
    """Obtain all records for a specific domain"""
    records = {}

    # List all ids and then get info for each one
    record_ids = client.get('/domain/zone/{0}/record'.format(domain))

    for record_id in record_ids:
        info = client.get('/domain/zone/{0}/record/{1}'.format(domain, record_id))
        add_record(records, info)

    return records

def add_record(records, info):
    fieldtype = info['fieldType']
    subdomain = info['subDomain']
    targetval = info['target']

    if fieldtype not in records:
        records[fieldtype] = dict()
    if subdomain not in records[fieldtype]:
        records[fieldtype][subdomain] = dict()

    records[fieldtype][subdomain][targetval] = info

def find_record(records, name, fieldtype, targetval):
    if fieldtype not in records:
        return False
    if name not in records[fieldtype]:
        return False
    if targetval not in records[fieldtype][name]:
        return False

    return records[fieldtype][name][targetval]

def ensure_record_present(module, records, client):
    domain    = module.params.get('domain')
    name      = module.params.get('name')
    fieldtype = module.params.get('type')
    targetval = module.params.get('value')
    ttl       = int(module.params.get('ttl'))
    record    = find_record(records, name, fieldtype, targetval)

    # Does the record exist already?
    if record:
        # The record is already as requested, no need to change anything
        if ttl == record['ttl']:
            module.exit_json(changed=False)

        if module.check_mode:
            module.exit_json(changed=True, diff=dict(ttl=ttl))

        try:
            # find_record is based on record name, field type and target value
            # there's only ttl property left to be updated
            client.put('/domain/zone/{0}/record/{1}'.format(domain, record['id']), ttl=ttl)
        except APIError as error:
            module.fail_json(
                msg='Unable to call OVH api for updating the record "{0} {1} {2}" with ttl {3}. '
                'Error returned by OVH api is: "{4}".'.format(name, fieldtype, targetval, ttl, error)
            )

        refresh_domain(module, client, domain)
        module.exit_json(changed=True)

    if module.check_mode:
        module.exit_json(changed=True, diff=dict(name=name, type=fieldtype, value=targetval, ttl=ttl))

    try:
        # Add the record
        client.post('/domain/zone/{0}/record'.format(domain),
                    fieldType=fieldtype,
                    subDomain=name,
                    target=targetval,
                    ttl=ttl)
    except APIError as error:
        module.fail_json(msg='Unable to call OVH api for adding the record "{0} {1} {2}". '
            'Error returned by OVH api is: "{3}".'.format(name, fieldtype, targetval, error)
        )

    refresh_domain(module, client, domain)
    module.exit_json(changed=True)

def refresh_domain(module, client, domain):
    try:
        client.post('/domain/zone/{0}/refresh'.format(domain))
    except APIError as error:
        module.fail_json(
            msg='Unable to call OVH api to refresh domain "{0}". '
            'Error returned by OVH api is: "{1}"'.format(domain, error)
        )

def ensure_record_absent(module, records, client):
    domain    = module.params.get('domain')
    name      = module.params.get('name')
    fieldtype = module.params.get('type')
    targetval = module.params.get('value')
    record    = find_record(records, name, fieldtype, targetval)

    if not record:
        module.exit_json(changed=False)

    if module.check_mode:
        module.exit_json(changed=True)

    try:
        # Remove the record
        client.delete('/domain/zone/{0}/record/{1}'.format(domain, record['id']))
    except APIError as error:
        module.fail_json(
            msg='Unable to call OVH api for deleting the record "{0}" for "{1}"". '
            'Error returned by OVH api is: "{2}".'.format(name, domain, error)
        )

    refresh_domain(module, client, domain)
    module.exit_json(changed=True)

def main():
    module = AnsibleModule(
        argument_spec = dict(
            domain = dict(required=True),
            name = dict(required=True),
            value = dict(required=True),
            type = dict(default='A', choices=['A', 'AAAA', 'CNAME', 'DKIM', 'LOC', 'MX', 'NAPTR', 'NS', 'PTR', 'SPF', 'SRV', 'SSHFP', 'TXT']),
            ttl = dict(default='0'),
            state = dict(default='present', choices=['present', 'absent']),
            endpoint = dict(required=True),
            application_key = dict(required=True, no_log=True),
            application_secret = dict(required=True, no_log=True),
            consumer_key = dict(required=True, no_log=True),
        ),
        supports_check_mode=True
    )

    if not HAS_OVH:
        module.fail_json(msg='ovh python module is required to run this module.')

    # Get parameters
    domain = module.params.get('domain')
    name = module.params.get('name')
    state  = module.params.get('state')

    client = get_ovh_client(module)

    try:
        # Check that the domain exists
        domains = client.get('/domain/zone')
    except APIError as error:
        module.fail_json(
            msg='Unable to call OVH api for getting the list of domains. '
            'Check application key, secret, consumer key & parameters. '
            'Error returned by OVH api is: "{0}".'.format(error)
        )

    if not domain in domains:
        module.fail_json(msg='Domain {0} does not exist'.format(domain))

    try:
        # Obtain all domain records to check status against what is demanded
        records = get_domain_records(client, domain)
    except APIError as error:
        module.fail_json(
            msg='Unable to call OVH api for getting the list of records for "{0}". '
            'Error returned by OVH api is: "{1}".'.format(domain, error)
        )

    if state == 'absent':
        ensure_record_absent(module, records, client)
    elif state == 'present':
        ensure_record_present(module, records, client)

    # We should never reach here
    module.fail_json(msg='Internal ovh_dns module error')


# import module snippets
from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
