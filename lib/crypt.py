# coding=UTF-8
from __future__ import unicode_literals
from django.conf import settings
from Crypto.Cipher import Blowfish
from libjson import to_json, decode_json
import base64


__ALL__ = [
    'encrypt', 'decrypt'
]


def encrypt(plain):
    """
    Convert given plain data into json and encrypt the resulting json code and finally return the
    encrypted representation of it in base64.
    """
    alg = Blowfish.new(settings.CRYPT_KEY)
    json = to_json(plain)

    # pad to block size
    while len(json) % alg.block_size != 0:
        json += ' '

    return base64.b64encode(alg.encrypt(json))


def decrypt(ciph):
    """
    Decrypt given encrypted cipher (requires base64 representation) and return the plain python object.
    """
    alg = Blowfish.new(settings.CRYPT_KEY)
    plain = alg.decrypt(base64.b64decode(ciph))
    return decode_json(plain)