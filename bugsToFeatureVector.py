import re
import py_stringmatching.tokenizer as pyt
import py_stringmatching.similarity_measure as sm
import string
import pickle
from datetime import timedelta
import math
import scipy.spatial.distance

expression = re.compile(r'[0-9]+(?:[\.]?[0-9])|[A-z_]+(?:[\'\-_]?[A-z_])*')

#vector generator class
class VectorGenerator():
    def __init__(self):
        #initialize vector functions, stopwords, and available tokenization/set similarity utilities
        self.functions = [self.stackTraceFirstClass,self.stackTraceClassSoftSim, self.hardwarePlatformSimilarity, self.OSSimilarity,  self.reportedOnDelta, self.technicalTitleSimilarity, self.firstCommentAllWords, self.componentMatch, self.title3GramSimilarity, self.firstCommentSimilarity, self.productMatch, self.versionMatch, self.tfidfKeyText, self.importanceDelta, self.titleTFIDF, self.topicModelDistance, self.topicModelEuclidean, self.top50Distance, self.stackTraceLengthDelta, self.stackTraceLinesSoftSim]
        self.stopwords = open('stopwords.txt').read().split('\n')
        self.qGrammer = pyt.qgram_tokenizer.QgramTokenizer(qval=3)
        #monge-elkan defaults to a prefix weighted edit distance
        self.softSetSim = sm.monge_elkan.MongeElkan()
        self.prefixWeightedSim = sm.jaro_winkler.JaroWinkler()
        self.overlap = sm.overlap_coefficient.OverlapCoefficient()
        self.function_names = [func.__name__ for func in self.functions]
        #NOTE: corpora must be specific to the given database for TFIDF to work properly, as different systems have a different vocabulary
        corpora = pickle.load(open('50000_sample_all_words.p', 'rb'))
        self.tfidf = sm.tfidf.TfIdf(corpora)
        self.needleman = sm.jaro.Jaro()
        self.topicModelSource = pickle.load(open('topic_lists_20_40', mode='rb'))
        self.top50Words = pickle.load(open('top50words',mode='rb'))

        for i in range(len(self.topicModelSource)):
            self.function_names.append("topic" + (str(i)))

        for word in self.top50Words:
            self.function_names.append("wc_delta_" + word)

    def jaccard(self,seta, setb):
        seta = set(seta)
        setb = set(setb)
        denom = len(seta.union(setb))
        num = len(seta.intersection(setb))
        if denom == 0:
            return -1
        return float(num) / denom



    def tokenize(self, string):
        return re.findall(expression, string)
    #Assumes a [platform, OS] tuple in the hardware field, which is conventional for Eclipse Bugzilla
    def hardwarePlatformSimilarity(self, bug_a, bug_b):
        return (bug_a['hardware'][0].lower() == bug_b['hardware'][0].lower())

    def topicModelEuclidean(self, bug_a, bug_b):
        bug_a_vec = bug_a['dimensions']
        bug_b_vec = bug_b['dimensions']
        d = scipy.spatial.distance.sqeuclidean(bug_a_vec, bug_b_vec)
        return d

    # Assumes a [platform, OS] tuple in the hardware field, which is conventional for Eclipse Bugzilla
    def OSSimilarity(self, bug_a, bug_b):
        if bug_a['hardware'][1] == 'all' or bug_b['hardware'][1] == 'all':
            return 1
        else:
            return (bug_a['hardware'][1] == bug_b['hardware'][1])


    #The first comment typically explicates the problem, while further comments might be discussion
    def firstCommentSimilarity(self, bug_a, bug_b):
        parsed = []
        for bug in [bug_a, bug_b]:
            tokens = bug['comments'][0]['text'].lower().split()
            parsed.append([word for word in tokens if word not in self.stopwords])
        return self.jaccard(*parsed)

    def firstCommentAllWords(self, bug_a, bug_b):
        parsed = []
        for bug in [bug_a, bug_b]:
            raw = re.sub('\W', ' ', bug['comments'][0]['text'])
            tokens = raw.lower().split()
            tokens = [word for word in tokens if word not in self.stopwords]
            parsed.append(tokens)
        return self.overlap.get_raw_score(*parsed)


    #word level title similarity
    def technicalTitleSimilarity(self, bug_a, bug_b):
        a_title, b_title, = bug_a['title'],bug_b['title']
        p = []
        for t in [a_title, b_title]:
            s = t.lower().split(' ')
            #strategy: remove everything that definitely isn't a technical term (ie 'and' 'the')
            parsed = [word for word in s if word not in self.stopwords]
            p.append(parsed)
        return  self.jaccard(*p)

    def titleTFIDF(self, bug_a, bug_b):
        a_title, b_title, = bug_a['title'],bug_b['title']
        p = []
        for t in [a_title, b_title]:
            s = re.findall(expression, t)
            #strategy: remove everything that definitely isn't a technical term (ie 'and' 'the')
            parsed = [word for word in s if word not in self.stopwords]
            p.append(parsed)
        return  self.tfidf.get_raw_score(*p)



    #3gram jaccard similarity of titles
    def title3GramSimilarity(self, bug_a, bug_b):
        a_title, b_title, = bug_a['title'], bug_b['title']
        p = []
        for t in [a_title, b_title]:
            parsed = self.qGrammer.tokenize(t)
            p.append(parsed)
        return self.jaccard(*p)

    #does this trivialize the problem to an extent?
    def componentMatch(self, bug_a, bug_b):
        a,b, = bug_a['component'].lower(),bug_b['component'].lower()
        if a != b:
            return 0
        return 1

    def productMatch(self, bug_a, bug_b):
        a,b, = bug_a['product'].lower(),bug_b['product'].lower()
        if a != b:
            return 0
        return 1

    def topicModelDistance(self, bug_a, bug_b):
        bug_a_vec = bug_a['dimensions']
        bug_b_vec = bug_b['dimensions']
        d = scipy.spatial.distance.cosine(bug_a_vec, bug_b_vec)
        return d




    def versionMatch(self, bug_a, bug_b):
        a,b, = bug_a['version'].lower(),bug_b['version'].lower()
        if a == 'unspecified' or b == 'unspecified':
            return -1
        else:
            return self.prefixWeightedSim.get_raw_score(a, b)

    #jaro-winkler set similarity between class level stack trace data
    #flaws: we're missing a lot of stack trace data
    def stackTraceClassSoftSim(self, bug_a, bug_b):
        alist = set([b[0] for b in bug_a['trace_fragments'][:5]])
        blist = set([b[0] for b in bug_b['trace_fragments'][:5]])

        if alist != [] and blist != []:
            return self.overlap.get_raw_score(alist,blist)
        else:
            #indeterminate case (very common)
            return -1

    # jaro-winkler set similarity between class level stack trace data
    # flaws: we're missing a lot of stack trace data
    def stackTraceLinesSoftSim(self, bug_a, bug_b):
        alist = set([b[1] for b in bug_a['trace_fragments'][:10]])
        blist = set([b[1] for b in bug_b['trace_fragments'][:10]])
        if alist != [] and blist != []:
            return self.softSetSim.get_raw_score(alist, blist)
        else:
            # indeterminate case (very common)
            return -1

    def stackTraceFirstClass(self, bug_a, bug_b):
        alist = set([b[0] for b in bug_a['trace_fragments'][:3]])
        blist = set([b[0] for b in bug_b['trace_fragments'][:3]])
        if alist != [] and blist != []:
            return self.overlap.get_raw_score(alist, blist)
        else:
            # indeterminate case (very common)
            return -1

    def stackTraceFirstOnly(self, bug_a, bug_b):
        alist = ([b[0] for b in bug_a['trace_fragments'][:2]])
        blist = ([b[0] for b in bug_b['trace_fragments'][:2]])
        if alist != [] and blist != []:
            a = alist[0]
            b = blist[0]
            return (a == b)
        else:
            return -1


    #absolute difference in time reported between bugs
    def reportedOnDelta(self, bug_a, bug_b):
        d1, d2 = bug_a['reported_on'], bug_b['reported_on']
        return (abs(d1 - d2).days)

    def top50Distance(self, bug_a, bug_b):
        bug_a_vec = bug_a['top_50']
        bug_b_vec = bug_b['top_50']
        d = scipy.spatial.distance.cosine(bug_a_vec, bug_b_vec)
        return d


    def stackTraceLengthDelta(self, bug_a, bug_b):
        a = len(bug_a['trace_fragments'])
        b = len(bug_b['trace_fragments'])
        if a == 0 or b == 0:
            return -1
        else:
            return float(abs(a - b))/(a + b)
    #difference in perceived bug priority
    def importanceDelta(self, bug_a, bug_b):
        d1, d2 = bug_a['importance'], bug_b['importance']
        return abs(int(d1[-1]) - int(d2[-1]))

    # tfidf over key text fields
    def wordSimKeyText(self, bug_a, bug_b):
        return self.jaccard(bug_a['key_text'], bug_b['key_text'])

    #tfidf over key text fields
    def tfidfKeyText(self, bug_a, bug_b):
        return self.tfidf.get_sim_score(bug_a['key_text'], bug_b['key_text'])

    #returns a vector, label tuple
    def getVector(self, bug):
        v = []
        bug_a, bug_b = bug['bug_a'], bug['bug_b']
        thresh = max(bug_a['reported_on'],bug_b['reported_on'])
        for b in [bug_a, bug_b]:
            tokens = []
            b['top_50'] = [0.00001] * len(self.top50Words)
            for field in ['title','component','hardware','product','version']:
                raw = b[field]
                if type(raw) is list:
                    tokens.extend([j for i in raw for j in self.tokenize(i) if j != ''])
                else:
                    t = re.findall(expression, raw.lower())
                    for token in t:
                        if token != '' and token not in self.stopwords:
                            tokens.append(token)
                            # plus initial comment info
                for comment in b['comments']:
                    if (comment['date'] <= (thresh + timedelta(minutes=15))):
                        raw = comment['text'].lower()
                        t = re.findall(expression, raw)
                        for token in t:
                            if token != '' and token not in self.stopwords:
                                tokens.append(token)
            b['key_text'] = tokens
            b['dimensions'] = []
            #add topic model dimensions
            for topic in self.topicModelSource:
                dimension_sum = 0
                for word in b['key_text']:
                    if word in self.top50Words:
                        b['top_50'][self.top50Words.index(word)] += 1
                    if word in topic:
                        dimension_sum += topic[word]
                if dimension_sum > 0:
                    dimension_sum = math.log(dimension_sum)
                b['dimensions'].append(dimension_sum)

        for f in self.functions:
            v.append(f(bug_a, bug_b))

        #all topic model distances
        for i in range(len(self.topicModelSource)):
            d = abs(bug_a['dimensions'][i] - bug_b['dimensions'][i])
            v.append(d)

        for i in range(len(self.top50Words)):
            d = abs(bug_a['top_50'][i] - bug_b['top_50'][i])
            v.append(d)

        l = 0
        if bug['label'] == 'DUPES':
            l = 1
        return(v, l)


