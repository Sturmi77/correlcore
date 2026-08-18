package de.correlcore.app.health;

import android.content.Intent;

import com.getcapacitor.Bridge;
import com.getcapacitor.BridgeActivity;
import com.getcapacitor.Plugin;

import java.util.ArrayList;
import java.util.List;

/**
 * Play-flavor Health Connect seam — a deliberate no-op.
 *
 * <p>The Play build ships HC-free (AP-HC Option A, see
 * {@code docs/M11_PLAY_STORE_GAP_ANALYSIS.md} §4): no {@code health.*} permissions,
 * no Health Connect plugin, no HC data-safety declaration, no HC review. This
 * class mirrors the sideload flavor's public API so {@code MainActivity} remains
 * a single, flavor-agnostic source file. Health Connect returns to the Play build
 * via the reverse-path in §4.2 once a user-facing HC feature ships.
 */
public final class HealthConnectSupport {

    /** No native HC plugin in the Play build. */
    public List<Class<? extends Plugin>> pluginClasses() {
        return new ArrayList<>();
    }

    /** No Health Connect rationale routing in the Play build. */
    public void onBridgeReady(final BridgeActivity activity, final Bridge bridge) {
        // intentionally empty
    }

    /** No Health Connect rationale routing in the Play build. */
    public void onNewIntent(final BridgeActivity activity, final Intent intent) {
        // intentionally empty
    }
}
