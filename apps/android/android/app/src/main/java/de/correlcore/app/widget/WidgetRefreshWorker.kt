package de.correlcore.app.widget

import android.appwidget.AppWidgetManager
import android.content.ComponentName
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
import de.correlcore.app.session.SessionRefreshCoordinator
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import java.time.LocalDate
import java.util.TimeZone
import java.util.concurrent.TimeUnit

/**
 * Battery-aware poll of GET /api/v1/widget/summary (15-minute periodic).
 *
 * On 401/403, rotates via [SessionRefreshCoordinator] (shared lock + dual-write
 * with SecureSession) before signing the widget out.
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
                var apiBase = creds.apiBase
                var summary = fetchSummary(apiBase, accessToken)

                if (summary is SummaryResult.Unauthorized) {
                    when (
                        val outcome =
                            SessionRefreshCoordinator.refresh(
                                applicationContext,
                                apiBaseHint = apiBase,
                                refreshTokenHint = creds.refreshToken,
                            )
                    ) {
                        is SessionRefreshCoordinator.Outcome.Success -> {
                            accessToken = outcome.tokens.accessToken
                            apiBase = outcome.tokens.apiBase
                            summary = fetchSummary(apiBase, accessToken)
                        }
                        SessionRefreshCoordinator.Outcome.AuthRejected,
                        SessionRefreshCoordinator.Outcome.MissingCredentials,
                        -> {
                            WidgetCredentialsStore.clearCredentials(applicationContext)
                            CorrelCoreWidget().updateAll(applicationContext)
                            return@withContext Result.success()
                        }
                        SessionRefreshCoordinator.Outcome.TransientFailure -> {
                            // Keep credentials; retry without wiping auth (avoids
                            // WebView stale-JWT refresh → revoke_all).
                            WidgetCredentialsStore.setStatus(
                                applicationContext,
                                WidgetCredentialsStore.STATUS_ERROR,
                            )
                            CorrelCoreWidget().updateAll(applicationContext)
                            return@withContext Result.retry()
                        }
                    }
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

    companion object {
        // NEWAPI-PROBE: java.time on minSdk 23 must fail lintDebug. Reverted.
        @JvmStatic
        fun __newApiProbe(): String = LocalDate.now().toString()

        private const val UNIQUE_PERIODIC = "correlcore_widget_refresh"
        private const val UNIQUE_ONCE = "correlcore_widget_refresh_once"

        /** True when at least one CorrelCore widget is on a homescreen. */
        @JvmStatic
        fun hasInstalledWidgets(context: Context): Boolean {
            return try {
                val component = ComponentName(context, CorrelCoreWidgetReceiver::class.java)
                AppWidgetManager.getInstance(context)
                    ?.getAppWidgetIds(component)
                    ?.isNotEmpty() == true
            } catch (_: Exception) {
                // Never let a widget-manager hiccup break app start.
                false
            }
        }

        /**
         * Align periodic polling with reality (#446).
         *
         * App start used to enqueue the 15-minute poll unconditionally, so users
         * who never placed a widget still ran background summary requests after
         * signing in — and with no onDisabled, polling continued until logout.
         */
        @JvmStatic
        fun syncPeriodicWork(context: Context) {
            if (hasInstalledWidgets(context)) {
                enqueuePeriodic(context)
            } else {
                cancelPeriodic(context)
            }
        }

        @JvmStatic
        fun cancelPeriodic(context: Context) {
            // Also drop a queued one-time refresh: onEnabled enqueues it behind a
            // network constraint, so placing a widget offline and removing it
            // again before connectivity returns would otherwise still fire one
            // request with no widget left to paint.
            WorkManager.getInstance(context).apply {
                cancelUniqueWork(UNIQUE_PERIODIC)
                cancelUniqueWork(UNIQUE_ONCE)
            }
        }

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

        /**
         * @param force skip the installed-widget check. Used from [onEnabled],
         *   where the first instance may not be visible to AppWidgetManager yet.
         */
        @JvmStatic
        @JvmOverloads
        fun enqueueImmediate(context: Context, force: Boolean = false) {
            if (!force && !hasInstalledWidgets(context)) {
                // Nothing to paint — make sure no stale periodic work survives.
                cancelPeriodic(context)
                return
            }

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

        fun buildSummaryUrl(apiBase: String): String {
            val base = apiBase.trimEnd('/')
            val path =
                if (base.endsWith("/api/v1")) {
                    "$base/widget/summary"
                } else if (base.endsWith("/api")) {
                    "$base/v1/widget/summary"
                } else {
                    "$base/api/v1/widget/summary"
                }
            // Entries are stored against a device-local date, so the server must
            // resolve "today" in this zone or the widget disagrees with the app
            // for anyone whose local day differs from UTC (#445).
            //
            // java.util.TimeZone, not java.time.ZoneId: minSdkVersion is 23 and
            // core-library desugaring is not enabled, so ZoneId would throw
            // NoClassDefFoundError on API 23-25 — an Error, which the worker's
            // `catch (Exception)` does not catch, killing every refresh.
            val tz = URLEncoder.encode(TimeZone.getDefault().id, "UTF-8")
            return "$path?tz=$tz"
        }

    }
}
