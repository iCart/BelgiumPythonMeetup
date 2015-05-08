#! /usr/bin/env python
# coding=utf-8
from __future__ import unicode_literals, print_function, division
from ansible.inventory import Inventory
from ansible.runner import Runner
from psycopg2 import connect
import argparse

parser = argparse.ArgumentParser(description='Fetch dns config from servers and feed them in the database')
parser.add_argument('-p', '--pattern', default='*', help='limit selected hosts to an additional pattern')
parser.add_argument('-f', '--forks', type=int, default=200, help='specify number of parallel processes to use')

args = parser.parse_args()

FORKS = args.forks
COMMAND = 'grep "^nameserver" /etc/resolv.conf | cut -d" " -f2'
PATTERN = args.pattern

inventory = Inventory('../inventory.py')
runner = Runner(forks=FORKS, pattern=PATTERN, inventory=inventory, module_name='shell', module_args=COMMAND)
results = runner.run()

if not results['dark'] and not results['contacted']:
    print('[X] No servers matched pattern, exiting')
    exit(1)

if results['dark']:
    print('[X] Some servers were not contacted:')
    for server, why in results['dark'].items():
        print('\t%s: %s' % (server, why['msg']))
    print('\n\n\n')

if not results['contacted']:
    print('[X] All servers failed, exiting')
    exit(1)

pg = connect('host=127.0.0.1 user=admin password=... dbname=...')
pg.autocommit = True
with pg.cursor() as cursor:
    print('[✓] Contacted %s servers' % (len(results['contacted'])))

    for server, details in results['contacted'].items():
        nameservers = details['stdout'].split('\n')
        server_id = inventory.get_host(server).get_variables()['srv_id']

        print('\t[✓] Cleaning up for server %s (%s)' % (server, server_id))
        cursor.execute('DELETE FROM nameservers WHERE srv_id = %s', server_id)
        
        print('\t[✓] Inserting %s (%s):' % (server, server_id))
        for nameserver in nameservers:
            cursor.execute('INSERT INTO nameservers (srv_id, ip) VALUES (%s, %s)', (server_id, nameserver))
            print('\t\t[✓] Inserted %s ' % nameserver)
        print('\t\t[✓] Done inserting')

exit(0)
