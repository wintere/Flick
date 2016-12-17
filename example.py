# -*- coding: utf-8 -*-

# Required for configuration SLL opts in pymongo
import ssl
import numpy
import random
import pymongo
from bugsToFeatureVector import VectorGenerator
from sklearn.ensemble import RandomForestClassifier
import time
import sys
from multiprocessing import Pool

# Makes a connection to the MongoDB sitting out in Azure
if __name__ == '__main__':
    client = pymongo.MongoClient()

    remote_db = client.cs706

    # GET COLLECTION FOR TRAINING
    # *******************************************************************************************
    if len(sys.argv) != 2:
        print("USAGE: COLLECTION_NAME")
        exit()

    COLLECTION = sys.argv[1]

    print('[NOTE] Will select the %s COLLECTION for use' % COLLECTION)
    DB = remote_db[COLLECTION].find()
    vg = VectorGenerator()

    z = time.time()
    #create vectors from data
    p = Pool(4)
    all_vecs = p.map(vg.getVector,[bug_tuple for bug_tuple in DB])
    print(str(len(all_vecs)) + " vectors generated in " + str(time.time() - z) + " seconds.")

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
    duplicateCLF = RandomForestClassifier(n_estimators=84, max_features=25)
    #train model on training set
    duplicateCLF.fit(training, training_y)

    print('[SUCCESS] we learned the thing!!')

    #step two: evaluate model
    print("Evaluating test set...")

    tp, fp, tn, fn = 0,0,0,0
    #walk through vector of guesses and count false positives, false natives, true positives, true negatives
    guesses = [t for t in duplicateCLF.predict_proba(test)]
    v = zip(guesses, test_y)

    for guess, label in v:
        #ADJUST
        if guess[1] > 0.60:
            o = 1
        else:
            o = 0
        if o == 1 and label == 1:
            tp += 1
        elif o == 0 and label == 1:
            fn += 1
        elif o == 1 and label == 0:
            fp += 1
        else:
            tn += 1

    precision, recall = float(tp)/(tp + fp), float(tp)/(tp + fn)
    print("\nTest set evaluation completed.")
    print("Precision: " + str(precision) + "\nRecall: " + str(recall))

    #Added Exploratory Feature Rankings: These Approximate How Much Each Feature Contributes To the Model
    feature_name_to_weight = zip( duplicateCLF.feature_importances_, vg.function_names)
    print("\nFeature Rankings in Classification")
    i = 1
    for weight, feature in sorted(feature_name_to_weight, reverse=True):
        print(str(i) + '. ' + feature + ': ' + str(weight))
        i += 1
