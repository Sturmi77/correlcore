package de.correlcore.app.widget

import android.content.Context
import androidx.glance.appwidget.updateAll
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.TimeUnit

/**
 * Battery-aware poll of GET /api/v1/widget/summary (15-minute periodic).
 *
 * On 401/403, attempts POST /auth/refresh?include_access_token=true with the
 * mirrored refresh token before signing the widget out.
 */
class WidgetRefreshWorker(
    appContext: Context,
    params: WorkerParameters,
) : CoroutineWorker(appContext, params) {
    override suspend fun doWork(): Result =
        withContext(Dispatchers.IO) {
            val creds = WidgetCredentialsStore.getCredentials(applicationContext)
            if (creds == null) {
                WidgetCredentialsStore.setStatus(
                    applicationContext,
                    WidgetCredentialsStore.STATUS_SIGNED_OUT,
                )
                CorrelCoreWidget().updateAll(applicationContext)
                return@withContext Result.success()
            }

            WidgetCredentialsStore.setStatus(
                applicationContext,
                WidgetCredentialsStore.STATUS_LOADING,
            )

            try {
                var accessToken = creds.accessToken
                var refreshToken = creds.refreshToken
                var summary = fetchSummary(creds.apiBase, accessToken)

                if (summary is SummaryResult.Unauthorized) {
                    val rotated = refreshAccessToken(creds.apiBase, refreshToken)
                    if (rotated == null) {
                        WidgetCredentialsStore.clearCredentials(applicationContext)
                        CorrelCoreWidget().updateAll(applicationContext)
                        return@withContext Result.success()
                    }
                    accessToken = rotated.accessToken
                    refreshToken = rotated.refreshToken
                    WidgetCredentialsStore.setCredentials(
                        applicationContext,
                        accessToken,
                        refreshToken,
                        creds.apiBase,
                    )
                    summary = fetchSummary(creds.apiBase, accessToken)
                }

                when (summary) {
                    is SummaryResult.Unauthorized -> {
                        WidgetCredentialsStore.clearCredentials(applicationContext)
                        CorrelCoreWidget().updateAll(applicationContext)
                        Result.success()
                    }
                    is SummaryResult.HttpError -> {
                        WidgetCredentialsStore.setStatus(
                            applicationContext,
                            WidgetCredentialsStore.STATUS_ERROR,
                        )
                        CorrelCoreWidget().updateAll(applicationContext)
                        Result.retry()
                    }
                    is SummaryResult.Ok -> {
                        WidgetCredentialsStore.saveSummary(
                            applicationContext,
                            hasEntry = summary.hasEntry,
                            moodAvg7d = summary.moodAvg7d,
                            suggestedNextEntryAt = summary.suggestedNextEntryAt,
                            status = WidgetCredentialsStore.STATUS_OK,
                        )
                        CorrelCoreWidget().updateAll(applicationContext)
                        Result.success()
                    }
                }
            } catch (_: Exception) {
                WidgetCredentialsStore.setStatus(
                    applicationContext,
                    WidgetCredentialsStore.STATUS_ERROR,
                )
                CorrelCoreWidget().updateAll(applicationContext)
                Result.retry()
            }
        }

    private sealed class SummaryResult {
        data class Ok(
            val hasEntry: Boolean,
            val moodAvg7d: Float?,
            val suggestedNextEntryAt: String?,
        ) : SummaryResult()

        data object Unauthorized : SummaryResult()

        data object HttpError : SummaryResult()
    }

    private data class RotatedTokens(
        val accessToken: String,
        val refreshToken: String,
    )

    private fun fetchSummary(apiBase: String, accessToken: String): SummaryResult {
        val connection =
            (URL(buildSummaryUrl(apiBase)).openConnection() as HttpURLConnection).apply {
                requestMethod = "GET"
                setRequestProperty("Authorization", "Bearer $accessToken")
                setRequestProperty("Accept", "application/json")
                connectTimeout = 12_000
                readTimeout = 12_000
            }
        try {
            val code = connection.responseCode
            if (code == HttpURLConnection.HTTP_UNAUTHORIZED ||
                code == HttpURLConnection.HTTP_FORBIDDEN
            ) {
                return SummaryResult.Unauthorized
            }
            if (code !in 200..299) {
                return SummaryResult.HttpError
            }
            val body = connection.inputStream.bufferedReader().use { it.readText() }
            val json = JSONObject(body)
            val hasEntry = json.optBoolean("has_entry", false)
            val mood =
                if (json.isNull("mood_avg_7d")) {
                    null
                } else {
                    json.optDouble("mood_avg_7d", Double.NaN).toFloat().takeUnless { it.isNaN() }
                }
            val suggested =
                if (json.isNull("suggested_next_entry_at")) {
                    null
                } else {
                    json.optString("suggested_next_entry_at").takeIf { it.isNotBlank() }
                }
            return SummaryResult.Ok(
                hasEntry = hasEntry,
                moodAvg7d = mood,
                suggestedNextEntryAt = suggested,
            )
        } finally {
            connection.disconnect()
        }
    }

    /**
     * Body-token refresh (Capacitor path). Cookie refresh is never used from
     * the widget process — credentials: omit equivalent (no Cookie header).
     */
    private fun refreshAccessToken(apiBase: String, refreshToken: String): RotatedTokens? {
        val connection =
            (URL(buildRefreshUrl(apiBase)).openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                doOutput = true
                setRequestProperty("Content-Type", "application/json")
                setRequestProperty("Accept", "application/json")
                connectTimeout = 12_000
                readTimeout = 12_000
            }
        try {
            val payload = JSONObject().put("refresh_token", refreshToken).toString()
            connection.outputStream.bufferedWriter().use { it.write(payload) }
            val code = connection.responseCode
            if (code !in 200..299) {
                return null
            }
            val body = connection.inputStream.bufferedReader().use { it.readText() }
            val json = JSONObject(body)
            val access = json.optString("access_token").takeIf { it.isNotBlank() } ?: return null
            val refresh = json.optString("refresh_token").takeIf { it.isNotBlank() } ?: return null
            return RotatedTokens(accessToken = access, refreshToken = refresh)
        } catch (_: Exception) {
            return null
        } finally {
            connection.disconnect()
        }
    }

    companion object {
        private const val UNIQUE_PERIODIC = "correlcore_widget_refresh"
        private const val UNIQUE_ONCE = "correlcore_widget_refresh_once"

        @JvmStatic
        fun enqueuePeriodic(context: Context) {
            val constraints =
                Constraints.Builder()
                    .setRequiredNetworkType(NetworkType.CONNECTED)
                    .setRequiresBatteryNotLow(true)
                    .build()

            val request =
                PeriodicWorkRequestBuilder<WidgetRefreshWorker>(15, TimeUnit.MINUTES)
                    .setConstraints(constraints)
                    .build()

            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                UNIQUE_PERIODIC,
                ExistingPeriodicWorkPolicy.KEEP,
                request,
            )
        }

        @JvmStatic
        fun enqueueImmediate(context: Context) {
            val constraints =
                Constraints.Builder()
                    .setRequiredNetworkType(NetworkType.CONNECTED)
                    .build()

            val request =
                OneTimeWorkRequestBuilder<WidgetRefreshWorker>()
                    .setConstraints(constraints)
                    .build()

            WorkManager.getInstance(context).enqueueUniqueWork(
                UNIQUE_ONCE,
                ExistingWorkPolicy.REPLACE,
                request,
            )
            enqueuePeriodic(context)
        }

        private fun buildSummaryUrl(apiBase: String): String {
            val base = apiBase.trimEnd('/')
            return if (base.endsWith("/api/v1")) {
                "$base/widget/summary"
            } else if (base.endsWith("/api")) {
                "$base/v1/widget/summary"
            } else {
                "$base/api/v1/widget/summary"
            }
        }

        private fun buildRefreshUrl(apiBase: String): String {
            val base = apiBase.trimEnd('/')
            val root =
                if (base.endsWith("/api/v1")) {
                    base
                } else if (base.endsWith("/api")) {
                    "$base/v1"
                } else {
                    "$base/api/v1"
                }
            return "$root/auth/refresh?include_access_token=true"
        }
    }
}
