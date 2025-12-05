// native-apps/android/app/src/main/java/com/panel/PanelApplication.kt

package com.panel.app

import android.app.Application
import dagger.hilt.android.HiltAndroidApp
import timber.log.Timber

@HiltAndroidApp
class PanelApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        
        // Initialize Timber for logging
        if (BuildConfig.DEBUG) {
            Timber.plant(Timber.DebugTree())
        }
        
        Timber.d("Panel Application initialized")
    }
}