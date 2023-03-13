#!/bin/bash
# scrub.sh uses the autopep8 tool to clean up whitespace and other small bits

# E261 = double space before inline comment
# E501 = don't squeeze lines to fix max length
# E302 = don't go crazy with the double whitespace between funcs
# E401 = don't put imports on separate lines
# E305 = don't put two blank lines after the last function
# E309 = don't put a blank line after class declaration
# E721 = Use "isinstance()" instead of comparing types directly.
#  - this is a *bad* check as checking if a value is an *instance* of something is different from checking it's *type*.
#  - for example, a datetime.datetime is an *instance* of a datetime.date 
# E731 = don't assign a lambda expression check.

autopep8 \
    --in-place --recursive --aggressive \
    --ignore E501,E302,E261,E401,E305,E309,E721,E731 \
    --exclude *.html \
    src/
