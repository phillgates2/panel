# Panel Native Apps - Build Instructions

## ?? Quick Start Guide

This guide will help you build and run both the Android and iOS native applications.

## ?? Android Build Instructions

### Prerequisites
1. **Install Android Studio**
   - Download from: https://developer.android.com/studio
   - Version: Hedgehog (2023.1.1) or later

2. **Install JDK 17**
   - Download from: https://adoptium.net/
   - Or use Android Studio's embedded JDK

3. **Configure Android SDK**
   - Open Android Studio
   - Go to Tools > SDK Manager
   - Install:
     - Android SDK Platform 34
     - Android SDK Build-Tools 34.0.0
     - Android Emulator
     - Android SDK Platform-Tools

### Build Steps

#### Option 1: Using Android Studio (Recommended)
```bash
1. Open Android Studio
2. Click "Open" and select: F:\repos\phillgates2\panel\native-apps\android
3. Wait for Gradle sync to complete (may take 5-10 minutes first time)
4. Click the "Run" button (green play icon) or press Shift+F10
5. Select a device (emulator or physical device)
```

#### Option 2: Using Command Line
```bash
cd F:\repos\phillgates2\panel\native-apps\android

# Clean and build
gradlew.bat clean build

# Install debug build on connected device
gradlew.bat installDebug

# Run on device
adb shell am start -n com.panel.app/.MainActivity
```

### Create Release Build
```bash
cd F:\repos\phillgates2\panel\native-apps\android

# Generate signed APK
gradlew.bat assembleRelease

# Generate App Bundle (recommended for Play Store)
gradlew.bat bundleRelease

# Output locations:
# APK: app/build/outputs/apk/release/app-release.apk
# AAB: app/build/outputs/bundle/release/app-release.aab
```

### Common Issues & Solutions

#### Issue: "SDK location not found"
**Solution**: Create `local.properties` file in android/ directory:
```properties
sdk.dir=C\:\\Users\\YourUsername\\AppData\\Local\\Android\\Sdk
```

#### Issue: "Unsupported Java version"
**Solution**: Set JAVA_HOME to JDK 17
```bash
# Windows
set JAVA_HOME=C:\Program Files\Java\jdk-17
set PATH=%JAVA_HOME%\bin;%PATH%
```

#### Issue: Gradle sync fails
**Solution**: Delete `.gradle` folder and rebuild:
```bash
cd native-apps/android
rmdir /s /q .gradle
gradlew.bat clean build
```

## ?? iOS Build Instructions

### Prerequisites
1. **macOS Required** - iOS development requires a Mac computer

2. **Install Xcode**
   - Download from Mac App Store
   - Version: 15.0 or later

3. **Install Xcode Command Line Tools**
```bash
xcode-select --install
```

4. **Install CocoaPods**
```bash
sudo gem install cocoapods
```

### Build Steps

#### Option 1: Using Xcode (Recommended)
```bash
1. Open Terminal and navigate to ios directory:
   cd F:\repos\phillgates2\panel\native-apps\ios

2. Install dependencies:
   pod install

3. Open workspace in Xcode:
   open Panel.xcworkspace

4. Select target device (iPhone simulator or connected device)

5. Press ?+R to build and run
```

#### Option 2: Using Command Line
```bash
cd F:\repos\phillgates2\panel\native-apps\ios

# Install dependencies
pod install

# Build for simulator
xcodebuild -workspace Panel.xcworkspace \
           -scheme Panel \
           -sdk iphonesimulator \
           -configuration Debug \
           build

# Run on simulator
xcrun simctl boot "iPhone 15 Pro"
xcrun simctl install booted build/Debug-iphonesimulator/Panel.app
xcrun simctl launch booted com.panel.app
```

### Create Release Build
```bash
# Archive for App Store
xcodebuild -workspace Panel.xcworkspace \
           -scheme Panel \
           -sdk iphoneos \
           -configuration Release \
           archive \
           -archivePath build/Panel.xcarchive

# Export IPA
xcodebuild -exportArchive \
           -archivePath build/Panel.xcarchive \
           -exportPath build/Panel-IPA \
           -exportOptionsPlist ExportOptions.plist
```

### Common Issues & Solutions

#### Issue: "Command not found: pod"
**Solution**: Install CocoaPods
```bash
sudo gem install cocoapods
pod setup
```

#### Issue: "Unable to boot device"
**Solution**: Reset simulator
```bash
xcrun simctl shutdown all
xcrun simctl erase all
```

#### Issue: Code signing error
**Solution**: Configure signing in Xcode
```
1. Select project in Xcode
2. Go to Signing & Capabilities
3. Check "Automatically manage signing"
4. Select your Team
```

