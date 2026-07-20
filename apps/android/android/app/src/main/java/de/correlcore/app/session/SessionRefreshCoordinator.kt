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
 * 2. always reads the latest token from native stores before calling the API
 *    (SecureSession preferred — canonical after WebView login),
 * 3. dual-writes rotated tokens to WidgetCredentials + SecureSession,
 * 4. distinguishes auth rejection from transient network/5xx failures so
 *    callers do not wipe credentials (and provoke stale-JWT revoke_all).
 */
object SessionRefreshCoordinator {
    private val lock = Any()

    data class RotatedTokens(
        val accessToken: String,
        val refreshToken: String,
        val apiBase: String,
    )

    sealed class Outcome {
        data class Success(val tokens: RotatedTokens) : Outcome()

        /** Server rejected the refresh token (401/403) — clear local credentials. */
        data object AuthRejected : Outcome()

        /** Network / 5xx / parse failure — keep credentials and retry later. */
        data object TransientFailure : Outcome()

        /** No usable refresh token in either store. */
        data object MissingCredentials : Outcome()
    }

    /**
     * Rotate access/refresh using the newest native (or hint) refresh token.
     */
    fun refresh(
        context: Context,
        apiBaseHint: String?,
        refreshTokenHint: String?,
    ): Outcome {
        synchronized(lock) {
            val appContext = context.applicationContext
            val widget = WidgetCredentialsStore.getCredentials(appContext)
            val secure = SecureSessionStore.get(appContext)
            // Prefer SecureSession (WebView login mirror) over widget — the
            // widget copy can lag after an in-app rotation.
            val refreshToken =
                secure?.refreshToken?.takeIf { it.isNotBlank() }
                    ?: widget?.refreshToken?.takeIf { it.isNotBlank() }
                    ?: refreshTokenHint?.takeIf { it.isNotBlank() }
                    ?: return Outcome.MissingCredentials
            val apiBase =
                secure?.apiBase?.takeIf { it.isNotBlank() }
                    ?: widget?.apiBase?.takeIf { it.isNotBlank() }
                    ?: apiBaseHint?.trim()?.trimEnd('/')?.takeIf { it.isNotBlank() }
                    ?: return Outcome.MissingCredentials

            val http = httpRefresh(apiBase, refreshToken)
            when (http) {
                is HttpResult.AuthRejected -> return Outcome.AuthRejected
                is HttpResult.TransientFailure -> return Outcome.TransientFailure
                is HttpResult.Success -> {
                    val rotated = http.tokens
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
                    return Outcome.Success(
                        RotatedTokens(
                            accessToken = rotated.accessToken,
                            refreshToken = rotated.refreshToken,
                            apiBase = apiBase,
                        ),
                    )
                }
            }
        }
    }

    private data class HttpTokens(
        val accessToken: String,
        val refreshToken: String,
    )

    private sealed class HttpResult {
        data class Success(val tokens: HttpTokens) : HttpResult()

        data object AuthRejected : HttpResult()

        data object TransientFailure : HttpResult()
    }

    private fun httpRefresh(apiBase: String, refreshToken: String): HttpResult {
        val connection =
            try {
                (URL(buildRefreshUrl(apiBase)).openConnection() as HttpURLConnection).apply {
                    requestMethod = "POST"
                    doOutput = true
                    setRequestProperty("Content-Type", "application/json")
                    setRequestProperty("Accept", "application/json")
                    connectTimeout = 12_000
                    readTimeout = 12_000
                }
            } catch (_: Exception) {
                return HttpResult.TransientFailure
            }
        try {
            val payload = JSONObject().put("refresh_token", refreshToken).toString()
            connection.outputStream.bufferedWriter().use { it.write(payload) }
            val code = connection.responseCode
            if (code == HttpURLConnection.HTTP_UNAUTHORIZED ||
                code == HttpURLConnection.HTTP_FORBIDDEN
            ) {
                return HttpResult.AuthRejected
            }
            if (code !in 200..299) {
                return HttpResult.TransientFailure
            }
            val body = connection.inputStream.bufferedReader().use { it.readText() }
            val json = JSONObject(body)
            val access = json.optString("access_token").takeIf { it.isNotBlank() }
                ?: return HttpResult.TransientFailure
            val refresh = json.optString("refresh_token").takeIf { it.isNotBlank() }
                ?: return HttpResult.TransientFailure
            return HttpResult.Success(HttpTokens(accessToken = access, refreshToken = refresh))
        } catch (_: Exception) {
            return HttpResult.TransientFailure
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
