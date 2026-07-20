package de.correlcore.app.session

import android.content.Context
import de.correlcore.app.widget.WidgetCredentialsStore
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/**
 * Single-process refresh lock for Capacitor WebView + Glance WorkManager.
 *
 * Refresh tokens are single-use. If the widget rotates first and the WebView
 * later posts the stale refresh JWT, the API treats it as replay and
 * ``revoke_all`` — the user appears to "lose contact" after ~15 minutes
 * (access TTL). This coordinator:
 * 1. serializes refresh in-process,
 * 2. always reads the latest token from native stores before calling the API,
 * 3. dual-writes rotated tokens to WidgetCredentials + SecureSession.
 */
object SessionRefreshCoordinator {
    private val lock = Any()

    data class RotatedTokens(
        val accessToken: String,
        val refreshToken: String,
        val apiBase: String,
    )

    /**
     * Rotate access/refresh using the newest native (or hint) refresh token.
     * Returns null when no token/base is available or the HTTP refresh fails.
     */
    fun refresh(
        context: Context,
        apiBaseHint: String?,
        refreshTokenHint: String?,
    ): RotatedTokens? {
        synchronized(lock) {
            val appContext = context.applicationContext
            val widget = WidgetCredentialsStore.getCredentials(appContext)
            val secure = SecureSessionStore.get(appContext)
            val refreshToken =
                widget?.refreshToken
                    ?: secure?.refreshToken
                    ?: refreshTokenHint?.takeIf { it.isNotBlank() }
                    ?: return null
            val apiBase =
                widget?.apiBase
                    ?: secure?.apiBase
                    ?: apiBaseHint?.trim()?.trimEnd('/')?.takeIf { it.isNotBlank() }
                    ?: return null

            val rotated = httpRefresh(apiBase, refreshToken) ?: return null

            // Widget mirror exists only when „Angemeldet bleiben“ mirrored tokens.
            WidgetCredentialsStore.setCredentials(
                appContext,
                rotated.accessToken,
                rotated.refreshToken,
                apiBase,
            )
            // Keep EncryptedSharedPreferences in lockstep so WebView cold-start
            // and in-memory re-sync never see a stale refresh after widget rotate.
            if (secure != null || refreshTokenHint != null) {
                SecureSessionStore.set(
                    appContext,
                    accessToken = rotated.accessToken,
                    refreshToken = rotated.refreshToken,
                    apiBase = apiBase,
                    rememberMe = true,
                )
            }

            return RotatedTokens(
                accessToken = rotated.accessToken,
                refreshToken = rotated.refreshToken,
                apiBase = apiBase,
            )
        }
    }

    private data class HttpTokens(
        val accessToken: String,
        val refreshToken: String,
    )

    private fun httpRefresh(apiBase: String, refreshToken: String): HttpTokens? {
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
            return HttpTokens(accessToken = access, refreshToken = refresh)
        } catch (_: Exception) {
            return null
        } finally {
            connection.disconnect()
        }
    }

    internal fun buildRefreshUrl(apiBase: String): String {
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
