# Natural Language Toolkit: Language Models
#
# Copyright (C) 2001-2012 NLTK Project
# Authors: Steven Bird <sb@csse.unimelb.edu.au>
#          Daniel Blanchard <dblanchard@ets.org>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

from itertools import chain
from math import log

from nltk.probability import (ConditionalProbDist, ConditionalFreqDist,
                              SimpleGoodTuringProbDist)

def _ingrams(sequence, n, pad_left=False, pad_right=False, pad_symbol=None):
    """
    Return the ngrams generated from a sequence of items, as an iterator.
    For example:

        >>> from nltk.util import ingrams
        >>> list(ingrams([1,2,3,4,5], 3))
        [(1, 2, 3), (2, 3, 4), (3, 4, 5)]

    Use ngrams for a list version of this function.  Set pad_left
    or pad_right to true in order to get additional ngrams:

        >>> list(ingrams([1,2,3,4,5], 2, pad_right=True))
        [(1, 2), (2, 3), (3, 4), (4, 5), (5, None)]

    :param sequence: the source data to be converted into ngrams
    :type sequence: sequence or iter
    :param n: the degree of the ngrams
    :type n: int
    :param pad_left: whether the ngrams should be left-padded
    :type pad_left: bool
    :param pad_right: whether the ngrams should be right-padded
    :type pad_right: bool
    :param pad_symbol: the symbol to use for padding (default is None)
    :type pad_symbol: any
    :rtype: iter(tuple)
    """

    sequence = iter(sequence)
    if pad_left:
        sequence = chain((pad_symbol,) * (n-1), sequence)
    if pad_right:
        sequence = chain(sequence, (pad_symbol,) * (n-1))

    history = []
    while n > 1:
        history.append(next(sequence))
        n -= 1
    for item in sequence:
        history.append(item)
        yield tuple(history)
        del history[0]



def _estimator(fdist, bins):
    """
    Default estimator function using a SimpleGoodTuringProbDist.
    """
    # can't be an instance method of NgramModel as they
    # can't be pickled either.
    return SimpleGoodTuringProbDist(fdist)


