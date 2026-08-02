package de.correlcore.app;

import android.content.Intent;
import android.os.Bundle;
import android.webkit.ValueCallback;

import com.getcapacitor.Bridge;
import com.getcapacitor.BridgeActivity;

import de.correlcore.app.health.HealthConnectPlugin;
import de.correlcore.app.push.PushAvailabilityPlugin;
import de.correlcore.app.session.SecureSessionPlugin;
import de.correlcore.app.widget.WidgetCredentialsPlugin;
import de.correlcore.app.widget.WidgetRefreshWorker;

public class MainActivity extends BridgeActivity {
    // Health Connect asks the app to explain its data use via these actions
    // (pre-14 HC APK, and the Android 14+ framework permission-usage view).
    private static final String ACTION_HC_RATIONALE =
        "androidx.health.ACTION_SHOW_PERMISSIONS_RATIONALE";
    private static final String ACTION_VIEW_PERMISSION_USAGE =
        "android.intent.action.VIEW_PERMISSION_USAGE";
    // Web route that documents which Health Connect data is read and why.
    private static final String HC_RATIONALE_PATH = "/health-connect";

    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(WidgetCredentialsPlugin.class);
        registerPlugin(PushAvailabilityPlugin.class);
        registerPlugin(SecureSessionPlugin.class);
        registerPlugin(HealthConnectPlugin.class);
        super.onCreate(savedInstanceState);
        // Only poll when a widget is actually on a homescreen (#446). Also
        // cancels leftover work from a build that scheduled unconditionally.
        WidgetRefreshWorker.syncPeriodicWork(getApplicationContext());
        routeHealthConnectRationale(getIntent());
    }

    @Override
    public void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        routeHealthConnectRationale(intent);
    }

    /**
     * When Health Connect launches us to show the permission rationale, send the
     * WebView to the rationale page (M8 Sprint 3, ADR-0042). Best-effort: if the
     * bridge is not ready yet the app simply opens at its normal start route.
     */
    private void routeHealthConnectRationale(Intent intent) {
        if (intent == null || intent.getAction() == null) {
            return;
        }
        String action = intent.getAction();
        if (!ACTION_HC_RATIONALE.equals(action) && !ACTION_VIEW_PERMISSION_USAGE.equals(action)) {
            return;
        }
        final Bridge bridge = getBridge();
        if (bridge == null || bridge.getWebView() == null) {
            return;
        }
        bridge.getWebView().post(() ->
            bridge.eval(
                "window.location.assign('" + HC_RATIONALE_PATH + "')",
                (ValueCallback<String>) value -> { }
            )
        );
    }
}
