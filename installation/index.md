---
layout: page
title: Installation
permalink: /installation/
---
# TL;DR

    $ git clone https://github.com/OpenTreeOfLife/peyotl.git
    $ cd peyotl
    $ pip install -r requirements.txt
    $ python setup.py develop

and then look at the [configuration page](../configuration)

# Download

Peyotl code is regularly tested using [Python 2.7](https://www.python.org/download/releases/2.7). Earlier versions of python are not officially supported. It has been tested some under python 3.3 and 3.4

Because peyotl is still under very active development. you probably don't want to use`pip` or `easy_install` to install it yet.

You should probably download it using version control (rather than by downloading a snapshot). Make sure that you have a reasonably modern version of [git](http://git-scm.com/) and then run:

    $ git clone https://github.com/OpenTreeOfLife/peyotl.git

# Installation
We highly recommend that you install in a sandbox environment using [virtualenv](https://pypi.python.org/pypi/virtualenv):

    $ virtualenv my-env
    $ source my-env/bin/activate
    
If you do not use virtualenv, you'll need to install [pip](https://pypi.python.org/pypi/pip) (virtualenv installs pip for you).

To install the dependencies:

    $ cd peyotl
    $ pip install -r requirements.txt

Finally, you should probably install using the `develop` command rather than the normal `install` command. This will put a link from your python distributions `site-packages` directory (`<install-prefix>/lib/python2.7/site-packages`) to peyotl. Install copies the files to your `site-packages` directory. That means that you'll have to reinstall each time you get a new version of peyotl. By using the link from the `develop` command, your python distribution will always find the version of peyotl in the original directory.

    $ python setup.py develop

# Keeping up-to-date
If you have followed the recommended approach then you'll just need to run:

    $ git pull origin master

to pull down the latest changes from the `git` repository from which you cloned `peyotl`.
