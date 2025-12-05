#!/bin/bash
# iOS Build Script for Panel App
# This script builds the iOS application

echo "========================================"
echo "Panel iOS Build Script"
echo "========================================"
echo

cd "$(dirname "$0")/ios"

echo "[1/5] Installing CocoaPods dependencies..."
pod install
if [ $? -ne 0 ]; then
    echo "ERROR: Pod install failed"
    exit 1
fi

echo "[2/5] Cleaning build folder..."
xcodebuild clean \
    -workspace Panel.xcworkspace \
    -scheme Panel
if [ $? -ne 0 ]; then
    echo "ERROR: Clean failed"
    exit 1
fi

echo "[3/5] Running tests..."
xcodebuild test \
    -workspace Panel.xcworkspace \
    -scheme Panel \
    -destination 'platform=iOS Simulator,name=iPhone 15 Pro'
if [ $? -ne 0 ]; then
    echo "WARNING: Tests failed but continuing..."
fi

echo "[4/5] Building for simulator..."
xcodebuild build \
    -workspace Panel.xcworkspace \
    -scheme Panel \
    -sdk iphonesimulator \
    -configuration Debug
if [ $? -ne 0 ]; then
    echo "ERROR: Simulator build failed"
    exit 1
fi

echo "[5/5] Archiving for release..."
xcodebuild archive \
    -workspace Panel.xcworkspace \
    -scheme Panel \
    -sdk iphoneos \
    -configuration Release \
    -archivePath build/Panel.xcarchive
if [ $? -ne 0 ]; then
    echo "ERROR: Archive failed"
    exit 1
fi

echo
echo "========================================"
echo "Build Complete!"
echo "========================================"
echo
echo "Debug App: build/Debug-iphonesimulator/Panel.app"
echo "Archive: build/Panel.xcarchive"
echo
echo "To run on simulator:"
echo "  xcrun simctl boot 'iPhone 15 Pro'"
echo "  xcrun simctl install booted build/Debug-iphonesimulator/Panel.app"
echo "  xcrun simctl launch booted com.panel.app"
echo