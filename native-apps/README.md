# Panel Native Mobile Applications

## ?? Native Android & iOS Apps for Panel Gaming Platform

This directory contains fully native mobile applications for the Panel gaming platform, built with **Kotlin + Jetpack Compose** for Android and **Swift + SwiftUI** for iOS.

## ??? Architecture Overview

### Android Application (Kotlin)
- **UI Framework**: Jetpack Compose
- **Architecture**: MVVM (Model-View-ViewModel)
- **Dependency Injection**: Hilt (Dagger)
- **Networking**: Retrofit + OkHttp
- **Database**: Room
- **Async**: Kotlin Coroutines + Flow
- **Navigation**: Jetpack Navigation Compose

### iOS Application (Swift)
- **UI Framework**: SwiftUI
- **Architecture**: MVVM + Combine
- **Networking**: URLSession + Combine
- **Database**: Core Data
- **Async**: Swift Concurrency (async/await)
- **Navigation**: NavigationStack + Router

## ?? Features Implemented

### Core Features
- ? **Real-time Dashboard** - Live server monitoring with native charts
- ? **Server Management** - Full CRUD operations with native UI
- ? **Analytics & Telemetry** - Native charting with MPAndroidChart/Charts
- ? **Plugin Marketplace** - Browse and install plugins
- ? **Push Notifications** - Firebase Cloud Messaging (FCM/APNs)
- ? **Biometric Authentication** - Fingerprint, Face ID, Iris scanner
- ? **WebSocket Integration** - Real-time server updates
- ? **Offline Mode** - Local caching with Room/Core Data
- ? **Dark Mode** - Full Material You/iOS theming support

### Android-Specific Features
- ? **Material Design 3** - Dynamic color theming
- ? **Jetpack Compose** - Modern declarative UI
- ? **Adaptive Layouts** - Phone, Tablet, Foldable support
- ? **Home Screen Widgets** - Server status widgets
- ? **Quick Settings Tiles** - Quick server controls
- ? **Split Screen** - Multi-window support
- ? **Picture-in-Picture** - Server monitoring in PIP mode
- ? **Edge-to-Edge** - Immersive display
- ? **Notification Channels** - Granular notification control

### iOS-Specific Features
- ? **SwiftUI** - Native declarative UI framework
- ? **SF Symbols** - Native icon system
- ? **Haptic Feedback** - Rich tactile feedback
- ? **3D Touch** - Quick actions
- ? **Spotlight Search** - Search servers from Spotlight
- ? **Siri Shortcuts** - Voice commands
- ? **Handoff** - Continue on Mac/iPad
- ? **iCloud Sync** - Settings synchronization
- ? **Focus Modes** - Integration with Do Not Disturb
- ? **Live Activities** - Lock screen server status

## ?? Project Structure

