package de.correlcore.app;

import android.content.Intent;
import android.os.Bundle;
import android.webkit.ValueCallback;
import android.webkit.WebView;

import com.getcapacitor.Bridge;
import com.getcapacitor.BridgeActivity;
import com.getcapacitor.WebViewListener;

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

    // Cold start: the WebView's first page load has not finished yet, so a
    // rationale intent that arrives via onCreate must wait for onPageLoaded
    // (below) instead of navigating immediately (#626 review).
    private boolean webViewLoaded = false;
    private boolean pendingRationaleRoute = false;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(WidgetCredentialsPlugin.class);
        registerPlugin(PushAvailabilityPlugin.class);
        registerPlugin(SecureSessionPlugin.class);
        registerPlugin(HealthConnectPlugin.class);
        super.onCreate(savedInstanceState);
        final Bridge bridge = getBridge();
        if (bridge != null) {
            bridge.addWebViewListener(new WebViewListener() {
                @Override
                public void onPageLoaded(WebView webView) {
                    webViewLoaded = true;
                    if (pendingRationaleRoute) {
                        pendingRationaleRoute = false;
                        navigateToRationale(bridge);
                    }
                }
            });
        }
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
     * bridge never becomes available the app simply opens at its normal start
     * route. On a cold start the WebView's initial page has not finished
     * loading yet, so navigating immediately races that pending load and can be
     * silently overwritten — defer until {@link WebViewListener#onPageLoaded}
     * fires instead (#626 review).
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
        if (bridge == null) {
            return;
        }
        if (webViewLoaded) {
            navigateToRationale(bridge);
        } else {
            pendingRationaleRoute = true;
        }
    }

    private void navigateToRationale(Bridge bridge) {
        if (bridge.getWebView() == null) {
            return;
        }
        bridge.eval(
            "window.location.assign('" + HC_RATIONALE_PATH + "')",
            (ValueCallback<String>) value -> { }
        );
    }
}
