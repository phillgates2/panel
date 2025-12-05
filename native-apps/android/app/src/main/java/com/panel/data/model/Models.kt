// native-apps/android/app/src/main/java/com/panel/data/model/Server.kt

package com.panel.app.data.model

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.google.gson.annotations.SerializedName

@Entity(tableName = "servers")
data class Server(
    @PrimaryKey
    @SerializedName("id")
    val id: String,
    
    @SerializedName("name")
    val name: String,
    
    @SerializedName("game_type")
    val gameType: String,
    
    @SerializedName("status")
    val status: String,
    
    @SerializedName("player_count")
    val playerCount: Int,
    
    @SerializedName("max_players")
    val maxPlayers: Int,
    
    @SerializedName("cpu_usage")
    val cpuUsage: Float,
    
    @SerializedName("memory_usage")
    val memoryUsage: Float,
    
    @SerializedName("ip_address")
    val ipAddress: String,
    
    @SerializedName("region")
    val region: String? = null,
    
    @SerializedName("created_at")
    val createdAt: Long? = null
)

data class DashboardStats(
    @SerializedName("total_servers")
    val totalServers: Int,
    
    @SerializedName("active_servers")
    val activeServers: Int,
    
    @SerializedName("total_players")
    val totalPlayers: Int,
    
    @SerializedName("avg_cpu_usage")
    val avgCpuUsage: Float,
    
    @SerializedName("avg_memory_usage")
    val avgMemoryUsage: Float
)

data class ServerAlert(
    @SerializedName("id")
    val id: String,
    
    @SerializedName("title")
    val title: String,
    
    @SerializedName("message")
    val message: String,
    
    @SerializedName("severity")
    val severity: String,
    
    @SerializedName("timestamp")
    val timestamp: String,
    
    @SerializedName("server_id")
    val serverId: String? = null
)

data class AnalyticsData(
    @SerializedName("avg_cpu_usage")
    val avgCpuUsage: Float?,
    
    @SerializedName("avg_memory_usage")
    val avgMemoryUsage: Float?,
    
    @SerializedName("performance_history")
    val performanceHistory: List<Float>?,
    
    @SerializedName("alerts")
    val alerts: List<ServerAlert>?
)