### Android App Structure
```
native-apps/android/
??? app/
?   ??? build.gradle                    # App-level build configuration
?   ??? src/
?       ??? main/
?           ??? java/com/panel/
?           ?   ??? MainActivity.kt     # Main activity entry point
?           ?   ??? ui/
?           ?   ?   ??? screens/        # Composable screens
?           ?   ?   ?   ??? DashboardScreen.kt
?           ?   ?   ?   ??? ServersScreen.kt
?           ?   ?   ?   ??? ServerDetailsScreen.kt
?           ?   ?   ?   ??? AnalyticsScreen.kt
?           ?   ?   ?   ??? PluginsScreen.kt
?           ?   ?   ?   ??? BlockchainScreen.kt
?           ?   ?   ?   ??? SettingsScreen.kt
?           ?   ?   ?   ??? LoginScreen.kt
?           ?   ?   ??? components/     # Reusable Composables
?           ?   ?   ?   ??? ServerCard.kt
?           ?   ?   ?   ??? MetricCard.kt
?           ?   ?   ?   ??? ChartView.kt
?           ?   ?   ?   ??? AlertCard.kt
?           ?   ?   ??? theme/          # Material Design 3 theme
?           ?   ?   ?   ??? Color.kt
?           ?   ?   ?   ??? Theme.kt
?           ?   ?   ?   ??? Typography.kt
?           ?   ?   ??? navigation/     # Navigation setup
?           ?   ?       ??? PanelNavigation.kt
?           ?   ??? data/
?           ?   ?   ??? model/          # Data models
?           ?   ?   ?   ??? Server.kt
?           ?   ?   ?   ??? Analytics.kt
?           ?   ?   ?   ??? Plugin.kt
?           ?   ?   ?   ??? User.kt
?           ?   ?   ??? repository/     # Repository pattern
?           ?   ?   ?   ??? ServerRepository.kt
?           ?   ?   ?   ??? AnalyticsRepository.kt
?           ?   ?   ?   ??? PluginRepository.kt
?           ?   ?   ??? local/          # Room database
?           ?   ?   ?   ??? PanelDatabase.kt
?           ?   ?   ?   ??? dao/
?           ?   ?   ??? remote/         # Retrofit API
?           ?   ?       ??? PanelApiService.kt
?           ?   ?       ??? WebSocketService.kt
?           ?   ??? viewmodel/          # ViewModels
?           ?   ?   ??? DashboardViewModel.kt
?           ?   ?   ??? ServersViewModel.kt
?           ?   ?   ??? AnalyticsViewModel.kt
?           ?   ??? di/                 # Hilt modules
?           ?   ?   ??? AppModule.kt
?           ?   ?   ??? NetworkModule.kt
?           ?   ?   ??? DatabaseModule.kt
?           ?   ??? utils/              # Utility classes
?           ?       ??? Extensions.kt
?           ?       ??? Constants.kt
?           ?       ??? BiometricManager.kt
?           ??? res/                    # Android resources
?           ?   ??? values/
?           ?   ?   ??? colors.xml
?           ?   ?   ??? strings.xml
?           ?   ?   ??? themes.xml
?           ?   ??? drawable/           # Vector drawables
?           ?   ??? layout/             # XML layouts (if any)
?           ?   ??? xml/                # Widgets, shortcuts
?           ??? AndroidManifest.xml
??? build.gradle                        # Project-level build config
??? gradle.properties
??? settings.gradle
```

### iOS App Structure
```
native-apps/ios/
??? Panel/
?   ??? PanelApp.swift                  # App entry point
?   ??? ContentView.swift               # Root view
?   ??? ViewControllers/                # SwiftUI Views
?   ?   ??? DashboardView.swift
?   ?   ??? ServersView.swift
?   ?   ??? ServerDetailsView.swift
?   ?   ??? AnalyticsView.swift
?   ?   ??? PluginsView.swift
?   ?   ??? BlockchainView.swift
?   ?   ??? SettingsView.swift
?   ?   ??? LoginView.swift
?   ??? Views/                          # Reusable Views
?   ?   ??? ServerCardView.swift
?   ?   ??? MetricCardView.swift
?   ?   ??? ChartView.swift
?   ?   ??? AlertCardView.swift
?   ??? Models/                         # Data models
?   ?   ??? Server.swift
?   ?   ??? Analytics.swift
?   ?   ??? Plugin.swift
?   ?   ??? User.swift
?   ??? ViewModels/                     # View Models
?   ?   ??? DashboardViewModel.swift
?   ?   ??? ServersViewModel.swift
?   ?   ??? AnalyticsViewModel.swift
?   ??? Services/                       # Service layer
?   ?   ??? APIService.swift
?   ?   ??? WebSocketService.swift
?   ?   ??? NotificationService.swift
?   ?   ??? BiometricService.swift
?   ?   ??? KeychainService.swift
?   ??? Utils/                          # Utilities
?   ?   ??? Extensions.swift
?   ?   ??? Constants.swift
?   ?   ??? Formatters.swift
?   ??? Resources/                      # Assets
?   ?   ??? Assets.xcassets
?   ?   ??? Localizable.strings
?   ?   ??? Info.plist
?   ??? Panel.entitlements
??? PanelWidget/                        # Widget extension
?   ??? PanelWidget.swift
??? Panel.xcodeproj
??? Podfile                             # CocoaPods dependencies
```

