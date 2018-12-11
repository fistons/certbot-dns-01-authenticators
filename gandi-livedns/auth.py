#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import pprint
import time

import requests
from config import *

pp = pprint.PrettyPrinter(indent=4)

certbot_domain = os.environ.get("CERTBOT_DOMAIN")
try:
    certbot_domain
except NameError:
    print("CERTBOT_DOMAIN environment variable is missing, exiting")
    exit(1)

certbot_validation = os.environ.get("CERTBOT_VALIDATION")
try:
    certbot_validation
except NameError:
    print("CERTBOT_VALIDATION environment variable is missing, exiting")
    exit(1)

if livedns_sharing_id == None:
    sharing_param = ""
else:
    sharing_param = "?sharing_id=" + livedns_sharing_id

headers = {
    'X-Api-Key': livedns_apikey,
}

response = requests.get(livedns_api + "domains" + sharing_param, headers=headers)

if response.ok:
    domains = response.json()
else:
    response.raise_for_status()
    exit(1)

domain_index = next((index for (index, d) in enumerate(domains) if d["fqdn"] == certbot_domain), None)

if domain_index is None:
    # domain not found
    print("The requested domain " + certbot_domain + " was not found in this gandi account")
    exit(1)

domain_records_href = domains[domain_index]["domain_records_href"]

response = requests.get(domain_records_href + "/_acme-challenge" + sharing_param, headers=headers)

if not response.ok:
    print("Failed to look for existing _acme-challenge record")
    response.raise_for_status()
    exit(1)

certbot_validation_array = [certbot_validation]
for r in response.json():
    certbot_validation_array.extend(r["rrset_values"])

new_record = {
    "rrset_name": "_acme-challenge",
    "rrset_type": "TXT",
    "rrset_ttl": 300,
    "rrset_values": certbot_validation_array
}

response = requests.post(domain_records_href + sharing_param, headers=headers, json=new_record)
if response.ok:
    print("all good, entry created")
    # Let's wait 10 seconds, just in case
    time.sleep(10)
elif response.status_code == 409:
    requests.delete(domain_records_href + "/_acme-challenge/TXT" + sharing_param, headers=headers)
    response = requests.post(domain_records_href + sharing_param, headers=headers, json=new_record)
    if not response.ok:
        print("something went wrong")
        pp.pprint(response.content)
        response.raise_for_status()
        exit(1)
    else:
        print("all good, entry created (after a retry)")
        # Let's wait 10 seconds, just in case
        time.sleep(10)
else:
    print("something went wrong")
    pp.pprint(response.content)
    response.raise_for_status()
    exit(1)
