# -*- coding: utf-8 -*-

# Required for configuration SLL opts in pymongo
import ssl
import numpy
import random
import pymongo
import re
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer

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
client = pymongo.MongoClient()

print('[NOTE] Will select the bugs DATABASE for use')
remote_db = client.cs706


COLLECTION = 'fedora_bugs'

stopwords = open('stopwords.txt').read().split('\n')
expression = re.compile(r'[a-z_]+(?:[\'\-_][a-z_])*')

def tokenize(string):
    return re.findall(expression, string)

print('[NOTE] Will select the %s COLLECTION for use' % COLLECTION)
DB = remote_db[COLLECTION].find()
aggregate_texts = []
target_fields = ['title', 'hardware','component','product']
for bug in DB:
    print(bug.keys())
    tokens = []
    #add information from key fields
    for field in target_fields:
        if field in bug:
            raw = bug[field]
            if type(raw) is list:
                tokens.extend([j for i in raw for j in tokenize(i) if j != ''])
            else:
                t = re.findall(expression, raw.lower())
                for token in t:
                    if token != '' and token not in stopwords and not token.isdigit():
                        tokens.append(token)
    #plus initial comment info
    if len(bug['comments']) > 0:
        raw = bug['comments'][0]['text'].lower()
        t = re.findall(expression, raw)
        for token in t:
            if token != '' and token not in stopwords and not token.isdigit():
                tokens.append(token)
        if len(bug['comments']) > 2:
            raw = bug['comments'][1]['text'].lower()
            t = re.findall(expression, raw)
            for token in t:
                if token != '' and token not in stopwords and not token.isdigit():
                    tokens.append(token)
    aggregate_texts.append(tokens)



pickle.dump(aggregate_texts, open('fedora_sample_all_words', mode='wb'))
# #STEP TWO: TOPIC MODELING

# vectorizer = TfidfVectorizer(analyzer='word', min_df=0.09, max_df=0.93,smooth_idf=True, stop_words='english')
# matrix = vectorizer.fit_transform(a_texts)
# feature_names = vectorizer.get_feature_names()
# vocab = feature_names
#
# model = LatentDirichletAllocation(n_topics=20, evaluate_every=5, max_iter=25)
# model.fit(matrix)
# n_top_words = 30
# #pickle.dump(aggregate_texts, open('50000_sample_all_words.p', mode='wb'))
# topic_lists = []
# for topic_idx, topic in enumerate(model.components_):
#     t_words = {}
#     print("Topic #%d:" % topic_idx)
#     print(" ".join([feature_names[i]
#                     for i in topic.argsort()[:-n_top_words - 1:-1]]))
#     for i in topic.argsort()[:-n_top_words - 1:-1]:
#         word = feature_names[i]
#         t_words[word] = topic[i]
#     topic_lists.append(t_words)
# pickle.dump(topic_lists, open('fedora_topics_15_20', mode='wb'))