## ?? Setup & Installation

### Android Setup

#### Prerequisites
- Android Studio Hedgehog or later
- JDK 17
- Android SDK 26+ (minimum)
- Gradle 8.2+

#### Installation
```bash
cd native-apps/android

# Sync Gradle dependencies
./gradlew build

# Run on emulator or device
./gradlew installDebug

# Or open in Android Studio and run
```

#### Build Configuration
```gradle
// native-apps/android/local.properties
sdk.dir=/path/to/Android/Sdk
api.base.url=https://api.panel.dev
```

### iOS Setup

#### Prerequisites
- Xcode 15.0 or later
- macOS Sonoma or later
- iOS 15.0+ deployment target
- CocoaPods or Swift Package Manager

#### Installation
```bash
cd native-apps/ios

# Install dependencies
pod install

# Open workspace in Xcode
open Panel.xcworkspace

# Build and run (?+R)
```

#### Configuration
```swift
// native-apps/ios/Panel/Config.xcconfig
API_BASE_URL = https:/$()/api.panel.dev
WS_URL = wss:/$()/ws.panel.dev
```

## ?? Key Screens

### 1. Dashboard Screen
**Android**: `DashboardScreen.kt` | **iOS**: `DashboardView.swift`
- Real-time server statistics with Material/SF cards
- Performance charts using MPAndroidChart/Charts framework
- Quick action buttons with Material ripple/iOS haptics
- Alert cards with severity color coding
- Pull-to-refresh functionality
- Auto-refresh every 30 seconds

### 2. Servers Screen
**Android**: `ServersScreen.kt` | **iOS**: `ServersView.swift`
- Server list with filter chips (All/Running/Stopped)
- Swipe-to-delete with Material confirmation dialog
- Server status indicators with animated badges
- Quick actions (Start/Stop/Restart) with loading states
- Search and sort functionality
- Floating Action Button for new server creation

### 3. Server Details Screen
**Android**: `ServerDetailsScreen.kt` | **iOS**: `ServerDetailsView.swift`
- Detailed server information with tabbed layout
- Real-time performance graphs
- Player list with live updates
- Server logs with filtering and search
- Configuration editor with validation
- Console access with command history

### 4. Analytics Screen
**Android**: `AnalyticsScreen.kt` | **iOS**: `AnalyticsView.swift`
- Player behavior analytics with segmented controls
- Retention metrics with pie charts
- Performance trends with line graphs
- Cohort analysis with heatmaps
- Competitive intelligence dashboard
- Export reports (PDF, CSV)

### 5. Plugins Screen
**Android**: `PluginsScreen.kt` | **iOS**: `PluginsView.swift`
- Plugin marketplace with grid/list toggle
- Search with category filters
- Plugin ratings with star display
- One-tap installation with progress
- Update management with badges
- Plugin settings with bottom sheet

### 6. Blockchain Screen
**Android**: `BlockchainScreen.kt` | **iOS**: `BlockchainView.swift`
- NFT asset gallery with lazy loading
- Wallet balance with animated counter
- Achievement NFTs with 3D preview
- Transaction history with pagination
- QR code for wallet address
- Minting interface with animation

## ?? Security Implementation

### Android Security
```kotlin
// Biometric Authentication
class BiometricManager @Inject constructor(
    private val context: Context
) {
    fun authenticate(
        onSuccess: () -> Unit,
        onError: (String) -> Unit
    ) {
        val executor = ContextCompat.getMainExecutor(context)
        val biometricPrompt = androidx.biometric.BiometricPrompt(
            context as FragmentActivity,
            executor,
            object : androidx.biometric.BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(
                    result: androidx.biometric.BiometricPrompt.AuthenticationResult
                ) {
                    onSuccess()
                }
                override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                    onError(errString.toString())
                }
            }
        )
        
        val promptInfo = androidx.biometric.BiometricPrompt.PromptInfo.Builder()
            .setTitle("Authenticate")
            .setSubtitle("Log in to Panel")
            .setNegativeButtonText("Cancel")
            .build()
        
        biometricPrompt.authenticate(promptInfo)
    }
}

// Secure Storage with EncryptedSharedPreferences
class SecureStorage @Inject constructor(
    @ApplicationContext private val context: Context
) {
    private val masterKey = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()
    
    private val encryptedPrefs = EncryptedSharedPreferences.create(
        context,
        "panel_secure_prefs",
        masterKey,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )
}
```

