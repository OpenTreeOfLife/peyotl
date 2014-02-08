from setuptools import setup
# setup.py largely based on
#   http://hynek.me/articles/sharing-your-labor-of-love-pypi-quick-and-dirty/

setup(
    name='peyotl',
    version='0.0.0a',
    description='Library for interacting with Open Tree of Life resources',
    long_description=(open('README.md').read() + '\n\n' +
                      open('AUTHORS.txt').read()),
    url='https://github.com/OpenTreeOfLife/peyotl',
    license='BSD',
    author='Mark T. Holder',
    author_email='mtholder',
    py_modules=['peyotl'],
    include_package_data=True,
    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
    ],
)