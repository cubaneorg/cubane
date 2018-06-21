from setuptools import setup

setup(
    name='Cubane',
    description='Website/CMS/Shop and Backend Framework for Django.',
    version='1.0.0',
    url='https://github.com/cubaneorg/cubane',
    author='Cubane Organisation',
    author_email='hello@cubane.org',
    license='GPL-3',
    classifiers=[
      'Development Status :: 5 - Production/Stable',
      'Intended Audience :: Developers',
      'License :: OSI Approved :: GNU GENERAL PUBLIC LICENSE V3 (GPLV3)',
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
      'PyYAML>=3.11',
      'sh>=1.11'
    ],
    entry_points={
      'console_scripts': [
          'encrypt=crytto.main:run'
      ]
    }
)