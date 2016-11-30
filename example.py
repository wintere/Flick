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


def reservoir_sample(take, from_this):
    sample = []
    for i, thingie in enumerate(from_this):
        if i < take:
            sample.append(thingie)
        elif i >= take and random.random() < take / float(i + 1):
            replace = random.randint(0, len(sample) - 1)
            sample[replace] = thingie
    return sample


def find_in_pool_by_id(bug_id, pool):
    filtered = filter(lambda b: b['id'] == bug_id, pool)
    if len(filtered) == 1:
        return filtered[0]
    else:
        print('[WARN] Could not find bug matching id=%s' % bug_id)
        return None

print('[CREATE] Azure connection string string')
connection_string = AZURE_FMT % (AZURE_USR,
                                 AZURE_KEY,
                                 AZURE_HST,
                                 AZURE_PRT,
                                 AZURE_OPT)

print('[CREATE] Done! Connection string= "%s"' % connection_string)
print('[CREATE] Pymongo client with azure connection')

# Makes a connection to the MongoDB sitting out in Azure
client = pymongo.MongoClient(connection_string, ssl_cert_reqs=ssl.CERT_NONE)

print('[NOTE] Will select the bugs DATABASE for use')
remote_db = client.bugs

# GET COLLECTION FOR TRAINING
# *******************************************************************************************

COLLECTION = 'eclipse_test_A'

print('[NOTE] Will select the %s COLLECTION for use' % COLLECTION)
DB = remote_db[COLLECTION]

base_pool = list(DB.find({'pool': 'BASE'}))
test_pool = list(DB.find({'pool': 'TEST'}))

print('[NOTE] Retrieved base_pool with %s bugs in it' % len(base_pool))
print('[NOTE] Retrieved test_pool with %s bugs in it' % len(test_pool))

print('[NOTE] In base_pool there are %s duplicates and %s non-duplicates' %
      (len([b for b in base_pool if len(b['dupes']) > 0]),
       len([b for b in base_pool if len(b['dupes']) == 0])))

print('[NOTE] In test_pool there are %s duplicates and %s non-duplicates' %
      (len([b for b in test_pool if len(b['dupes']) > 0]),
       len([b for b in test_pool if len(b['dupes']) == 0])))

# PAIR BUGS
# *******************************************************************************************

dup_pairs = []
non_pairs = []

# for each of the bugs in the test_pool that were duplicates of some bug in base_pool
for bug in [b for b in test_pool if len(b['dupes']) > 0]:
    # iterate the bugs in base_pool that they match
    for match in bug['should_match']:
        # sanity check
        if match in bug['dupes']:
            # add those pairs
            dup_pairs.append((bug, find_in_pool_by_id(match, base_pool), True))

# For each of the bugs in the test_pool
for bug in test_pool:
    # pair them with each bug in the base pool
    for other in base_pool:
        # sanity check
        if other not in bug['dupes']:
            # add this pair
            non_pairs.append((bug, other, False))

print('[NOTE] We created %s pairs of duplicate bugs' % len(dup_pairs))
print('[NOTE] We created %s piars of NOT duplicate bugs' % len(non_pairs))

SAMPLE_SIZE = min(len(dup_pairs), len(non_pairs))

print('[NOTE] We will randomly sample out %s dup pairs and %s non-dup pairs' % (SAMPLE_SIZE, SAMPLE_SIZE))

final_pairs = []
final_pairs.extend(reservoir_sample(SAMPLE_SIZE, dup_pairs))
final_pairs.extend(reservoir_sample(SAMPLE_SIZE, non_pairs))

print('[NOTE] Final sample has %s PAIRS of bugs' % len(final_pairs))
print('[NOTE] Shuffling so that we do not have a deterministic ordering')

random.shuffle(final_pairs)

print('[SUCCESS] final_pairs is ready for use!!')

# EXTRACT FEATURES
# *******************************************************************************************

# todo: something here
# convert the tuples of bug1, bug2, is_dup? into tuples of features to learn from

print('[SUCCESS] feature tuples have been extracted and are ready for use!!')

# DO THE LEARN THING
# *******************************************************************************************

print('[SUCCESS] we learned the thing!!')
