import os
import re
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

# folder where pygmos is stored
here = os.path.abspath(os.path.dirname(__file__))



#Taken from the Python docs:
#Utility function to read the README file.
#Used for the long_description.  It's nice, because now 1) we have a
#top level README file and 2) it's easier to type in the README file
#than to put a raw string in below
def read(fname):
    return open(os.path.join(here, fname)).read()



setup(
    name='pygmos',
    version='0.1.0.dev',
    description='Automatic reduction of GMOS spectroscopic data',
    author='Cristobal Sifon',
    author_email='sifon@astro.princeton.edu',
    long_description=read('README.md'),
    url='https://github.com/cristobal-sifon/pygmos',
    packages=['pygmos'],
    package_data={'': ['docs/*',
                       'pygmos/CuAr_GMOS.dat',
                       'pygmos/*.cl',
                       'README.md']},
    scripts=['bin/pygmos'],
    install_requires=[]
    )
