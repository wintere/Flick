import re
import py_stringmatching.tokenizer as pyt
import py_stringmatching.similarity_measure as sm

def jaccard(seta, setb):
    seta = set(seta)
    setb = set(setb)
    denom = len(seta.union(setb))
    num = len(seta.intersection(setb))
    return float(num)/denom

#vector generator class
class VectorGenerator():
    def __init__(self):
        #initialize vector functions, stopwords, and available tokenization/set similarity utilities
        self.functions = [self.hardwareSimilarity, self.stackTraceClassSoftSim, self.reportedOnDelta, self.technicalTitleSimilarity, self.componentMatch, self.title3GramSimilarity]
        self.stopwords = open('stopwords.txt').read().split('\n')
        self.qGrammer = pyt.qgram_tokenizer.QgramTokenizer(qval=3)
        self.softSetSim = sm.monge_elkan.MongeElkan()


    #TODO: Accomodate synonyms like macintosh for Mac OS X, return 0.5 for values of ALL?
    def hardwareSimilarity(self, bug_a, bug_b):
        return jaccard(bug_a['hardware'],bug_b['hardware'])

    #word level title similarity
    def technicalTitleSimilarity(self, bug_a, bug_b):
        a_title, b_title, = bug_a['title'],bug_b['title']
        p = []
        for t in [a_title, b_title]:
            t = t.rstrip('.')
            s = t.lower().split(' ')
            #strategy: remove everything that definitely isn't a technical term (ie 'and' 'the')
            parsed = [word for word in s if word not in self.stopwords]
            p.append(parsed)
        return jaccard(*p)

    #3gram jaccard similarity of titles
    def title3GramSimilarity(self, bug_a, bug_b):
        a_title, b_title, = bug_a['title'], bug_b['title']
        p = []
        for t in [a_title, b_title]:
            t = t.rstrip('.')
            parsed = self.qGrammer.tokenize(t)
            p.append(parsed)
        return jaccard(*p)

    #does this trivialize the problem to an extent?
    def componentMatch(self, bug_a, bug_b):
        a,b, = bug_a['component'].lower(),bug_b['component'].lower()
        if a != b:
            return 0
        return 1

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

