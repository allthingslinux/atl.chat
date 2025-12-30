#!/bin/sh

set -e

cd /home/unrealircd/unrealircd

if [ -f /home/unrealircd/third-party-modules.list ]; then
    echo "Installing third-party modules..."

    while IFS= read -r module || [ -n "$module" ]; do
        case "$module" in
            \#*) continue ;;  # Skip comments
            "") continue ;;   # Skip empty lines
    esac

        echo "Installing module: $module"

        if ./unrealircd module install "$module"; then
            echo "✓ Successfully installed $module"
    else
            echo "✗ Failed to install $module"
            exit 1
    fi
  done   < /home/unrealircd/third-party-modules.list

    echo "Third-party modules installation completed"
else
    echo "No third-party modules configuration found"
fi
