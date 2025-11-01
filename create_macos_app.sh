#!/bin/bash
# Create macOS .app bundle for Dictation Manager

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="Dictation Manager.app"
APP_DIR="$HOME/Applications/$APP_NAME"

echo "🚀 Creating macOS Application..."
echo ""

# Create app bundle structure
echo "📁 Creating .app bundle structure..."
mkdir -p "$APP_DIR/Contents/MacOS"
mkdir -p "$APP_DIR/Contents/Resources"

# Create Info.plist
echo "📝 Generating Info.plist..."
cat > "$APP_DIR/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>DictationManager</string>
    <key>CFBundleIdentifier</key>
    <string>com.local.dictation-manager</string>
    <key>CFBundleName</key>
    <string>Dictation Manager</string>
    <key>CFBundleDisplayName</key>
    <string>Dictation Manager</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSMinimumSystemVersion</key>
    <string>10.13</string>
    <key>NSMicrophoneUsageDescription</key>
    <string>Dictation Manager needs access to your microphone for voice recognition.</string>
</dict>
</plist>
EOF

# Create launcher script
echo "🔧 Creating launcher script..."
cat > "$APP_DIR/Contents/MacOS/DictationManager" << 'EOF'
#!/bin/bash
# Dictation Manager Launcher for macOS

# Use AppleScript to open Terminal and run the application
osascript << 'APPLESCRIPT'
tell application "Terminal"
    activate
    do script "cd 'PROJECT_DIR_PLACEHOLDER' && ./run.sh"
end tell
APPLESCRIPT
EOF

# Replace placeholder with actual project directory
sed -i '' "s|PROJECT_DIR_PLACEHOLDER|$PROJECT_DIR|g" "$APP_DIR/Contents/MacOS/DictationManager"

# Make launcher executable
chmod +x "$APP_DIR/Contents/MacOS/DictationManager"

# Copy icon if exists
if [ -f "$PROJECT_DIR/assets/logo.png" ]; then
    cp "$PROJECT_DIR/assets/logo.png" "$APP_DIR/Contents/Resources/icon.png"
    echo "🎨 Icon copied"
fi

echo ""
echo "✅ macOS app created successfully!"
echo ""
echo "📍 Location: $APP_DIR"
echo ""
echo "🔍 The app should now appear in:"
echo "   - Launchpad"
echo "   - Spotlight (search 'Dictation Manager')"
echo "   - ~/Applications/ folder"
echo ""
echo "⚠️  Note: You may need to:"
echo "   1. Log out and log back in for it to appear immediately"
echo "   2. Or run: killall Dock"
echo ""
