# -*- coding: utf-8 -*-

# Required for configuration SLL opts in pymongo
import ssl
import numpy
import random
import pymongo
from bugsToFeatureVector import VectorGenerator
from sklearn.ensemble import RandomForestClassifier


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
remote_db = client.cs706

# GET COLLECTION FOR TRAINING
# *******************************************************************************************

COLLECTION = 'eclipse_test_C'

print('[NOTE] Will select the %s COLLECTION for use' % COLLECTION)
DB = remote_db[COLLECTION].find()
vg = VectorGenerator()

#create vectors from data
all_vecs = []
for bug_tuple in DB:
    vector = vg.getVector(bug_tuple)
    all_vecs.append(vector)

print(str(len(all_vecs)) + " vectors generated.")

#randomly partition into training and test sets
test, test_y, training, training_y = [],[],[],[]
random.seed(2)
for i in range(len(all_vecs)):
    choice = random.randint(0,3) #1 in 4 bugs go into the test set
    if choice == 0:
        test.append(all_vecs[i][0])
        test_y.append(all_vecs[i][1])
    else: #3 in 4 go into the training set
        training.append(all_vecs[i][0])
        training_y.append(all_vecs[i][1])

print("Training set size: " + str(len(training)) + "\nTesting set size: " + str(len(test)))

#PARAM NOTES: probability is set to true so we can adjust for precision and recall,
duplicateCLF = RandomForestClassifier(n_estimators=15)
#train model on training set
duplicateCLF.fit(training, training_y)

print('[SUCCESS] we learned the thing!!')

#step two: evaluate model
print("Evaluating test set...")

tp, fp, tn, fn = 0,0,0,0
#walk through vector of guesses and count false positives, false natives, true positives, true negatives
guesses = [t for t in duplicateCLF.predict(test)]
v = zip(guesses, test_y)

for guess, label in v:
    if guess == 1:
        if label == 1:
            tp += 1
        else:
            fp += 1
    if guess == 0:
        if label == 0:
            tn += 1
        else:
            fn += 1

precision, recall = float(tp)/(tp + fp), float(tp)/(tp + fn)
print("Test set evauluation completed")
print("Precision: " + str(precision) + "\nRecall: " + str(recall))


