package de.correlcore.app.health

import androidx.activity.result.ActivityResult
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.PermissionController
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.HeartRateRecord
import androidx.health.connect.client.records.SleepSessionRecord
import androidx.health.connect.client.request.ReadRecordsRequest
import androidx.health.connect.client.time.TimeRangeFilter
import com.getcapacitor.JSArray
import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.ActivityCallback
import com.getcapacitor.annotation.CapacitorPlugin
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.time.Duration
import java.time.Instant

/**
 * Thin Health Connect bridge — M8 Sprint 3 (#172, ADR-0042).
 *
 * Reads **only** sleep sessions and heart-rate records. The read permission set
 * is fixed in [permissions], so the WebView can never widen it to movement or
 * location data (data-minimization is technically enforced here, not just in UI).
 * The web layer additionally gates every call behind the DSGVO Art. 9 consent
 * (`canUseHealthConnectImport`). Writing imported values into entries is Sprint 4.
 */
@CapacitorPlugin(name = "HealthConnect")
class HealthConnectPlugin : Plugin() {

    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())

    private val permissions = setOf(
        HealthPermission.getReadPermission(SleepSessionRecord::class),
        HealthPermission.getReadPermission(HeartRateRecord::class),
    )

    private fun sdkStatus(): Int {
        val ctx = context ?: return HealthConnectClient.SDK_UNAVAILABLE
        return HealthConnectClient.getSdkStatus(ctx)
    }

    private fun clientOrNull(): HealthConnectClient? {
        val ctx = context ?: return null
        return if (HealthConnectClient.getSdkStatus(ctx) == HealthConnectClient.SDK_AVAILABLE) {
            HealthConnectClient.getOrCreate(ctx)
        } else {
            null
        }
    }

    @PluginMethod
    fun isAvailable(call: PluginCall) {
        val status = sdkStatus()
        val result = JSObject()
        result.put("available", status == HealthConnectClient.SDK_AVAILABLE)
        result.put("status", status)
        call.resolve(result)
    }

    @PluginMethod
    fun checkPermissions(call: PluginCall) {
        val client = clientOrNull()
        if (client == null) {
            call.resolve(JSObject().put("granted", false).put("available", false))
            return
        }
        scope.launch {
            try {
                val granted = withContext(Dispatchers.IO) {
                    client.permissionController.getGrantedPermissions()
                }
                call.resolve(
                    JSObject()
                        .put("granted", granted.containsAll(permissions))
                        .put("available", true),
                )
            } catch (e: Exception) {
                call.reject("check_permissions_failed", e)
            }
        }
    }

    @PluginMethod
    fun requestPermissions(call: PluginCall) {
        if (sdkStatus() != HealthConnectClient.SDK_AVAILABLE) {
            call.reject("health_connect_unavailable")
            return
        }
        val ctx = context ?: return call.reject("health_connect_unavailable")
        val contract = PermissionController.createRequestPermissionResultContract()
        val intent = contract.createIntent(ctx, permissions)
        startActivityForResult(call, intent, "onPermissionResult")
    }

    @ActivityCallback
    private fun onPermissionResult(call: PluginCall?, result: ActivityResult) {
        if (call == null) return
        val client = clientOrNull()
        if (client == null) {
            call.resolve(JSObject().put("granted", false).put("available", false))
            return
        }
        scope.launch {
            try {
                val granted = withContext(Dispatchers.IO) {
                    client.permissionController.getGrantedPermissions()
                }
                call.resolve(
                    JSObject()
                        .put("granted", granted.containsAll(permissions))
                        .put("available", true),
                )
            } catch (e: Exception) {
                call.reject("check_permissions_failed", e)
            }
        }
    }

    @PluginMethod
    fun readSleepAndHeartRate(call: PluginCall) {
        val client = clientOrNull()
        if (client == null) {
            call.reject("health_connect_unavailable")
            return
        }
        val start = parseInstant(call.getString("start"))
        val end = parseInstant(call.getString("end"))
        if (start == null || end == null) {
            call.reject("invalid_time_range")
            return
        }
        scope.launch {
            try {
                val filter = TimeRangeFilter.between(start, end)
                val sleepRecords = withContext(Dispatchers.IO) {
                    client.readRecords(ReadRecordsRequest(SleepSessionRecord::class, filter)).records
                }
                val heartRecords = withContext(Dispatchers.IO) {
                    client.readRecords(ReadRecordsRequest(HeartRateRecord::class, filter)).records
                }

                val sleep = JSArray()
                for (record in sleepRecords) {
                    sleep.put(
                        JSObject()
                            .put("startTime", record.startTime.toString())
                            .put("endTime", record.endTime.toString())
                            .put(
                                "durationMinutes",
                                Duration.between(record.startTime, record.endTime).toMinutes(),
                            ),
                    )
                }

                val heartRate = JSArray()
                for (record in heartRecords) {
                    val bpm = record.samples.map { it.beatsPerMinute }
                    val obj = JSObject()
                        .put("startTime", record.startTime.toString())
                        .put("endTime", record.endTime.toString())
                        .put("sampleCount", bpm.size)
                    if (bpm.isNotEmpty()) {
                        obj.put("avgBpm", bpm.average())
                        obj.put("minBpm", bpm.minOrNull())
                        obj.put("maxBpm", bpm.maxOrNull())
                    }
                    heartRate.put(obj)
                }

                call.resolve(JSObject().put("sleep", sleep).put("heartRate", heartRate))
            } catch (e: Exception) {
                call.reject("read_failed", e)
            }
        }
    }

    private fun parseInstant(value: String?): Instant? {
        if (value.isNullOrBlank()) return null
        return try {
            Instant.parse(value)
        } catch (e: Exception) {
            null
        }
    }
}
