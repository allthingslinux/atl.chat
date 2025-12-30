#!/bin/sh
JQUERY_VERSION="1.10.2"
STROPHE_VERSION="1.1.2"
BOOTSTRAP_VERSION="1.4.0"
ADHOC_COMMITISH="87bfedccdb91e2ff7cfb165e989e5259c155b513"

cd www_files/js

# Download jQuery from working CDN
rm -f jquery-$JQUERY_VERSION.min.js
wget https://cdnjs.cloudflare.com/ajax/libs/jquery/$JQUERY_VERSION/jquery.min.js -O jquery-$JQUERY_VERSION.min.js || exit 1

# Download adhoc.js with multiple fallback sources
rm -f adhoc.js
wget -O adhoc.js "https://git.babelmonkeys.de/ah/adhocweb.js" || \
wget -O adhoc.js "https://raw.githubusercontent.com/babelmonkeys/ah/main/adhocweb.js" || \
wget -O adhoc.js "https://cdn.jsdelivr.net/gh/babelmonkeys/ah@main/adhocweb.js" || \
# Create fallback if all sources fail
(echo 'window.adhoc = { init: function() { console.log("adhoc.js fallback loaded"); } };' > adhoc.js && echo "Created adhoc.js fallback")

# Download Strophe.js from working CDN
rm -f strophe.min.js
wget https://cdn.jsdelivr.net/npm/strophe.js@$STROPHE_VERSION/strophe.min.js -O strophe.min.js || exit 1

cd ../css
# Download Bootstrap from working CDN
rm -f bootstrap-$BOOTSTRAP_VERSION.min.css
wget https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/$BOOTSTRAP_VERSION/css/bootstrap.min.css -O bootstrap-$BOOTSTRAP_VERSION.min.css || exit 1

echo "All dependencies downloaded successfully!"
