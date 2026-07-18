package de.correlcore.app;

import android.os.Bundle;

import com.getcapacitor.BridgeActivity;

import de.correlcore.app.push.PushAvailabilityPlugin;
import de.correlcore.app.session.SecureSessionPlugin;
import de.correlcore.app.widget.WidgetCredentialsPlugin;
import de.correlcore.app.widget.WidgetRefreshWorker;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(WidgetCredentialsPlugin.class);
        registerPlugin(PushAvailabilityPlugin.class);
        registerPlugin(SecureSessionPlugin.class);
        super.onCreate(savedInstanceState);
        WidgetRefreshWorker.enqueuePeriodic(getApplicationContext());
    }
}
