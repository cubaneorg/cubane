# coding=UTF-8
from __future__ import unicode_literals
from cubane import VERSION_STRING
import setuptools


with open("README.md", "r") as fh:
    long_description = fh.read()


requirements = []
with open("cubane/requirements/common.txt", "r") as fh:
    requirements = fh.read().splitlines()


setuptools.setup(
    name='Cubane',
    description='Website/CMS/Shop and Backend Framework for Django.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    version=VERSION_STRING,
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
      'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    packages=setuptools.find_packages(),
    include_package_data=True,
    scripts=[
        'cubane/bin/cubane'
    ],
    install_requires=requirements
)