// native-apps/android/app/src/main/java/com/panel/viewmodel/DashboardViewModel.kt

package com.panel.app.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.panel.app.data.model.AnalyticsData
import com.panel.app.data.model.DashboardStats
import com.panel.app.data.model.Server
import com.panel.app.data.model.ServerAlert
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class DashboardUiState(
    val isLoading: Boolean = false,
    val stats: DashboardStats? = null,
    val performanceData: List<Float> = emptyList(),
    val alerts: List<ServerAlert> = emptyList(),
    val error: String? = null
)

@HiltViewModel
class DashboardViewModel @Inject constructor(
    // private val repository: DashboardRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(DashboardUiState())
    val uiState: StateFlow<DashboardUiState> = _uiState.asStateFlow()

    private val _isRefreshing = MutableStateFlow(false)
    val isRefreshing: StateFlow<Boolean> = _isRefreshing.asStateFlow()

    init {
        loadDashboard()
    }

    fun loadDashboard() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            
            try {
                // Mock data for demonstration
                val mockStats = DashboardStats(
                    totalServers = 15,
                    activeServers = 12,
                    totalPlayers = 350,
                    avgCpuUsage = 45.5f,
                    avgMemoryUsage = 62.3f
                )
                
                val mockPerformanceData = List(24) { (40..80).random().toFloat() }
                
                val mockAlerts = listOf(
                    ServerAlert(
                        id = "1",
                        title = "High CPU Usage",
                        message = "Server minecraft-01 CPU usage at 95%",
                        severity = "warning",
                        timestamp = System.currentTimeMillis().toString(),
                        serverId = "minecraft-01"
                    ),
                    ServerAlert(
                        id = "2",
                        title = "Server Restarted",
                        message = "Server rust-02 has been automatically restarted",
                        severity = "info",
                        timestamp = System.currentTimeMillis().toString(),
                        serverId = "rust-02"
                    )
                )
                
                _uiState.value = DashboardUiState(
                    isLoading = false,
                    stats = mockStats,
                    performanceData = mockPerformanceData,
                    alerts = mockAlerts
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = e.message
                )
            }
        }
    }

    fun refresh() {
        viewModelScope.launch {
            _isRefreshing.value = true
            loadDashboard()
            _isRefreshing.value = false
        }
    }
}