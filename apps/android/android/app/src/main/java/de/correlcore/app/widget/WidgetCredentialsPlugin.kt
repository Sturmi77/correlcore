package de.correlcore.app.widget

import com.getcapacitor.JSObject
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
    fun get(call: PluginCall) {
        val creds = WidgetCredentialsStore.getCredentials(context)
        if (creds == null) {
            call.resolve(JSObject())
            return
        }
        val result = JSObject()
        result.put("accessToken", creds.accessToken)
        result.put("refreshToken", creds.refreshToken)
        result.put("apiBase", creds.apiBase)
        call.resolve(result)
    }

    @PluginMethod
    fun clear(call: PluginCall) {
        WidgetCredentialsStore.clearCredentials(context)
        WidgetRefreshWorker.enqueueImmediate(context)
        call.resolve()
    }
}
