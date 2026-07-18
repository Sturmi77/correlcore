package de.correlcore.app.push

import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin
import de.correlcore.app.BuildConfig

/**
 * Reports whether this APK was built with Firebase / FCM wired
 * (`google-services.json` present → BuildConfig.FCM_ENABLED).
 *
 * Sideload builds omit the file; calling Capacitor PushNotifications.register()
 * then crashes the process (FirebaseApp uninitialized). The WebView must query
 * this before requesting permission or registering.
 */
@CapacitorPlugin(name = "PushAvailability")
class PushAvailabilityPlugin : Plugin() {
    @PluginMethod
    fun isAvailable(call: PluginCall) {
        val result = JSObject()
        result.put("available", BuildConfig.FCM_ENABLED)
        call.resolve(result)
    }
}
