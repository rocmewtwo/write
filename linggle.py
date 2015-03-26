# all the imports
from itertools import cycle
import re
from flask import Flask, request, render_template, make_response
import json
import string

import sql

DEBUG = False

app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('FLASKR_SETTINGS', silent=True)
#app.config['DEBUG'] = True
db = sql.connect()
syn = json.load(open('syn.json'))

def home(*args, **kwargs):
  if 'writeaway' in request.headers['Host']:
    title = 'WriteAway'
  elif 'writebetter' in request.headers['Host']:
    title = 'WriteBetter'
  elif 'bestwrite' in request.headers['Host']:
    title = 'BestWrite'
  else:
    title = 'WriteAhead'
  return render_template('show_entries.html', *args, title=title, **kwargs)

@app.route('/')
def root():
  return home()

@app.route('/more')
def more():
  resp = make_response(home(corps = sql.corpNames, selectedCorp = sql.BNC))
  corp = request.cookies.get('corp')
  if request.cookies.get('corp') not in sql.corpNames:
    resp.set_cookie('corp', sql.BNC)
    corp = sql.BNC
  return home(corps = sql.corpNames, selectedCorp = corp)

@app.route('/<corp>')
def corpus(corp):
  if not corp in sql.nameToCorp:
    return ' '
  else:
    return home(searchCorp=sql.nameToCorp[corp])

def search(query, corp):
  return db.search([query] + syn[query] if syn.has_key(query) else query, corp)

@app.route('/add', methods=['GET'])
def add_entry():
  text = request.args['text'].lower().__str__().translate(string.maketrans("",""), string.punctuation).split()
  if 'corp' in request.args:
    corp = request.args['corp']
  else:
    corp = sql.CITE_TRANS
  pos = None
  if 'hover' in request.args:
    pos = int(request.args['hover'])
  elif 'sel' in request.args and request.args['sel'] != '0 0':
    sel = map(int, request.args['sel'].split())
    pos = len(request.args['text'][:sel[0]].split())
  if pos != None and pos < len(text):
    entries = search(text[pos], corp)
  else:
    entries = search(text[-1], corp)
    if entries == None and len(text) > 1:  entries = search(text[-2], corp)
  if entries != None:
    if len(text) > 1:
      entries.sortBySentence(text)
    return render_template('query.html', entries=entries.sortedNgrams(), showMore=(request.cookies.get('show_more') == 'true'), showMoreExp=(request.cookies.get('show_more_exp') == 'true'), lang=(request.cookies.get('lang')), corp=corp)
  else:
    return render_template('noquery.html')

@app.errorhandler(500)
def internalError(e):
  import traceback
  if DEBUG:
    return traceback.format_exc()
  else:
    return 'ERROR!'

if __name__ == '__main__':
  app.run()
