package de.correlcore.app.widget

import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin

/**
 * Capacitor bridge: WebView mirrors in-memory Bearer tokens for Glance.
 */
@CapacitorPlugin(name = "WidgetCredentials")
class WidgetCredentialsPlugin : Plugin() {
    @PluginMethod
    fun set(call: PluginCall) {
        val accessToken = call.getString("accessToken")
        val refreshToken = call.getString("refreshToken")
        val apiBase = call.getString("apiBase")
        if (accessToken.isNullOrBlank() || refreshToken.isNullOrBlank() || apiBase.isNullOrBlank()) {
            call.reject("accessToken, refreshToken and apiBase are required")
            return
        }
        WidgetCredentialsStore.setCredentials(context, accessToken, refreshToken, apiBase)
        WidgetRefreshWorker.enqueueImmediate(context)
        call.resolve()
    }

    @PluginMethod
    fun clear(call: PluginCall) {
        WidgetCredentialsStore.clearCredentials(context)
        WidgetRefreshWorker.enqueueImmediate(context)
        call.resolve()
    }
}
