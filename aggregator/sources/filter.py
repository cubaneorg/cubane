# coding=UTF-8
from __future__ import unicode_literals
from cubane.aggregator.source_base import SourceBase
from cubane.lib.bad_words import contains_bad_word
from cubane.lib.bad_words import is_suspicious_username
from cubane.lib.bad_words import is_latin
from cubane.lib.bad_words import get_bad_words


class Filter(SourceBase):
    def __init__(self, source, bad_words=[], username_blacklist=[]):
        self.source = source
        self.bad_words = bad_words
        self.username_blacklist = username_blacklist


    def get_messages(self, since):
        for message in self.source.get_messages(since):
            if not self.is_bad_word_in_message(message):
                yield message


    def is_bad_word_in_message(self, message):
        # simply do not accept anything from user's with too many
        # suspicious characters in it
        if is_suspicious_username(message.get('author')):
            return True

        # username blacklist
        for username in self.username_blacklist:
            if username.lower() in message.get('author', '').lower():
                return True

        # message text
        if contains_bad_word(message.get('text'), self.bad_words):
            return True

        # author/username
        if contains_bad_word(message.get('author'), self.bad_words):
            return True

        # do not accept non-latin message text
        if not is_latin(message.get('text')):
            return True

        return False