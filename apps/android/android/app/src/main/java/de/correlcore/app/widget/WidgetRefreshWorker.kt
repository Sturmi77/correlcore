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
                val summaryUrl = buildSummaryUrl(creds.apiBase)
                val connection = (URL(summaryUrl).openConnection() as HttpURLConnection).apply {
                    requestMethod = "GET"
                    setRequestProperty("Authorization", "Bearer ${creds.accessToken}")
                    setRequestProperty("Accept", "application/json")
                    connectTimeout = 12_000
                    readTimeout = 12_000
                }

                try {
                    val code = connection.responseCode
                    if (code == HttpURLConnection.HTTP_UNAUTHORIZED ||
                        code == HttpURLConnection.HTTP_FORBIDDEN
                    ) {
                        WidgetCredentialsStore.clearCredentials(applicationContext)
                        CorrelCoreWidget().updateAll(applicationContext)
                        return@withContext Result.success()
                    }
                    if (code !in 200..299) {
                        WidgetCredentialsStore.setStatus(
                            applicationContext,
                            WidgetCredentialsStore.STATUS_ERROR,
                        )
                        CorrelCoreWidget().updateAll(applicationContext)
                        return@withContext Result.retry()
                    }

                    val body =
                        connection.inputStream.bufferedReader().use { it.readText() }
                    val json = JSONObject(body)
                    val hasEntry = json.optBoolean("has_entry", false)
                    val mood =
                        if (json.isNull("mood_avg_7d")) {
                            null
                        } else {
                            json.optDouble("mood_avg_7d", Double.NaN).toFloat().takeUnless {
                                it.isNaN()
                            }
                        }
                    val suggested =
                        if (json.isNull("suggested_next_entry_at")) {
                            null
                        } else {
                            json.optString("suggested_next_entry_at").takeIf { it.isNotBlank() }
                        }

                    WidgetCredentialsStore.saveSummary(
                        applicationContext,
                        hasEntry = hasEntry,
                        moodAvg7d = mood,
                        suggestedNextEntryAt = suggested,
                        status = WidgetCredentialsStore.STATUS_OK,
                    )
                    CorrelCoreWidget().updateAll(applicationContext)
                    Result.success()
                } finally {
                    connection.disconnect()
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
    }
}
