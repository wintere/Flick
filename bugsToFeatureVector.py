import re
import py_stringmatching.tokenizer as pyt
import py_stringmatching.similarity_measure as sm
import string
import pickle

def jaccard(seta, setb):
    seta = set(seta)
    setb = set(setb)
    denom = len(seta.union(setb))
    num = len(seta.intersection(setb))
    return float(num)/denom

expression = re.compile(r'[0-9]+(?:[\.]?[0-9])|[\w]+(?:[\'\-]?[\w])*|')

def tokenize(string):
    return re.findall(expression, string)

#vector generator class
class VectorGenerator():
    def __init__(self):
        #initialize vector functions, stopwords, and available tokenization/set similarity utilities
        self.functions = [self.hardwarePlatformSimilarity, self.OSSimilarity, self.stackTraceClassSoftSim, self.reportedOnDelta, self.technicalTitleSimilarity, self.firstCommentAllWords, self.componentMatch, self.title3GramSimilarity, self.firstCommentSimilarity, self.productMatch, self.versionMatch, self.tfidfKeyText]
        self.stopwords = open('stopwords.txt').read().split('\n')
        self.qGrammer = pyt.qgram_tokenizer.QgramTokenizer(qval=3)
        #monge-elkan defaults to a prefix weighted edit distance
        self.softSetSim = sm.monge_elkan.MongeElkan()
        self.prefixWeightedSim = sm.jaro_winkler.JaroWinkler()
        self.overlap = sm.overlap_coefficient.OverlapCoefficient()
        self.function_names = [func.__name__ for func in self.functions]
        #NOTE: corpora must be specific to the given database for TFIDF to work properly, as different systems have a different vocabulary
        corpora = pickle.load(open('5000_sample_all_words.p', mode='rb'))
        self.tfidf = sm.tfidf.TfIdf(corpora)


    #Assumes a [platform, OS] tuple in the hardware field, which is conventional for Eclipse Bugzilla
    def hardwarePlatformSimilarity(self, bug_a, bug_b):
        return (bug_a['hardware'][0].lower() == bug_b['hardware'][0].lower())

    # Assumes a [platform, OS] tuple in the hardware field, which is conventional for Eclipse Bugzilla
    def OSSimilarity(self, bug_a, bug_b):
        return self.prefixWeightedSim.get_raw_score(bug_a['hardware'][1], bug_b['hardware'][1])

    #The first comment typically explicates the problem, while further comments might be discussion
    def firstCommentSimilarity(self, bug_a, bug_b):
        parsed = []
        for bug in [bug_a, bug_b]:
            tokens = bug['comments'][0]['text'].lower().split()
            parsed.append([word for word in tokens if word not in self.stopwords])
        return jaccard(*parsed)

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
        return  jaccard(*p)

    #3gram jaccard similarity of titles
    def title3GramSimilarity(self, bug_a, bug_b):
        a_title, b_title, = bug_a['title'], bug_b['title']
        p = []
        for t in [a_title, b_title]:
            parsed = self.qGrammer.tokenize(t)
            p.append(parsed)
        return jaccard(*p)

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

    def versionMatch(self, bug_a, bug_b):
        a,b, = bug_a['version'].lower(),bug_b['version'].lower()
        if a == 'unspecified' or b == 'unspecified':
            return -1
        else:
            return self.prefixWeightedSim.get_raw_score(a, b)

    #jaro-winkler set similarity between class level stack trace data
    #flaws: we're missing a lot of stack trace data
    def stackTraceClassSoftSim(self, bug_a, bug_b):
        alist = set([b[0] for b in bug_a['trace_fragments']])
        blist = set([b[0] for b in bug_b['trace_fragments']])
        if alist != [] and blist != []:
            return self.softSetSim.get_raw_score(alist,blist)
        else:
            #indeterminate case (very common)
            return -1

    #absolute difference in time reported between bugs
    def reportedOnDelta(self, bug_a, bug_b):
        d1, d2 = bug_a['reported_on'], bug_b['reported_on']
        return (abs(d1 - d2).days)


    def tfidfKeyText(self, bug_a, bug_b):
        target_fields = ['title', 'hardware', 'component', 'product', 'version']
        sets = []
        for bug in [bug_a, bug_b]:
            tokens = []
            # add information from key fields
            for field in target_fields:
                raw = bug[field]
                if type(raw) is list:
                    tokens.extend([j for i in raw for j in tokenize(i) if j != ''])
                else:
                    t = re.findall(expression, raw.lower())
                    for token in t:
                        if token != '' and token not in self.stopwords:
                            tokens.append(token)
            # plus initial comment info
            if len(bug['comments']) > 0:
                raw = bug['comments'][0]['text'].lower()
                t = re.findall(expression, raw)
                for token in t:
                    if token != '' and token not in self.stopwords:
                        tokens.append(token)
            sets.append(tokens)
        return self.tfidf.get_raw_score(*sets)

    #returns a vector, label tuple
    def getVector(self, bug):
        v = []
        bug_a, bug_b = bug['bug_a'], bug['bug_b']
        for f in self.functions:
            v.append(f(bug_a, bug_b))
        l = 0
        if bug['label'] == 'DUPES':
            l = 1
        return(v, l)

