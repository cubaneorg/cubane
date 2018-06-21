# coding=UTF-8
from __future__ import unicode_literals
from cubane.aggregator.source_base import SourceBase


class Enumerator():
    def __init__(self, source, since):
        self.messages = source.get_messages(since)
        self.has_next = True

    def next(self):
        try:
            return next(self.messages)
        except StopIteration:
            self.has_next = False
            raise StopIteration


class Aggregator(SourceBase):
    def __init__(self, sources):
        self.sources = sources

    def get_messages(self, since):
        enumerators = [Enumerator(source, since) for source in self.sources]

        while self.can_next(enumerators):
            for enum in enumerators:
                if enum.has_next:
                    try:
                        yield enum.next()
                    except StopIteration:
                        pass


    def can_next(self, enumerators):
        for enum in enumerators:
            if enum.has_next:
                return True
        return False
