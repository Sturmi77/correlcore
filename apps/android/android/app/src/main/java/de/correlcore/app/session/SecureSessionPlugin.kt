package de.correlcore.app.session

import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin

/**
 * Capacitor bridge for WebView persistent session restore (Issue #453).
 */
@CapacitorPlugin(name = "SecureSession")
class SecureSessionPlugin : Plugin() {
    @PluginMethod
    fun set(call: PluginCall) {
        val refreshToken = call.getString("refreshToken")
        if (refreshToken.isNullOrBlank()) {
            call.reject("refreshToken is required")
            return
        }
        val rememberMe = call.getBoolean("rememberMe", true) ?: true
        if (!rememberMe) {
            SecureSessionStore.clear(context)
            call.resolve()
            return
        }
        SecureSessionStore.set(
            context,
            accessToken = call.getString("accessToken"),
            refreshToken = refreshToken,
            apiBase = call.getString("apiBase"),
            rememberMe = true,
        )
        call.resolve()
    }

    @PluginMethod
    fun get(call: PluginCall) {
        val session = SecureSessionStore.get(context)
        if (session == null) {
            call.resolve(JSObject())
            return
        }
        val result = JSObject()
        result.put("refreshToken", session.refreshToken)
        result.put("rememberMe", session.rememberMe)
        session.accessToken?.let { result.put("accessToken", it) }
        session.apiBase?.let { result.put("apiBase", it) }
        call.resolve(result)
    }

    @PluginMethod
    fun clear(call: PluginCall) {
        SecureSessionStore.clear(context)
        call.resolve()
    }

    /**
     * Rotate JWTs via [SessionRefreshCoordinator] so WebView and Glance share
     * one in-process refresh (avoids refresh-token replay → revoke_all).
     *
     * Reject codes (JS must not fall back to fetch with a stale refresh JWT
     * on TRANSIENT — that can trigger revoke_all):
     * - AUTH_REJECTED: server rejected token — clear session
     * - TRANSIENT: network/5xx — keep credentials, retry later
     * - MISSING: no refresh token available
     */
    @PluginMethod
    fun refresh(call: PluginCall) {
        when (
            val outcome =
                SessionRefreshCoordinator.refresh(
                    context,
                    apiBaseHint = call.getString("apiBase"),
                    refreshTokenHint = call.getString("refreshToken"),
                )
        ) {
            is SessionRefreshCoordinator.Outcome.Success -> {
                val rotated = outcome.tokens
                val result = JSObject()
                result.put("accessToken", rotated.accessToken)
                result.put("refreshToken", rotated.refreshToken)
                result.put("apiBase", rotated.apiBase)
                call.resolve(result)
            }
            SessionRefreshCoordinator.Outcome.AuthRejected ->
                call.reject("refresh rejected by server", "AUTH_REJECTED")
            SessionRefreshCoordinator.Outcome.TransientFailure ->
                call.reject("refresh temporarily unavailable", "TRANSIENT")
            SessionRefreshCoordinator.Outcome.MissingCredentials ->
                call.reject("no refresh credentials", "MISSING")
        }
    }
}
