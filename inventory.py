#!/usr/bin/env python
import psycopg2, psycopg2.extras, json
from collections import defaultdict
from pprint import pprint

db =  psycopg2.connect(dbname = '...',
                                        user = '...',
                                        password = '...',
                                        host = '...',
                                        port = 5432,
                                        )

cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


############## Servers in their groups #############
cur.execute(""" SELECT S.primary_name as server_name, R.name as group
                FROM server as S
                LEFT JOIN server_role as SR ON S.id=SR.srv_id
                LEFT JOIN role as R ON SR.role_id=R.id
            """)

inventory = defaultdict(lambda: { 'hosts': [], 'vars': {}} )

rows = cur.fetchall()
ignored_servers = set()
for row in rows:
    if row['group'] == 'ansible_ignored':
        ignored_servers.add(row['server_name'])

for row in rows:
    if row['server_name'] not in ignored_servers:
        inventory[row['group']]['hosts'].append(row['server_name'])



############## Host variables #############
hostvars = defaultdict(dict)
# ansible_vars
cur.execute(""" SELECT S.id as id, S.primary_name as server_name, V.key, V.value
                FROM server as S
                LEFT JOIN ansible_vars as V ON S.id=V.srv_id
            """)

rows = cur.fetchall()
for row in rows:
    hostvars[row['server_name']]['srv_id'] = row['id']
    hostvars[row['server_name']][row['key']] = row['value']
    hostvars[row['server_name']]['network_ether_interfaces'] = []

# ssh port
cur.execute(""" SELECT S.primary_name as server_name, S.ssh_port as ssh_port
                FROM server as S
            """)

rows = cur.fetchall()
for row in rows:
    hostvars[row['server_name']]['ansible_ssh_port'] = row['ssh_port']

# network devices
cur.execute(""" SELECT S.primary_name as server_name, host(I.ip) as ip, I.type, I.device, netmask(I.ip) as mask
                FROM server as S
                LEFT JOIN ip as I ON S.id=I.srv_id
                WHERE type = 'LAN_OVH'
            """)

rows = cur.fetchall()
for row in rows:
    hostvars[row['server_name']]['network_ether_interfaces'].append({
            'device' : row['device'],
            'bootproto': 'static',
            'address': row['ip'],
            'netmask': row['mask']
        })

inventory['_meta'] = { 'hostvars' : hostvars}


# pprint(dict(hostvars))
#pprint(dict(inventory))
print(json.dumps(inventory))

