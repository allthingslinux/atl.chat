#!/bin/bash

# One-time script to download all Prosody community modules locally
# Follows the official Prosody documentation approach
# Usage: ./setup-modules-locally.sh

set -e

PROSODY_MODULES_DIR="prosody-modules"
ENABLED_DIR="prosody-modules-enabled"

# Admin web dependencies removed - no longer needed

echo "📦 Setting up Prosody community modules (official approach)..."

# Clone the repository (do this once)
if [[ ! -d "$PROSODY_MODULES_DIR/.hg" ]]; then
    echo "⬇️  Cloning prosody-modules repository..."

    # Try to use bundle first (avoids rate limiting)
    if [[ -f "prosody-modules.zstd-v2" ]]; then
        echo "📦 Using local bundle to avoid rate limiting..."
        hg clone "prosody-modules.zstd-v2" "$PROSODY_MODULES_DIR"
        # Set up paths to use official repo for future updates
        cat >"$PROSODY_MODULES_DIR/.hg/hgrc" <<'EOF'
[paths]
default = https://hg.prosody.im/prosody-modules/
bundle = ../prosody-modules.zstd-v2
EOF
    else
        echo "🌐 Cloning directly from official repository..."
        hg clone https://hg.prosody.im/prosody-modules/ "$PROSODY_MODULES_DIR"
    fi
else
    echo "⬆️  Updating existing repository..."
    (cd "$PROSODY_MODULES_DIR" && (hg pull bundle 2>/dev/null && echo "📦 Updated from bundle" || (hg pull default && echo "🌐 Updated from official repo")) && hg update)
fi

# Create enabled directory
mkdir -p "$ENABLED_DIR"

# Read modules from modules.list
MODULES_FILE="modules.list"
if [[ -f "$MODULES_FILE" ]]; then
    echo "📄 Reading enabled modules from $MODULES_FILE..."
    mapfile -t DEFAULT_MODULES < <(grep -v '^#' "$MODULES_FILE" | grep -v '^$')
else
    echo "⚠️  $MODULES_FILE not found, using hardcoded defaults."
    DEFAULT_MODULES=(
        "mod_cloud_notify"
        "mod_cloud_notify_extensions"
        "mod_muc_notifications"
        "mod_muc_offline_delivery"
        "mod_http_status"
        "mod_compliance_latest"
    )
fi

echo "🔗 Creating symlinks for default modules..."
for module in "${DEFAULT_MODULES[@]}"; do
    if [[ -d "$PROSODY_MODULES_DIR/$module" ]]; then
        ln -sf "../$PROSODY_MODULES_DIR/$module" "$ENABLED_DIR/$module"
        echo "✅ $module -> enabled"
    else
        echo "❌ $module not found in repository"
    fi
done

# Fix module structure for community modules that have subdirectories
echo "🔧 Fixing module structure for community modules..."
for module_dir in "$ENABLED_DIR"/*; do
    if [[ -d "$module_dir" && "$module_dir" == *mod_* ]]; then
        module_name="${module_dir##*mod_}"
        if [[ -d "$module_dir/$module_name" && -f "$module_dir/$module_name/mod_$module_name.lua" ]]; then
            ln -sf "$module_dir/$module_name/mod_$module_name.lua" "$module_dir.lua"
            echo "✅ Fixed structure for $module_name"
        fi
    fi
done

echo "🎉 Local module setup complete!"
echo "📁 Repository: $PROSODY_MODULES_DIR"
echo "📁 Enabled modules: $ENABLED_DIR"
echo
echo "To add more modules: ln -s ../prosody-modules/mod_new_module prosody-modules-enabled/mod_new_module"
echo "To remove modules: rm prosody-modules-enabled/mod_unwanted_module"
