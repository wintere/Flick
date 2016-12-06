# -*- coding: utf-8 -*-

#  * Inspired by the InfoZilla Tool
#  * <a href='http://groups.csail.mit.edu/pag/pubs/bettenburg-msr-2008.pdf'>
#  * Extracting Structural Information From Bug Reports
#  * </a>
#  * @authors Nicolas Bettenburg, Rahul Premraj, Thomas Zimmermann, Sunghun Kim

# Required for configuration SLL opts in pymongo
import ssl
import re
import sys

# Options for azure connection
AZURE_KEY = '4S4139jcfvvpXFDRrTiEC6NmnWxb5J41nrDOns8UOSt2s37xt2s6tinw6zPgj5Ei41nOXB7i3q3DkKKQlQplEA=='
AZURE_USR = 'csci706'
AZURE_HST = 'csci706.documents.azure.com'
AZURE_PRT = '10250'
AZURE_FMT = 'mongodb://%s:%s@%s:%s/?%s'
AZURE_OPT = 'ssl=true'


def try_refresh_path():
    try:
        import site
        reload(site)
    except Exception:
        pass


def install_and_import(package):
    import importlib
    try:
        importlib.import_module(package)
    except ImportError:
        import pip
        pip.main(['install', '--user', package])
        try_refresh_path()
    finally:
        globals()[package] = importlib.import_module(package)


# Print iterations progress
def print_progress(iteration, total, prefix='', suffix='', decimals=1, bar_length=100):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        bar_length  - Optional  : character length of bar (Int)
    """
    str_format = "{0:." + str(decimals) + "f}"
    percents = str_format.format(100 * (iteration / float(total)))
    filled_length = int(round(bar_length * iteration / float(total)))
    bar = '█' * filled_length + '-' * (bar_length - filled_length)

    sys.stdout.write('\r%s |%s| %s%s %s' % (prefix, bar, percents, '%', suffix)),

    if iteration == total:
        sys.stdout.write('\n')
    sys.stdout.flush()


class StackTraceExtractor:
    def __init__(self):
        self.JAVA_TRACE = r'\s*?at\s+([\w<>\$_]+\.)+([\w<>\$_]+)\s*\((.+?)\.java:?(\d+)?\)'

        # These two are for more 'strict' stack trace finding
        self.JAVA_EXCEPTION = r'\n(([\w<>\$_]++\.?)++[\w<>\$_]*+(Exception|Error){1}(\s|:))'
        self.JAVA_CAUSE = r'(Caused by:).*?(Exception|Error)(.*?)(\s+at.*?\(.*?:\d+\))+'
        self.RE_FLAGS = re.I | re.M | re.S

    def find_stack_traces(self, s):
        stack_traces = []

        for r in re.findall(re.compile(self.JAVA_TRACE, self.RE_FLAGS), s):
            if "Native Method" not in r[2]:
                item = (r[0] + r[1], r[2] + ":" + r[3])
                if item not in stack_traces:
                    stack_traces.append(item)

        return stack_traces

FRAMES_FOUND = 0

# Makes sure we have pymongo ready
print('[ENSURE] That pymongo is present and installed')
install_and_import('pymongo')

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
remote_db = client.cs706  # Creates DB if not exist

print('[NOTE] Will select the eclipse_raw COLLECTION for use')
DB = remote_db.eclipse_bugs # Creates collection if not exist

query = DB.find({'has_trace_fragments': {'$exists': False}})

print('[NOTE] Stack Trace Finder initialized')
stfinder = StackTraceExtractor()

i = 0
TOTAL = query.count() + 1

print_progress(i, TOTAL, prefix='Progress:', suffix='Bugs Processed (%s w/ frames)' % FRAMES_FOUND)

for bug in query:
    i += 1
    found = False

    if 'has_trace_fragments' in bug:
        continue

    updates = {
        '$set': {}
    }

    trace_fragments = []

    for comment in bug['comments']:
        stack_trace = stfinder.find_stack_traces(comment['text'])

        if len(stack_trace) > 0:
            found = True

        for st in stack_trace:
            if st not in trace_fragments:
                trace_fragments.append(st)

    updates['$set']['trace_fragments'] = trace_fragments
    updates['$set']['number_of_trace_fragments'] = len(trace_fragments)
    updates['$set']['has_trace_fragments'] = (len(trace_fragments) > 0)

    DB.update_one({'id': bug["id"]}, updates, upsert=False)

    if found:
        FRAMES_FOUND += 1

    print_progress(i, TOTAL, prefix='Progress:', suffix='Bugs Processed (%s w/ frames)' % FRAMES_FOUND)