class NgramModel():
    """
    A processing interface for assigning a probability to the next word.
    """

    # add cutoff
    def __init__(self, n, train, pad_left=True, pad_right=False,
                 estimator=None, *estimator_args, **estimator_kwargs):
        """
        Create an ngram language model to capture patterns in n consecutive
        words of training text.  An estimator smooths the probabilities derived
        from the text and may allow generation of ngrams not seen during
        training.

            >>> from nltk.corpus import brown
            >>> from nltk.probability import LidstoneProbDist
            >>> est = lambda fdist, bins: LidstoneProbDist(fdist, 0.2)
            >>> lm = NgramModel(3, brown.words(categories='news'), estimator=est)
            >>> lm
            <NgramModel with 91603 3-grams>
            >>> lm._backoff
            <NgramModel with 62888 2-grams>
            >>> lm.entropy(['The', 'Fulton', 'County', 'Grand', 'Jury', 'said',
            ... 'Friday', 'an', 'investigation', 'of', "Atlanta's", 'recent',
            ... 'primary', 'election', 'produced', '``', 'no', 'evidence',
            ... "''", 'that', 'any', 'irregularities', 'took', 'place', '.'])
            ... # doctest: +ELLIPSIS
            0.5776...

        :param n: the order of the language model (ngram size)
        :type n: int
        :param train: the training text
        :type train: list(str) or list(list(str))
        :param pad_left: whether to pad the left of each sentence with an (n-1)-gram of empty strings
        :type pad_left: bool
        :param pad_right: whether to pad the right of each sentence with an (n-1)-gram of empty strings
        :type pad_right: bool
        :param estimator: a function for generating a probability distribution
        :type estimator: a function that takes a ConditionalFreqDist and
            returns a ConditionalProbDist
        :param estimator_args: Extra arguments for estimator.
            These arguments are usually used to specify extra
            properties for the probability distributions of individual
            conditions, such as the number of bins they contain.
            Note: For backward-compatibility, if no arguments are specified, the
            number of bins in the underlying ConditionalFreqDist are passed to
            the estimator as an argument.
        :type estimator_args: (any)
        :param estimator_kwargs: Extra keyword arguments for the estimator
        :type estimator_kwargs: (any)
        """

        # protection from cryptic behavior for calling programs
        # that use the pre-2.0.2 interface
        assert(isinstance(pad_left, bool))
        assert(isinstance(pad_right, bool))

        self._n = n
        self._lpad = ('',) * (n - 1) if pad_left else ()
        self._rpad = ('',) * (n - 1) if pad_right else ()

        if estimator is None:
            estimator = _estimator

        cfd = ConditionalFreqDist()
        self._ngrams = set()
        
            
        # If given a list of strings instead of a list of lists, create enclosing list
        basestring=(str,bytes)
        if (train is not None) and isinstance(train[0], basestring):
            train = [train]

        for sent in train:
            for ngram in _ingrams(chain(self._lpad, sent, self._rpad), n):
                self._ngrams.add(ngram)
                context = tuple(ngram[:-1])
                token = ngram[-1]
                #print("confidence=%s\tcontext=%s\ttoken=%s\t%s" % (cfd, context, token, cfd[context]))
                cfd[context][token]=cfd[context].get(token, 0)+1
                #cfd[context].inc(token)

        if not estimator_args and not estimator_kwargs:
            self._model = ConditionalProbDist(cfd, estimator, len(cfd))
        else:
            self._model = ConditionalProbDist(cfd, estimator, *estimator_args, **estimator_kwargs)

        # recursively construct the lower-order models
        if n > 1:
            self._backoff = NgramModel(n-1, train, pad_left, pad_right,
                                       estimator, *estimator_args, **estimator_kwargs)

    def prob(self, word, context):
        """
        Evaluate the probability of this word in this context using Katz Backoff.

        :param word: the word to get the probability of
        :type word: str
        :param context: the context the word is in
        :type context: list(str)
        """

        context = tuple(context)
        if (context + (word,) in self._ngrams) or (self._n == 1):
            return self[context].prob(word)
        else:
            return self._alpha(context) * self._backoff.prob(word, context[1:])

    def _alpha(self, tokens):
        return self._beta(tokens) / self._backoff._beta(tokens[1:])

    def _beta(self, tokens):
        if tokens in self:
            return self[tokens].discount()
        else:
            return 1

    def logprob(self, word, context):
        """
        Evaluate the (negative) log probability of this word in this context.

        :param word: the word to get the probability of
        :type word: str
        :param context: the context the word is in
        :type context: list(str)
        """

        return -log(self.prob(word, context), 2)

    def choose_random_word(self, context):
        '''
        Randomly select a word that is likely to appear in this context.

        :param context: the context the word is in
        :type context: list(str)
        '''

        return self.generate(1, context)[-1]

    # NB, this will always start with same word if the model
    # was trained on a single text
    def generate(self, num_words, context=()):
        '''
        Generate random text based on the language model.

        :param num_words: number of words to generate
        :type num_words: int
        :param context: initial words in generated string
        :type context: list(str)
        '''

        text = list(context)
        for i in range(num_words):
            text.append(self._generate_one(text))
        return text

    def _generate_one(self, context):
        context = (self._lpad + tuple(context))[-self._n+1:]
        # print "Context (%d): <%s>" % (self._n, ','.join(context))
        if context in self:
            return self[context].generate()
        elif self._n > 1:
            return self._backoff._generate_one(context[1:])
        else:
            return '.'

    def entropy(self, text):
        """
        Calculate the approximate cross-entropy of the n-gram model for a
        given evaluation text.
        This is the average log probability of each word in the text.

        :param text: words to use for evaluation
        :type text: list(str)
        """

        e = 0.0
        text = list(self._lpad) + text + list(self._rpad)
        for i in range(self._n-1, len(text)):
            context = tuple(text[i-self._n+1:i])
            token = text[i]
            e += self.logprob(token, context)
        return e / float(len(text) - (self._n-1))

    def perplexity(self, text):
        """
        Calculates the perplexity of the given text.
        This is simply 2 ** cross-entropy for the text.

        :param text: words to calculate perplexity of
        :type text: list(str)
        """

        return pow(2.0, self.entropy(text))

    def __contains__(self, item):
        return tuple(item) in self._model

    def __getitem__(self, item):
        return self._model[tuple(item)]

    def __repr__(self):
        return '<NgramModel with %d %d-grams>' % (len(self._ngrams), self._n)


if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)
