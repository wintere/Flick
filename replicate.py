# -*- coding: utf-8 -*-

# Required for configuration SLL opts in pymongo
import ssl
import numpy
import random
import pymongo

# Options for azure connection
AZURE_KEY = '4S4139jcfvvpXFDRrTiEC6NmnWxb5J41nrDOns8UOSt2s37xt2s6tinw6zPgj5Ei41nOXB7i3q3DkKKQlQplEA=='
AZURE_USR = 'csci706'
AZURE_HST = 'csci706.documents.azure.com'
AZURE_PRT = '10250'
AZURE_FMT = 'mongodb://%s:%s@%s:%s/?%s'
AZURE_OPT = 'ssl=true'

print('[CREATE] Azure connection string string')
connection_string = AZURE_FMT % (AZURE_USR,
                                 AZURE_KEY,
                                 AZURE_HST,
                                 AZURE_PRT,
                                 AZURE_OPT)

print('[CREATE] Done! Connection string= "%s"' % connection_string)
print('[CREATE] Pymongo client with azure connection')

# Makes a connection to the MongoDB sitting out in Azure
client = pymongo.MongoClient(connection_string, ssl_cert_reqs=ssl.CERT_NONE).cs706
local = pymongo.MongoClient().cs706

migrate = [
    'eclipse_test_A',
    'eclipse_test_B',
    'eclipse_test_C',
    'eclipse_test_D',
    'eclipse_test_E',
    'eclipse_test_F',
    'eclipse_test_G'
]

for db in migrate:
    for b in client[db].find():
        local[db].insert_one(b)

