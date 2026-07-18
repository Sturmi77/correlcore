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
}