## ?? Development Configuration

### Android Development
```gradle
// native-apps/android/local.properties
sdk.dir=C\:\\Users\\YourUsername\\AppData\\Local\\Android\\Sdk
api.base.url=http://10.0.2.2:5000
ws.url=ws://10.0.2.2:5000/ws
```

### iOS Development
```swift
// native-apps/ios/Panel/Config.xcconfig
API_BASE_URL = http:/$()/localhost:5000
WS_URL = ws:/$()/localhost:5000/ws
```

## ?? Build Outputs

### Android
- **Debug APK**: `android/app/build/outputs/apk/debug/app-debug.apk`
- **Release APK**: `android/app/build/outputs/apk/release/app-release.apk`
- **Release AAB**: `android/app/build/outputs/bundle/release/app-release.aab`

### iOS
- **Debug App**: `ios/build/Debug-iphonesimulator/Panel.app`
- **Archive**: `ios/build/Panel.xcarchive`
- **IPA**: `ios/build/Panel-IPA/Panel.ipa`

## ?? Running on Physical Devices

### Android Physical Device
1. Enable Developer Options on device:
   - Go to Settings > About Phone
   - Tap "Build Number" 7 times

2. Enable USB Debugging:
   - Go to Settings > Developer Options
   - Enable "USB Debugging"

3. Connect device via USB

4. Run:
```bash
gradlew.bat installDebug
```

### iOS Physical Device
1. Connect iPhone/iPad to Mac via USB

2. Trust the computer on device

3. In Xcode:
   - Select your device from device menu
   - Press ?+R to build and run

4. On device:
   - Go to Settings > General > VPN & Device Management
   - Trust your developer certificate

## ?? Testing

### Android Unit Tests
```bash
gradlew.bat test
gradlew.bat connectedAndroidTest
```

### iOS Unit Tests
```bash
xcodebuild test \
  -workspace Panel.xcworkspace \
  -scheme Panel \
  -destination 'platform=iOS Simulator,name=iPhone 15 Pro'
```

## ?? Performance Profiling

### Android
1. Open Android Studio
2. Run > Profile 'app'
3. Select CPU, Memory, or Network profiler

### iOS
1. Open Xcode
2. Product > Profile (?+I)
3. Select Instruments template (Time Profiler, Allocations, etc.)

## ?? Debugging

### Android Debug Logs
```bash
# View all logs
adb logcat

# Filter Panel app logs
adb logcat | findstr "Panel"

# Clear logs
adb logcat -c
```

### iOS Debug Logs
```bash
# In Xcode
View > Debug Area > Show Debug Area (?+Shift+Y)

# Or use Console.app on Mac
```

## ?? Deployment

### Android - Google Play Store
1. Generate signed AAB
2. Go to Google Play Console
3. Create new release
4. Upload AAB
5. Complete store listing
6. Submit for review

### iOS - App Store
1. Archive in Xcode
2. Open Organizer (Window > Organizer)
3. Click "Distribute App"
4. Select "App Store Connect"
5. Follow upload wizard
6. Go to App Store Connect
7. Complete app information
8. Submit for review

## ?? Additional Resources

- **Android Documentation**: https://developer.android.com/docs
- **iOS Documentation**: https://developer.apple.com/documentation/
- **Jetpack Compose**: https://developer.android.com/jetpack/compose
- **SwiftUI**: https://developer.apple.com/xcode/swiftui/
- **Material Design 3**: https://m3.material.io/
- **iOS Human Interface Guidelines**: https://developer.apple.com/design/human-interface-guidelines/

## ?? Tips for Success

### Android Tips
- Use Android Studio's Layout Inspector to debug UI
- Enable R8 minification for smaller APKs
- Use ProGuard rules to protect code
- Test on multiple screen sizes and Android versions
- Use Android Profiler to optimize performance

### iOS Tips
- Use Xcode Previews for rapid UI development
- Enable Instruments for performance analysis
- Test on multiple iOS versions and device sizes
- Use Swift Concurrency (async/await) for better performance
- Follow iOS accessibility guidelines

## ?? Continuous Integration

### Android CI (GitHub Actions)
```yaml
name: Android CI
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-java@v3
        with:
          java-version: '17'
      - run: cd native-apps/android && ./gradlew build
```

### iOS CI (GitHub Actions)
```yaml
name: iOS CI
on: [push, pull_request]
jobs:
  build:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3
      - run: cd native-apps/ios && pod install
      - run: xcodebuild build -workspace Panel.xcworkspace -scheme Panel
```

---

**Need Help?** Open an issue on GitHub or check the documentation!

?? **Happy Building!** ??