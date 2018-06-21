# coding=UTF-8
from __future__ import unicode_literals
import cubane
import setuptools


with open("README.md", "r") as fh:
    long_description = fh.read()

version = '.'.join([unicode(x) for x in cubane.VERSION[:3]])


setuptools.setup(
    name='Cubane',
    description='Website/CMS/Shop and Backend Framework for Django.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    version=version,
    url='https://github.com/cubaneorg/cubane',
    author='Cubane Organisation',
    author_email='hello@cubane.org',
    license='GPL-3',
    classifiers=[
      'Development Status :: 5 - Production/Stable',
      'Intended Audience :: Developers',
      'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
      'Programming Language :: Python',
      'Programming Language :: Python :: 2',
      'Programming Language :: Python :: 2.7',
      'Topic :: Internet :: WWW/HTTP',
      'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
      'Topic :: Internet :: WWW/HTTP :: Dynamic Content :: Content Management System',
      'Topic :: Internet :: WWW/HTTP :: Site Management',
      'Topic :: Software Development :: Libraries',
      'Topic :: Software Development :: Libraries :: Application Frameworks',
      'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    packages=['cubane'],
    install_requires=[
        'Django>=1.10,<=1.11',
        'psycopg2>=2.5.4',
        'beautifulsoup4>=4.5.3',
        'lxml>=3.7.2',
        'django-htmlmin>=0.9.0',
        'Wand>=0.4.4',
        'requests>=2.12.5',
        'requests[security]',
        'pycrypto>=2.6.1',
        'oauth2>=1.9.0.post1',
        'mailsnake>=1.6.4',
        'ipaddr>=2.1.11',
        'ifaddr>=0.1.4',
        'pydns>=2.3.6',
        'pyspf==2.0.11',
        'chardet>=2.3.0',
        'stripe>=1.46.0',
        'pyBarcode>=0.7',
        'idna>=2.5'
    ]
)