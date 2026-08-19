package de.correlcore.app.health;

import android.content.Intent;
import android.webkit.ValueCallback;
import android.webkit.WebView;

import com.getcapacitor.Bridge;
import com.getcapacitor.BridgeActivity;
import com.getcapacitor.Plugin;
import com.getcapacitor.WebViewListener;

import java.util.ArrayList;
import java.util.List;

/**
 * Sideload-flavor Health Connect wiring (M8). Provides the HC Capacitor plugin
 * to {@code MainActivity} and routes Health Connect permission-rationale intents
 * to the {@code /health-connect} web route.
 *
 * <p>The Play flavor ships a no-op counterpart of this class (same package,
 * same public API) so {@code MainActivity} stays a single source file and the
 * Play build carries no Health Connect code, permissions, or declaration —
 * AP-HC Option A, see {@code docs/M11_PLAY_STORE_GAP_ANALYSIS.md} §4.
 */
public final class HealthConnectSupport {
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
    // instead of navigating immediately (#626 review).
    private boolean webViewLoaded = false;
    private boolean pendingRationaleRoute = false;

    /** Native plugins this flavor contributes; registered before super.onCreate(). */
    public List<Class<? extends Plugin>> pluginClasses() {
        List<Class<? extends Plugin>> plugins = new ArrayList<>();
        plugins.add(HealthConnectPlugin.class);
        return plugins;
    }

    /** Wire rationale routing once the Capacitor bridge exists (after super.onCreate()). */
    public void onBridgeReady(final BridgeActivity activity, final Bridge bridge) {
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
        routeRationale(bridge, activity.getIntent());
    }

    /** Route a Health Connect rationale intent delivered to a running activity. */
    public void onNewIntent(final BridgeActivity activity, final Intent intent) {
        routeRationale(activity.getBridge(), intent);
    }

    /**
     * When Health Connect launches us to show the permission rationale, send the
     * WebView to the rationale page (M8 Sprint 3, ADR-0042). Best-effort: on a
     * cold start the WebView's initial page has not finished loading yet, so
     * navigating immediately races that pending load and can be silently
     * overwritten — defer until {@link WebViewListener#onPageLoaded} fires (#626).
     */
    private void routeRationale(final Bridge bridge, final Intent intent) {
        if (intent == null || intent.getAction() == null) {
            return;
        }
        String action = intent.getAction();
        if (!ACTION_HC_RATIONALE.equals(action) && !ACTION_VIEW_PERMISSION_USAGE.equals(action)) {
            return;
        }
        if (bridge == null) {
            return;
        }
        if (webViewLoaded) {
            navigateToRationale(bridge);
        } else {
            pendingRationaleRoute = true;
        }
    }

    private void navigateToRationale(final Bridge bridge) {
        if (bridge.getWebView() == null) {
            return;
        }
        bridge.eval(
            "window.location.assign('" + HC_RATIONALE_PATH + "')",
            (ValueCallback<String>) value -> { }
        );
    }
}
