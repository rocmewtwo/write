import json
import os
import os.path
from collections import defaultdict
import sqlite3
import word2vec

JSON, NAME = range(2)

DBFILE = 'writebest.db'

BNC = 'bnc'
CITE = 'citeseer'
PHD = 'phd'
PHD_NF = 'PHD_NF'
#CITE = 'cite_trans'

corpus = [
['diff/overuse.json', PHD],
['diff/akl.phd.json', PHD_NF],
['diff/akl.bnc.json', BNC],
['diff/akl.citeseer.json', CITE],
#['patterns_with_zh_ja.json', CITE],
]

word2vec_model = {'bnc':'bnc.bin', 'citeseer':'citeseer.bin', 'phd':'phd.bin', 'PHD_NF':'phd.bin'}
model = ''

corpNames = [(BNC,"general"), (CITE,"academic"), (PHD,"overuse"), (PHD_NF,"learner")]
nameToCorp = dict([i[::-1] for i in corpNames])
corps = zip(*corpNames)[0]

def createDB():
  con = sqlite3.connect(DBFILE)
  cur = con.cursor()

  for corp in corpus:
    cur.execute("DROP TABLE if exists %s;"%corp[NAME])
    cur.execute("CREATE TABLE %s (word varchar , data text);"%corp[NAME])
  return con, cur

class DBInterface:
  def __init__(self):
    self.con = sqlite3.connect(DBFILE, check_same_thread=False)
    self.cur = self.con.cursor()

  def execute(self, cmd):
    try:
      self.cur = self.cur.execute(cmd)
      r = self.cur.fetchall()
      return [(eval(r[0][1]),),]
    except sqlite3.ProgrammingError:
      self.con.rollback()
      return []
    except sqlite3.InternalError:
      self.con.rollback()
      return self.execute(cmd)
    except sqlite3.InterfaceError:
      self.__init__()
      return self.execute(cmd)

  def search(self, word, TBNAME=CITE):
    import dataWrapper
    if TBNAME not in corps:
        TBNAME = CITE
    if type(word) == list:
#       print "SELECT * FROM %s WHERE word IN ('%s');"%(TBNAME, "','".join(word))
      res = self.execute("SELECT * FROM %s WHERE word IN ('%s');"%(TBNAME, "','".join(word)))
      word = word[0]
    else:
#       print "SELECT * FROM %s WHERE word = '%s';"%(TBNAME, word)
      res = self.execute("SELECT * FROM %s WHERE word = '%s';"%(TBNAME, word))
    if len(res) == 0:
      return None
    else:
      r = dataWrapper.Patterns(res, word)
      return None if len(r.ngrams) == 0 else r

  def __del__(self):
    self.cur.close()
    self.con.close()

def thesauru(word):
  global model
  thesauru_list=[]
  if word == '_':
    return ['_']
  else:
    if word in model.vocab:
      indexes, metrics = model.cosine(word)
      if word in ['a','an', 'the']:
        return ['a','an', 'the']
      else:
        for i in indexes:
          thesauru_list.append(model.vocab[i])
        thesauru_list.append(word)
        return thesauru_list
    else:
        return ['_']

def sim(i, j):
  i = i.split('/')
  j = thesauru(j.encode('ascii'))
  return len(set(i).intersection(j)) > 0

def combine(i, j):
  it = i[0].split(' ')
  jt = j[0].split(' ')
  diff = 0
  if len(it) == len(jt):
    ot = []
    for iw,jw in zip(it,jt):
      if iw == jw:
        ot.append(iw)
      else:
        if sim(iw,jw):
          diff += 1
        else:
          diff += 10
        if diff > 1:  break
        if iw.endswith(']'):  iw = iw[:-1]
        ot.append("%s/%s"%(iw,jw))
  if diff == 1:
    if len(i) > 3:
      return [' '.join(ot), i[1]+j[1], i[2]+j[2], i[3]]
    return [' '.join(ot), i[1]+j[1], i[2]+j[2]]
  else:
    return None

def combineNgram(ngrams):
  i = 0
  while i+1 < len(ngrams):
    j = i+1
    while j < len(ngrams):
      c = combine(ngrams[i], ngrams[j])
      if c:
        del ngrams[j]
        ngrams[i] = c
      j += 1
    i += 1

def debug():
  db = connect()
  return db.search('difficulty')

def readPatterns(f='patterns_with_zh_ja.json'):
  import re
  d = defaultdict(dict)
  m = defaultdict(set)

  #for f in ['%s/reducer-%02d'%(folder, i) for i in range(80)]:
  for word, data in json.load(open(f)).iteritems():
    try:
        word, pos = word.split(':')
    except:
        print word, f
        continue
    for ngram in data[1:]:
      c = combineNgram(ngram[2])
      if c:  ngram[2] = c
    d[word][pos] = data
    for ngram in data[1:]:
      for example in ngram[2]:
        example[0] = map(unicode.strip, re.split("\[|\]", example[0]))
        other = example[0][1].split()[0]
        if other != word and len(other) > 0:
          m[other].add(word)
  m = {k: list(v) for k,v in m.iteritems()}
  return d, m

def genDB():
  global model
  con, cur = createDB()
  for corp in corpus:
    f, TBNAME = corp
    print f, TBNAME
    model = word2vec.load(word2vec_model[TBNAME])
    d, m = readPatterns(f)
    json.dump(m, open('syn_%s.json'%TBNAME,'w+'))

    for word, data in d.iteritems():
      #print '.', word, TBNAME
      cur.execute("""INSERT INTO %s (word, data) VALUES('%s','%s');"""%(TBNAME, word.replace("'","''"), json.dumps(data).replace("'","''")))
      con.commit()
    #cur.execute("SELECT * FROM test;")
  cur.close()
  con.close()

if __name__ == '__main__':
  connectDB()
  genDB()
