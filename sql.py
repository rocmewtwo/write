import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import json
import os
from collections import defaultdict
import urlparse

DBNAME = "linggle"

JSON, NAME = range(2)

BNC = 'bnc'
CITESEER = 'citeseer'
PHD = 'phd'
PHD_NF = 'PHD_NF'
CITE_TRANS = 'cite_trans'

corpus = [
['diff/bnc.json', BNC],
#['diff/citeseer.json', CITESEER],
['diff/overuse.json', PHD],
['diff/phd.nf.json', PHD_NF],
['patterns_with_zh_ja.json', CITE_TRANS],
]

corpNames = [(BNC,"general"), (CITE_TRANS,"academic"), (PHD,"overuse"), (PHD_NF,"learner")]
nameToCorp = dict([i[::-1] for i in corpNames])
corps = zip(*corpNames)[0]

urlparse.uses_netloc.append("postgres")
url = urlparse.urlparse(os.environ["DATABASE_URL"])
#url = urlparse.urlparse('postgres://vdqdjsixutvevb:TQMkmAd8mW7dfWNLWmvI2vnNJh@ec2-184-73-165-193.compute-1.amazonaws.com:5432/d2t44ilh4v3g5u')

def connectDB():
  con = psycopg2.connect(
    database=url.path[1:],
    user=url.username,
    password=url.password,
    host=url.hostname,
    port=url.port)
  cur = con.cursor()
  return con, cur

def createDB():
  con = psycopg2.connect(host = 'localhost')

  con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
  cur = con.cursor()
  try:
    cur.execute('DROP DATABASE %s'%DBNAME)
  except:
    pass

  cur.execute('CREATE DATABASE %s'%DBNAME)
  cur.close()
  con.close()

  con, cur = connectDB()
  for corp in corpus:
    cur.execute("CREATE TABLE %s (word varchar , data json);"%corp[NAME])
  return con, cur

class DBInterface:
  def __init__(self):
    self.con, self.cur = connectDB()

  def execute(self, cmd):
    try:
      self.cur.execute(cmd)
      return self.cur.fetchall()
    except psycopg2.ProgrammingError:
      self.con.rollback()
      return []
    except psycopg2.InternalError:
      self.con.rollback()
      return self.execute(cmd)
    except psycopg2.InterfaceError:
      self.__init__()
      return self.execute(cmd)

  def search(self, word, TBNAME=CITE_TRANS):
    import dataWrapper
    if TBNAME not in corps:
        TBNAME = CITE_TRANS
    if type(word) == list:
      print "SELECT * FROM %s WHERE word IN ('%s');"%(TBNAME, "','".join(word))
      res = self.execute("SELECT * FROM %s WHERE word IN ('%s');"%(TBNAME, "','".join(word)))
      word = word[0]
    else:
      print "SELECT * FROM %s WHERE word = '%s';"%(TBNAME, word)
      res = self.execute("SELECT * FROM %s WHERE word = '%s';"%(TBNAME, word))
    if len(res) == 0:
      return None
    else:
      r = dataWrapper.Patterns(res, word)
      return None if len(r.ngrams) == 0 else r

  def close(self):
    self.con.close()
    self.cur.close()

def connect():
  return DBInterface()

def sim(i, j):
  import rephrase
  i = i.split('/')
  j = rephrase.thesauru(j.encode('ascii'))
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
  con, cur = createDB()
  for corp in corpus:
    print corp
    f, TBNAME = corp
    d, m = readPatterns(f)
    json.dump(m, open('syn_%s.json'%TBNAME,'w+'))

    for word, data in d.iteritems():
      #print '.', word, TBNAME
      cur.execute("""INSERT INTO %s (word, data) VALUES('%s','%s');"""%(TBNAME, word.replace("'","''"), json.dumps(data).replace("'","''")))
      con.commit()
    #cur.execute("SELECT * FROM test;")
  con.close()
  cur.close()

if __name__ == '__main__':
  connectDB()
  genDB()
