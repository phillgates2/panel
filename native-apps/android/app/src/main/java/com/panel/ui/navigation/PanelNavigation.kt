// native-apps/android/app/src/main/java/com/panel/ui/navigation/PanelNavigation.kt

package com.panel.app.ui.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import com.panel.app.ui.screens.DashboardScreen

sealed class Screen(val route: String) {
    object Dashboard : Screen("dashboard")
    object Servers : Screen("servers")
    object Analytics : Screen("analytics")
    object Plugins : Screen("plugins")
    object Settings : Screen("settings")
}

@Composable
fun PanelNavigation(navController: NavHostController) {
    NavHost(
        navController = navController,
        startDestination = Screen.Dashboard.route
    ) {
        composable(Screen.Dashboard.route) {
            DashboardScreen(
                onNavigateToServers = { navController.navigate(Screen.Servers.route) },
                onNavigateToAnalytics = { navController.navigate(Screen.Analytics.route) },
                onNavigateToPlugins = { navController.navigate(Screen.Plugins.route) },
                onNavigateToSettings = { navController.navigate(Screen.Settings.route) }
            )
        }
        
        composable(Screen.Servers.route) {
            // ServersScreen()
        }
        
        composable(Screen.Analytics.route) {
            // AnalyticsScreen()
        }
        
        composable(Screen.Plugins.route) {
            // PluginsScreen()
        }
        
        composable(Screen.Settings.route) {
            // SettingsScreen()
        }
    }
}