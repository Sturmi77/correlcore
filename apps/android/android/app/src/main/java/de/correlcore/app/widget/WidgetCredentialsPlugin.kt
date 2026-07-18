package de.correlcore.app.widget

import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin

/**
 * Capacitor bridge: WebView mirrors the in-memory Bearer token for Glance.
 */
@CapacitorPlugin(name = "WidgetCredentials")
class WidgetCredentialsPlugin : Plugin() {
    @PluginMethod
    fun set(call: PluginCall) {
        val accessToken = call.getString("accessToken")
        val apiBase = call.getString("apiBase")
        if (accessToken.isNullOrBlank() || apiBase.isNullOrBlank()) {
            call.reject("accessToken and apiBase are required")
            return
        }
        WidgetCredentialsStore.setCredentials(context, accessToken, apiBase)
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
