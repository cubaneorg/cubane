# coding=UTF-8
from __future__ import unicode_literals
from cubane.aggregator.source_base import SourceBase
import oauth2 as oauth
import time
import urllib
import json


class Twitter(SourceBase):
    def __init__(self, settings):
        self.consumer_key = settings.get('consumer_key')
        self.consumer_secret = settings.get('consumer_secret')
        self.count = settings.get('count', 100)
        self.query = settings.get('query')
        self.previous_max_id = None
        self.max_id = None


    def get_raw_messages_request(self, url, timeout=None):
        return json.loads(self.oauth_req(url))


    def get_tweet(self, tweet_id):
        url = 'https://api.twitter.com/1.1/statuses/show/%s.json?%s' % (
            tweet_id,
            urllib.urlencode({
                'tweet_mode': 'extended'
            })
        )
        return json.loads(self.oauth_req(url))


    def get_raw_messages(self, since=None):
        if not (self.consumer_key and self.consumer_secret and self.query):
            return []

        # Construct payload
        payload = {
            'q': self.query,
            'count': self.count
        }
        if self.max_id:
            payload['max_id'] = self.max_id

        # Receive page of messages
        try:
            response = self.get_raw_messages_request('https://api.twitter.com/1.1/search/tweets.json?%s' % urllib.urlencode(payload))
        except:
            response = {}

        # maintain max id
        for m in response.get('statuses', []):
            self.previous_max_id = self.max_id
            max_id = m.get('id')
            self.max_id = max_id + 1

        # we processed all messages
        if self.previous_max_id == self.max_id:
            return []

        # for each message, get details
        messages = []
        for m in response.get('statuses', []):
            # skip re-tweets...
            if m.get('retweeted_status', False):
                continue

            # skip tweets older than since argument
            if since is not None and since != 0:
                ts = self._parse_timestamp(m.get('created_at'))
                if since > float(ts):
                    continue

            # fetch individual tweet from twitter api in order to get full
            # extended details including media data...
            try:
                message = self.get_tweet(m.get('id'))
                messages.append(message)
            except:
                pass

        return messages


    def normalize(self, message):
        return {
            'id': message.get('id'),
            'author': message['user'].get('screen_name') if message.get('user') else None,
            'profile_picture': message['user'].get('profile_image_url') if message.get('user') else None,
            'created_date': self._parse_timestamp(message.get('created_at')),
            'text': message.get('full_text', message.get('text')),
            'media': message.get('entities').get('media') if message.get('entities') else None,
            'entities': message.get('entities'),
            'link': 'https://twitter.com/statuses/' + unicode(message.get('id')) if message.get('id') else None,
            'source': 'twitter'
        }


    def _parse_timestamp(self, ts):
        return unicode(time.mktime(time.strptime(ts, '%a %b %d %H:%M:%S +0000 %Y'))) if ts else 0


    def oauth_req(self, url, http_method="GET", post_body=None, http_headers=None):
        consumer = oauth.Consumer(key=self.consumer_key, secret=self.consumer_secret)
        client = oauth.Client(consumer)
        resp, content = client.request(url, "GET")

        return content
