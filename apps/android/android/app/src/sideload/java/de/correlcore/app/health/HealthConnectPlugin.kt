package de.correlcore.app.health

import android.annotation.SuppressLint
import androidx.activity.result.ActivityResult
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.PermissionController
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.HeartRateRecord
import androidx.health.connect.client.records.Record
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
import kotlin.reflect.KClass

/**
 * Thin Health Connect bridge — M8 Sprint 3 (#172, ADR-0042).
 *
 * Reads **only** sleep sessions and heart-rate records. The read permission set
 * is fixed in [permissions], so the WebView can never widen it to movement or
 * location data (data-minimization is technically enforced here, not just in UI).
 * The web layer additionally gates every call behind the DSGVO Art. 9 consent
 * (`canUseHealthConnectImport`). Writing imported values into entries is Sprint 4.
 */
// java.time (Instant/Duration) and the Health Connect client need API 26+.
// Every entry point here is gated behind HealthConnectClient.getSdkStatus() ==
// SDK_AVAILABLE, which is only true on API 26+ (Health Connect does not exist on
// 24–25), so the java.time code never runs on the app's minSdk-24 floor. The
// NewApi lint (build.gradle) is therefore suppressed for this HC-only class.
@SuppressLint("NewApi")
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

    // Named *HealthPermissions to avoid clashing with Capacitor Plugin's built-in
    // checkPermissions/requestPermissions (we don't use its permission-alias system).
    @PluginMethod
    fun checkHealthPermissions(call: PluginCall) {
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
    fun requestHealthPermissions(call: PluginCall) {
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

    /**
     * Sleep-only read for Sync now. Avoids coupling the import path to heart-rate
     * reads (OEM/SecurityException on HR must not fail sleep sync).
     */
    @PluginMethod
    fun readSleepSessions(call: PluginCall) {
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
                    readAllRecords(client, SleepSessionRecord::class, filter)
                }
                call.resolve(JSObject().put("sleep", sleepSessionsToJs(sleepRecords)))
            } catch (e: Exception) {
                call.reject("read_failed", e)
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
                    readAllRecords(client, SleepSessionRecord::class, filter)
                }
                val heartRecords = withContext(Dispatchers.IO) {
                    readAllRecords(client, HeartRateRecord::class, filter)
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

                call.resolve(
                    JSObject()
                        .put("sleep", sleepSessionsToJs(sleepRecords))
                        .put("heartRate", heartRate),
                )
            } catch (e: Exception) {
                call.reject("read_failed", e)
            }
        }
    }

    private fun sleepSessionsToJs(records: List<SleepSessionRecord>): JSArray {
        val sleep = JSArray()
        for (record in records) {
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
        return sleep
    }

    /**
     * Health Connect paginates large result sets; a single [HealthConnectClient.readRecords]
     * call only returns one page and silently drops the rest. Follow [ReadRecordsResponse.pageToken]
     * until it is exhausted so wide date ranges don't produce truncated sleep/heart-rate data.
     */
    private suspend fun <T : Record> readAllRecords(
        client: HealthConnectClient,
        recordType: KClass<T>,
        filter: TimeRangeFilter,
    ): List<T> {
        val records = mutableListOf<T>()
        var pageToken: String? = null
        do {
            val response = client.readRecords(
                ReadRecordsRequest(recordType, filter, pageToken = pageToken),
            )
            records.addAll(response.records)
            pageToken = response.pageToken
        } while (!pageToken.isNullOrEmpty())
        return records
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
