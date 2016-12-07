# -*- coding: utf-8 -*-

# Required for configuration SLL opts in pymongo
import ssl
import numpy
import random
import pymongo
import re
import pickle
from sklearn.feature_extraction.text import CountVectorizer

from bugsToFeatureVector import VectorGenerator
from sklearn.decomposition import NMF, LatentDirichletAllocation


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
client = pymongo.MongoClient(connection_string, ssl_cert_reqs=ssl.CERT_NONE)

print('[NOTE] Will select the bugs DATABASE for use')
remote_db = client.cs706


COLLECTION = 'eclipse_random_A'

stopwords = open('stopwords.txt').read().split('\n')
expression = re.compile(r'[0-9]+(?:[\.]?[0-9])|[\w]+(?:[\'\-]?[\w])*|')

def tokenize(string):
    return re.findall(expression, string)

print('[NOTE] Will select the %s COLLECTION for use' % COLLECTION)
DB = remote_db[COLLECTION].find()
aggregate_texts = []
target_fields = ['title', 'hardware','component','product','version']
for bug in DB:
    tokens = []
    #add information from key fields
    for field in target_fields:
        raw = bug[field]
        if type(raw) is list:
            tokens.extend([j for i in raw for j in tokenize(i) if j != ''])
        else:
            t = re.findall(expression, raw.lower())
            for token in t:
                if token != '':
                    tokens.append(token)
    #plus initial comment info
    if len(bug['comments']) > 0:
        raw = bug['comments'][0]['text'].lower()
        t = re.findall(expression, raw)
        for token in t:
            if token != '':
                tokens.append(token)
        # if len(bug['comments']) > 2:
        #     raw = bug['comments'][1]['text'].lower()
        #     t = re.findall(expression, raw)
        #     for token in t:
        #         if token != '' and token not in stopwords:
        #             tokens.append(token)

    aggregate_texts.append(tokens)

# a_texts = [' '.join(tokens) for tokens in aggregate_texts]
# #STEP TWO: TOPIC MODELING
# count_vect = CountVectorizer()
# count_vect.fit_transform(a_texts)
# LDA = LatentDirichletAllocation(learning_method='batch')
# LDA.fit_transform(a_texts)
# print(LDA)