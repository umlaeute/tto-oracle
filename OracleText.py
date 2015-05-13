#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright © 2015, IOhannes m zmölnig, forum::für::umläute

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this file.  If not, see <http://www.gnu.org/licenses/>.

import nltk
from nltk.probability import LidstoneProbDist, WittenBellProbDist, SimpleGoodTuringProbDist
from NgramModel import NgramModel

import random

#nltk.help.upenn_tagset()
TAGS=[
    'NN', # noun (singular)
    'NNS',# noun (plural)
    'NNP',# proper noun (singular)
    'NNPS',# proper noun (plural)

    'JJ', # adjective
    'JJR',# comparative
    'JJS',# superlative

    'VB', # verb
    'VBD',# verb (past)
    'VBN',# verb (past part.)
    'VBP',# verb (present; not 3rd pers)
    'VBZ',# verb (present; 3rd pers)
    ]
INTERESTING_TAGS=[
    'NN', 'JJ', 'VB'
    ]

class OracleText():
    """
    text generator for TTO
    """
    def __init__(self, filename, order=2):
        text=None
        self.name=filename
        self.interesting_tags=INTERESTING_TAGS
        self.tags=TAGS
        with open(filename) as f:
            text=f.read()
        text, startwords=self._text2words(text)

        self.estimator = lambda fdist, bins: LidstoneProbDist(fdist, 0.2)
        self.lm = NgramModel(order, text, estimator=self.estimator)
        self.startwords=startwords
        self.ctx=nltk.text.ContextIndex(text, filter=lambda x:x.isalpha(), key=lambda s:s.lower())
    def common_contexts(self, words, fail_on_unknown=False):
        return self.ctx(words, fail_on_unknown)
    def word_similarity_dict(self, word):
        return self.ctx.word_similarity_dict(word)
    def similar_words(self, word, n=20):
        return self.ctx.similar_words(word, n)
    def similindex(self, words, n=20):
        if not words:
            return 0
        sum=0
        for w in words:
            sum+=len(self.ctx.similar_words(w, n))
        res=sum/(n*len(words))
        print("%s: similarity %s %s" % (self.name, res, words))
        return res
    def generate_basetext(self, wordcount=100):
        startword=random.choice(self.startwords)
        return self.lm.generate(wordcount, [startword])
    def speak(self, inputtext='', maxwords=200, truncate=False):
        t=self._speak(inputtext, maxwords, truncate)
        s=self._array2text(t).lower()
        return s
    def _speak(self, inputtext, maxwords, truncate):
        def get_tagindices(text, tags):
            d={}
            for i, (w,t) in enumerate(text):
                if t in tags:
                    if not t in d:
                        d[t]=[]
                    d[t]+=[i]
            return d
        inwords=self.postag_text(inputtext)
        replace_dict={}
        for (w,t) in inwords:
            for tag in INTERESTING_TAGS:
                if t.startswith(tag):
                    if not tag in replace_dict:
                        replace_dict[tag]=[]
                    replace_dict[tag]+=[w]
        self._cleanup_dict(replace_dict)
        replace_count={}
        for k in replace_dict:
            replace_count[k]=len(replace_dict[k])

        templatext=self.generate_basetext(maxwords)
        template=nltk.pos_tag(templatext)
        if truncate:
            template=self._truncate_text(template, minimumtags=replace_count)
        res=[x for x,t in template]

        tmplindices=get_tagindices(template, replace_dict.keys())
        for t in tmplindices:
            while t in replace_dict:
                words=replace_dict[t]
                indices=tmplindices[t]
                if not indices:
                    del replace_dict[t]
                    continue
                # pick a random index in the result
                n=random.randint(0, len(indices)-1)
                idx=indices.pop(n)
                res[idx]=words.pop(0)
                if not words:
                    del replace_dict[t]
        return res
    def tags(self, only_interesting=True):
        if only_interesting:
            return self.interesting_tags
        return self.tags
    @staticmethod
    def _cleanup_dict(d):
        keys=list(d.keys())
        for k in keys:
            if not d[k]:
                del d[k]

    @staticmethod
    def _truncate_text(text, stoptags=['.'], minimumtags={}):
        """
        shortens a pos_tagged text at the next convenient stoptag.
        minimumtags is a dictionary containing tag:mincount mappings.
        the text won't be shortened until all tags in the dictionary
        have been seen at least mincount times
        """
        #print("truncating for %s" % (minimumtags))
        force_truncate=True
        if minimumtags:
            force_truncate=False
        stopindex=0
        for i,(w,t) in enumerate(text):
            if minimumtags and t in minimumtags:
                minimumtags[t]-=1
                if minimumtags[t]<=0:
                    del minimumtags[t]
                if not minimumtags:
                    force_truncate=True
            if t in stoptags:
                stopindex=i
                if force_truncate:
                    break
        if force_truncate:
            print("truncating %s to %s" % (len(text), stopindex+1))
            return text[:stopindex+1]
        return text


    @staticmethod
    def _replace(template, repl, repltags=['NN', 'JJ'], truncate=False):
        def get_tagdict(text, tags):
            d={}
            p={}
            for i, (w,t) in enumerate(text):
                if t in tags:
                    if not t in d:
                        d[t]=[]
                        p[t]=[]
                    d[t]+=[w]
                    p[t]+=[i]
            return d,p
        replwords,_=get_tagdict(repl, repltags)
        tagcount={}
        for k in replwords:
            tagcount[k]=len(replwords[k])
        if truncate:
            #print("tags: %s" % (replwords))
            #print("pre-truncate: %s" % (template))
            template=self._truncate_text(template, minimumtags=tagcount)
            #print("pst-truncate: %s" % (template))
        _,tmplindices=get_tagdict(template, repltags)


        res=[x for x,t in template]

        for t in tmplindices:
            while t in replwords:
                words=replwords[t]
                indices=tmplindices[t]
                # pick a random index in the result
                n=random.randint(0, len(indices)-1)
                idx=indices.pop(n)
                res[idx]=words.pop(0)
                if not words:
                    del replwords[t]
        return res

        for w,t in template:
            if t in replwords:
                repw=replwords[t]
                w=repw.pop(0)
                if repw:
                    replwords[t]=repw
                else:
                    del replwords[t]
            res+=[w]
        return res

    @staticmethod
    def _array2text(text):
        """takes a list of tokens and reassembles them into a string"""
        puncts=".,;:'"
        result=""
        for w in text:
            if w[0] in puncts:
                result+=w
            else:
                result+=' '+w
        return result

    @staticmethod
    def _text2words(text):
        res=[]
        startwords=set()
        for sentence in nltk.sent_tokenize(text):
            words=nltk.word_tokenize(sentence)
            if words:
                res+=words
                startwords.add(words[0])
        return res, list(startwords)

    @staticmethod
    def postag_text(text):
        #print("postag_text: %s" % (text))
        insent=nltk.sent_tokenize(text)
        inwords=[]
        for sentence in insent:
            w=nltk.word_tokenize(sentence)
            inwords+=nltk.pos_tag(w)
        #print("postag_text:: %s" % (inwords))
        return inwords
    def postag_words(taggedtext, dictionary=dict()):
        #print("postag_words: %s .. %s" % (taggedtext, dictionary))
        if type(taggedtext) == str:
            ## that's a string; let's tag it
            taggedtext=OracleText.postag_text(taggedtext)
        for (w,t) in taggedtext:
            taglist=dictionary.get(t, [])
            taglist.append(w)
            dictionary[t]=taglist
        return dictionary

def foo():
    import sys
    if (len(sys.argv)>1):
        filename=sys.argv[1]
    textin=nltk.pos_tag(nltk.word_tokenize(' '.join(sys.argv[2:])))
    #print("input: %s" % (textin))
    with open(filename) as f:
        text=f.read()
        textgen=generate(text.split(), 200)
        print("textgen: %s" % (textgen))
        #print("TextGen: %s" % (OracleText._array2text(textgen)))
        text1=nltk.word_tokenize(OracleText._array2text(textgen))
        pt=nltk.pos_tag(text1)
        #print(OracleText._array2text(text1))
        #print("pos_tags: %s" %(pt))
        textout=OracleText._replace(pt, textin, truncate=True)
        print("output: %s" % (OracleText._array2text(textout)))


if '__main__' ==  __name__:
    import sys
    filename=sys.argv[1]
    print("filename: %s" % (filename))
    o=OracleText(filename)
    t=o.speak(inputtext="The artist is stupid!", truncate=True)
    print(t)
