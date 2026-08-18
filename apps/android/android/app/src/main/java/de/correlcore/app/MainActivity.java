package de.correlcore.app;

import android.content.Intent;
import android.os.Bundle;

import com.getcapacitor.BridgeActivity;
import com.getcapacitor.Plugin;

import de.correlcore.app.health.HealthConnectSupport;
import de.correlcore.app.push.PushAvailabilityPlugin;
import de.correlcore.app.session.SecureSessionPlugin;
import de.correlcore.app.widget.WidgetCredentialsPlugin;
import de.correlcore.app.widget.WidgetRefreshWorker;

public class MainActivity extends BridgeActivity {
    // Health Connect is provided only by the sideload flavor; the Play flavor
    // supplies a no-op HealthConnectSupport (AP-HC Option A —
    // docs/M11_PLAY_STORE_GAP_ANALYSIS.md §4). MainActivity stays flavor-agnostic.
    private final HealthConnectSupport healthConnect = new HealthConnectSupport();

    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(WidgetCredentialsPlugin.class);
        registerPlugin(PushAvailabilityPlugin.class);
        registerPlugin(SecureSessionPlugin.class);
        for (Class<? extends Plugin> plugin : healthConnect.pluginClasses()) {
            registerPlugin(plugin);
        }
        super.onCreate(savedInstanceState);
        // Only poll when a widget is actually on a homescreen (#446). Also
        // cancels leftover work from a build that scheduled unconditionally.
        WidgetRefreshWorker.syncPeriodicWork(getApplicationContext());
        healthConnect.onBridgeReady(this, getBridge());
    }

    @Override
    public void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        healthConnect.onNewIntent(this, intent);
    }
}
