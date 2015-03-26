from collections import defaultdict
import re

class Patterns:
  class Ngram:
    class Example:
      rePost = re.compile("([^\|]*)(\|tw:)?([^\|]*)(\|jp:)?([^\|]*)")
      def __init__(self, data, parent):
        if len(data) == 4:
          (self.prev, self.ngram, self.post), self.c1, self.c2, self.translate = data
        elif len(data) == 3:
          (self.prev, self.ngram, self.post), self.c1, self.c2= data
          self.translate = None
        self.parent = parent
        self.sentPrev = self.prev.split()
        self.sentPost = self.ngram.split()[1:] if len(self.post) == 0 else self.ngram.split()[1:] + [self.post]
        self.sent = None
      def getTranslate(self, lang):
        if lang == 'en' or self.translate == None:
          return ''
        elif lang == 'zh':
          return self.translate['zh']
        elif lang == 'jp':
          return self.translate['ja']
      def __repr__(self):
        return "%s(%r)" % (self.__class__, self.ngram)
      def __lt__(self, other):
        sSent = self.matchCount()
        oSent = other.matchCount()
        return sSent < oSent or (sSent == oSent) and (self.c1 < other.c1)
      def matchCount(self):
        if self.sent == self.parent.parent.sent:
          return self.match
        self.sent = self.parent.parent.sent
        post = len([True for s,p in zip(self.sentPost, self.parent.parent.sentPost) if s[:4]==p[:4]])
        prev = len([True for s,p in zip(self.sentPrev[::-1], self.parent.parent.sentPrev[::-1]) if s[:4]==p[:4]])
        self.match = prev + post
        return self.match


    def __init__(self, data, parent):
      self.ngram = data[0]
      self.count = data[1]
      self.parent = parent
      self.countX = 0
      self.example = []
      for ngram in data[2]:
        self.example.append(self.Example(ngram, self))
    def __lt__(self, other):
      if self.countX == other.countX:
        return self.count < other.count
      else:
        return self.countX < other.countX
    def __repr__(self):
      return "%s(%s)" % (self.__class__, self.ngram)

    def sortExample(self):
      self.countX = sum([(e.matchCount()<<10)+e.c1*e.matchCount() for e in self.example])
      self.example = sorted(self.example, reverse=True)

  def __init__(self, datas, word):
    self.ngrams = defaultdict(list)
    self.word = word
    for data in datas:
      for pos, ngrams in data[1].iteritems():
        #if ngrams[0] < 100:
	#  continue
        for ngram in ngrams[1:]:
          self.ngrams[pos].append(self.Ngram(ngram, self))

  def sortedNgrams(self):
    return sorted(self.ngrams.items(), key=lambda ngrams:-sum([(i.countX<<10)+i.count for i in ngrams[1]]))

  def sortBySentence(self, sent):
    if type(sent) == str:  sent = sent.split()
    self.sent = sent
    pos = sent.index(self.word)
    self.sentPrev = self.sent[:pos]
    self.sentPost = self.sent[pos+1:]
    for pos in self.ngrams:
      for e in self.ngrams[pos]:
        e.sortExample()
      self.ngrams[pos] = sorted(self.ngrams[pos], reverse=True)