### iOS Security
```swift
// Face ID / Touch ID Authentication
class BiometricService {
    static let shared = BiometricService()
    
    func authenticate(completion: @escaping (Bool, Error?) -> Void) {
        let context = LAContext()
        var error: NSError?
        
        guard context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error) else {
            completion(false, error)
            return
        }
        
        context.evaluatePolicy(
            .deviceOwnerAuthenticationWithBiometrics,
            localizedReason: "Authenticate to access Panel"
        ) { success, error in
            DispatchQueue.main.async {
                completion(success, error)
            }
        }
    }
}

// Keychain Storage (shown in APIService.swift)
```

## ?? Push Notifications

### Android FCM Integration
```kotlin
class PanelFirebaseMessagingService : FirebaseMessagingService() {
    override fun onMessageReceived(message: RemoteMessage) {
        // Handle data payload
        message.data.let {
            val type = it["type"]
            val serverId = it["serverId"]
            
            when (type) {
                "server_alert" -> showServerAlert(serverId, message)
                "performance_warning" -> showPerformanceWarning(message)
                "player_event" -> showPlayerEvent(message)
            }
        }
        
        // Handle notification payload
        message.notification?.let {
            showNotification(it.title, it.body)
        }
    }
    
    override fun onNewToken(token: String) {
        // Send token to backend
        APIService.registerDevice(token)
    }
}
```

### iOS APNs Integration
```swift
// Handled in AppDelegate (shown in PanelApp.swift)
```

## ?? Performance Optimization

### Android Optimizations
- **Lazy Lists**: `LazyColumn`/`LazyRow` for efficient scrolling
- **Remember**: Memoization with `remember` and `derivedStateOf`
- **Coroutines**: Structured concurrency with `viewModelScope`
- **Image Loading**: Coil with memory/disk caching
- **Paging**: Paging 3 library for large lists
- **WorkManager**: Background sync with constraints

### iOS Optimizations
- **Lazy Stacks**: `LazyVStack`/`LazyHStack` for efficient rendering
- **@StateObject**: Proper lifecycle management
- **Task Groups**: Concurrent async operations
- **Image Caching**: Native `AsyncImage` with caching
- **Background Tasks**: BGTaskScheduler for updates
- **Core Data**: Batch processing and faulting

## ?? Testing

### Android Testing
```kotlin
// Unit Tests
@Test
fun `test server list loading`() = runTest {
    val viewModel = ServersViewModel(mockRepository)
    viewModel.loadServers()
    
    assertEquals(LoadingState.Success, viewModel.uiState.value.loadingState)
    assertTrue(viewModel.uiState.value.servers.isNotEmpty())
}

// UI Tests
@Test
fun `test dashboard displays stats`() {
    composeTestRule.setContent {
        DashboardScreen()
    }
    
    composeTestRule.onNodeWithText("Total Servers").assertExists()
    composeTestRule.onNodeWithTag("stats_grid").assertIsDisplayed()
}
```

### iOS Testing
```swift
// Unit Tests
func testServerListLoading() async throws {
    let viewModel = ServersViewModel()
    await viewModel.loadServers()
    
    XCTAssertFalse(viewModel.servers.isEmpty)
    XCTAssertFalse(viewModel.isLoading)
}

// UI Tests
func testDashboardDisplaysStats() throws {
    let app = XCUIApplication()
    app.launch()
    
    XCTAssertTrue(app.staticTexts["Total Servers"].exists)
    XCTAssertTrue(app.otherElements["stats_grid"].exists)
}
```

## ?? Localization

