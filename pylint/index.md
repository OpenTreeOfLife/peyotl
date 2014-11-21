---
layout: page
title: Pylint configuration
permalink: /pylint/
---
[Pylint](http://www.pylint.org/) is a great tool for checking your code. It warns you about
violations of common conventions and the use of dangerous constructs.
It is also quite configurable.

You can integrate pylint into text editors so that runs on every save. This produces
an annoying set of warnings if you have suspect code.
Because some of the peyotl developers use this feature, we have pylintrc file that
disables some of the messages that we are not concerned about.
The peyotl code also is littered with many `pylint: disable`... comments that 
disable warnings when we are confident that we are using a dangerous construct 
correctly in a portion of the code (but we do not want to disable warnings if we
unintentionally use these constructs)

You can run the "peyotl-style" pylint by:

    bash dev/run_pylint.sh

The codebase should come in with a very high score (9.95/10 at the time of this writing)

We will try to keep this page up-to-date with explanations about why we disable message types,
but we will populate that list of justifications as needed when someone asks about a decision.
In general:

   * we do not like to be warned super strict naming conventions for variable,
   * we try to stick to the 80 char width limit for most code logic, but find it
        very convenient to allow error messages in exceptions and string templates
        to exceed that. So the line length warning is set to 120

A wiki explaining the error codes used by pylint is [here](http://pylint-messages.wikidot.com/all-codes).

