package de.correlcore.app.session

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/**
 * Keystore-backed store for Capacitor WebView session restore (Issue #453).
 *
 * Holds refresh (+ optional access) so a cold start can hydrate without
 * re-entering credentials when „Angemeldet bleiben“ is on. Never used by
 * the browser cookie path.
 */
object SecureSessionStore {
    private const val PREFS = "correlcore_secure_session"
    private const val KEY_ACCESS = "access_token"
    private const val KEY_REFRESH = "refresh_token"
    private const val KEY_API_BASE = "api_base"
    private const val KEY_REMEMBER = "remember_me"

    data class Session(
        val accessToken: String?,
        val refreshToken: String,
        val apiBase: String?,
        val rememberMe: Boolean,
    )

    private fun prefs(context: Context): SharedPreferences {
        val masterKey =
            MasterKey.Builder(context.applicationContext)
                .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
                .build()
        return EncryptedSharedPreferences.create(
            context.applicationContext,
            PREFS,
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    }

    fun set(
        context: Context,
        accessToken: String?,
        refreshToken: String,
        apiBase: String?,
        rememberMe: Boolean,
    ) {
        prefs(context)
            .edit()
            .putString(KEY_ACCESS, accessToken)
            .putString(KEY_REFRESH, refreshToken)
            .putString(KEY_API_BASE, apiBase?.trimEnd('/'))
            .putBoolean(KEY_REMEMBER, rememberMe)
            .apply()
    }

    fun clear(context: Context) {
        prefs(context).edit().clear().apply()
    }

    fun get(context: Context): Session? {
        val p = prefs(context)
        val refresh = p.getString(KEY_REFRESH, null)?.takeIf { it.isNotBlank() } ?: return null
        if (!p.getBoolean(KEY_REMEMBER, false)) return null
        return Session(
            accessToken = p.getString(KEY_ACCESS, null)?.takeIf { it.isNotBlank() },
            refreshToken = refresh,
            apiBase = p.getString(KEY_API_BASE, null)?.takeIf { it.isNotBlank() },
            rememberMe = true,
        )
    }
}
