#!/bin/bash
set -e
redirects_file=etc-nginx-traits.d-redirect-existing-paths.conf

# interview
cat $redirects_file | awk '{$1=$1};1' - | grep " '/interviews" | sort > interview-path-map.txt

# press-package
cat $redirects_file | awk '{$1=$1};1' - | grep " '/for-the-press" | sort > press-package-path-map.txt

# blog-article
cat $redirects_file | awk '{$1=$1};1' - | grep " '/inside-elife" | sort > blog-article-path-map.txt
