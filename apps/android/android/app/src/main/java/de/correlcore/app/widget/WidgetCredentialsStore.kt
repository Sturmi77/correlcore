package de.correlcore.app.widget

import android.content.Context

/**
 * App-private store for the Glance widget / WorkManager.
 *
 * Written by [WidgetCredentialsPlugin] when the Capacitor WebView logs in;
 * cleared on logout. Not used by the browser cookie auth path.
 *
 * Stores access + refresh so [WidgetRefreshWorker] can rotate after the
 * ~15 minute access JWT TTL (ADR-0006 M11 widget exception).
 */
object WidgetCredentialsStore {
    private const val PREFS = "correlcore_widget"
    private const val KEY_ACCESS_TOKEN = "access_token"
    private const val KEY_REFRESH_TOKEN = "refresh_token"
    private const val KEY_API_BASE = "api_base"
    private const val KEY_HAS_ENTRY = "cache_has_entry"
    private const val KEY_MOOD_AVG = "cache_mood_avg_7d"
    private const val KEY_SUGGESTED_AT = "cache_suggested_next_entry_at"
    private const val KEY_UPDATED_AT = "cache_updated_at_ms"
    private const val KEY_STATUS = "cache_status"

    const val STATUS_OK = "ok"
    const val STATUS_SIGNED_OUT = "signed_out"
    const val STATUS_ERROR = "error"
    const val STATUS_LOADING = "loading"

    data class Credentials(
        val accessToken: String,
        val refreshToken: String,
        val apiBase: String,
    )

    data class CachedSummary(
        val hasEntry: Boolean,
        val moodAvg7d: Float?,
        val suggestedNextEntryAt: String?,
        val updatedAtMs: Long,
        val status: String,
    )

    private fun prefs(context: Context) =
        context.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun setCredentials(
        context: Context,
        accessToken: String,
        refreshToken: String,
        apiBase: String,
    ) {
        prefs(context)
            .edit()
            .putString(KEY_ACCESS_TOKEN, accessToken)
            .putString(KEY_REFRESH_TOKEN, refreshToken)
            .putString(KEY_API_BASE, apiBase.trimEnd('/'))
            .apply()
    }

    fun clearCredentials(context: Context) {
        prefs(context)
            .edit()
            .remove(KEY_ACCESS_TOKEN)
            .remove(KEY_REFRESH_TOKEN)
            .remove(KEY_API_BASE)
            .putString(KEY_STATUS, STATUS_SIGNED_OUT)
            .apply()
    }

    fun getCredentials(context: Context): Credentials? {
        val p = prefs(context)
        val access = p.getString(KEY_ACCESS_TOKEN, null)?.takeIf { it.isNotBlank() } ?: return null
        val refresh = p.getString(KEY_REFRESH_TOKEN, null)?.takeIf { it.isNotBlank() } ?: return null
        val base = p.getString(KEY_API_BASE, null)?.takeIf { it.isNotBlank() } ?: return null
        return Credentials(accessToken = access, refreshToken = refresh, apiBase = base)
    }

    fun saveSummary(
        context: Context,
        hasEntry: Boolean,
        moodAvg7d: Float?,
        suggestedNextEntryAt: String?,
        status: String = STATUS_OK,
    ) {
        val editor =
            prefs(context)
                .edit()
                .putBoolean(KEY_HAS_ENTRY, hasEntry)
                .putLong(KEY_UPDATED_AT, System.currentTimeMillis())
                .putString(KEY_STATUS, status)
        if (moodAvg7d == null) {
            editor.remove(KEY_MOOD_AVG)
        } else {
            editor.putFloat(KEY_MOOD_AVG, moodAvg7d)
        }
        if (suggestedNextEntryAt.isNullOrBlank()) {
            editor.remove(KEY_SUGGESTED_AT)
        } else {
            editor.putString(KEY_SUGGESTED_AT, suggestedNextEntryAt)
        }
        editor.apply()
    }

    fun setStatus(context: Context, status: String) {
        prefs(context).edit().putString(KEY_STATUS, status).apply()
    }

    fun getCachedSummary(context: Context): CachedSummary {
        val p = prefs(context)
        val mood =
            if (p.contains(KEY_MOOD_AVG)) {
                p.getFloat(KEY_MOOD_AVG, 0f)
            } else {
                null
            }
        return CachedSummary(
            hasEntry = p.getBoolean(KEY_HAS_ENTRY, false),
            moodAvg7d = mood,
            suggestedNextEntryAt = p.getString(KEY_SUGGESTED_AT, null),
            updatedAtMs = p.getLong(KEY_UPDATED_AT, 0L),
            status = p.getString(KEY_STATUS, STATUS_SIGNED_OUT) ?: STATUS_SIGNED_OUT,
        )
    }
}
