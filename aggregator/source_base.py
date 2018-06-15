# coding=UTF-8
from __future__ import unicode_literals


class SourceBase(object):
    def get_messages(self, since):
        while True:
            messages = self.get_raw_messages(since)
            if len(messages) == 0:
                return

            for m in messages:
                data = self.normalize(m)
                if since > float(data.get('created_date', 0)):
                    return

                yield data


    def get_raw_messages(self, since=None):
        raise NotImplementedError('Not implemented.')


    def normalize(self):
        raise NotImplementedError('Not implemented.')