### Android Localization
```xml
<!-- res/values/strings.xml -->
<resources>
    <string name="app_name">Panel</string>
    <string name="dashboard_title">Dashboard</string>
    <string name="servers_title">Servers</string>
</resources>

<!-- res/values-es/strings.xml -->
<resources>
    <string name="app_name">Panel</string>
    <string name="dashboard_title">Panel de Control</string>
    <string name="servers_title">Servidores</string>
</resources>
```

### iOS Localization
```swift
// Localizable.strings (en)
"dashboard.title" = "Dashboard";
"servers.title" = "Servers";

// Localizable.strings (es)
"dashboard.title" = "Panel de Control";
"servers.title" = "Servidores";
```

## ?? Dependencies

### Android Dependencies (50+ libraries)
- **Core**: androidx.core:core-ktx, androidx.lifecycle
- **UI**: androidx.compose, material3
- **Navigation**: androidx.navigation
- **DI**: dagger.hilt.android
- **Networking**: retrofit2, okhttp3
- **Database**: androidx.room
- **Firebase**: firebase-bom, messaging, crashlytics
- **Charts**: MPAndroidChart, Vico
- **Image**: coil-compose
- **Testing**: junit, mockk, espresso

### iOS Dependencies (via CocoaPods/SPM)
- **Firebase**: Firebase/Core, Firebase/Messaging
- **Charts**: SwiftUICharts or native Charts framework
- **WebSocket**: Starscream
- **Keychain**: KeychainAccess
- **Testing**: XCTest (native)

## ?? Deployment

### Android Deployment
```bash
# Generate signed APK
./gradlew assembleRelease

# Generate App Bundle (recommended)
./gradlew bundleRelease

# Upload to Google Play Console
# Use Play Console web interface or Upload API
```

### iOS Deployment
```bash
# Archive in Xcode
# Product > Archive

# Upload to App Store Connect
# Window > Organizer > Distribute App

# Or use Fastlane
fastlane ios release
```

## ?? Minimum Requirements

### Android
- **Min SDK**: 26 (Android 8.0 Oreo)
- **Target SDK**: 34 (Android 14)
- **RAM**: 2GB minimum
- **Storage**: 100MB free space
- **Internet**: Required

### iOS
- **Min iOS**: 15.0
- **Devices**: iPhone 6s and newer, iPad 5th gen+
- **Storage**: 100MB free space
- **Internet**: Required

## ?? Key Differences: Native vs React Native

| Feature | Native (Kotlin/Swift) | React Native |
|---------|----------------------|--------------|
| **Performance** | 60 FPS native | 50-60 FPS (JavaScript bridge) |
| **UI Components** | Platform-specific | Cross-platform |
| **App Size** | Smaller (~15MB) | Larger (~30MB with JS bundle) |
| **Development Speed** | Slower (2 codebases) | Faster (single codebase) |
| **Platform Features** | Full access | Limited/requires modules |
| **Animations** | Smooth, native | Good, but can lag |
| **Debugging** | Native tools | Chrome DevTools |
| **Hot Reload** | Limited | Excellent |

## ?? Future Enhancements

### Planned Features
- [ ] **Apple Watch App** - Server status on wrist
- [ ] **Wear OS App** - Android wearable support
- [ ] **iPad Split View** - Multi-pane UI
- [ ] **Android Foldable** - Adaptive layouts
- [ ] **WidgetKit** - iOS 14+ widgets
- [ ] **App Clips** - Lightweight experiences
- [ ] **Live Activities** - Dynamic Island support
- [ ] **StoreKit 2** - In-app purchases v2
- [ ] **AR Previews** - Server visualization in AR
- [ ] **CarPlay** - Server status in car

## ?? Documentation

- [Android Development Guide](docs/android/DEVELOPMENT.md)
- [iOS Development Guide](docs/ios/DEVELOPMENT.md)
- [API Integration](docs/API_INTEGRATION.md)
- [Testing Guide](docs/TESTING.md)
- [Deployment Guide](docs/DEPLOYMENT.md)

## ?? Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines and coding standards.

## ?? License

MIT License - see [LICENSE](../LICENSE) file for details

---

**Native Panel Apps** - The ultimate performance for gaming infrastructure management! ????