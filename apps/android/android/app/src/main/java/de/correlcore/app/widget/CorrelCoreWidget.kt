package de.correlcore.app.widget

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.glance.GlanceId
import androidx.glance.GlanceModifier
import androidx.glance.GlanceTheme
import androidx.glance.action.clickable
import androidx.glance.appwidget.GlanceAppWidget
import androidx.glance.appwidget.GlanceAppWidgetReceiver
import androidx.glance.appwidget.SizeMode
import androidx.glance.appwidget.action.actionStartActivity
import androidx.glance.appwidget.provideContent
import androidx.glance.background
import androidx.glance.color.ColorProvider
import androidx.glance.layout.Alignment
import androidx.glance.layout.Column
import androidx.glance.layout.Row
import androidx.glance.layout.Spacer
import androidx.glance.layout.fillMaxSize
import androidx.glance.layout.fillMaxWidth
import androidx.glance.layout.height
import androidx.glance.layout.padding
import androidx.glance.layout.width
import androidx.glance.text.FontWeight
import androidx.glance.text.Text
import androidx.glance.text.TextStyle
import java.text.DateFormat
import java.util.Date

class CorrelCoreWidget : GlanceAppWidget() {
    override val sizeMode: SizeMode = SizeMode.Exact

    override suspend fun provideGlance(
        context: Context,
        id: GlanceId,
    ) {
        val summary = WidgetCredentialsStore.getCachedSummary(context)
        provideContent {
            GlanceTheme {
                WidgetContent(context = context, summary = summary)
            }
        }
    }
}

@Composable
private fun WidgetContent(
    context: Context,
    summary: WidgetCredentialsStore.CachedSummary,
) {
    val addEntryIntent =
        Intent(Intent.ACTION_VIEW, Uri.parse("correlcore://entries/new")).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            setPackage(context.packageName)
        }

    val bg =
        ColorProvider(
            day = Color(0xFFF4F2FF),
            night = Color(0xFF1C1830),
        )
    val primary =
        ColorProvider(
            day = Color(0xFF3D3470),
            night = Color(0xFFE8E4FF),
        )
    val muted =
        ColorProvider(
            day = Color(0xFF6B6588),
            night = Color(0xFFB0A9C9),
        )
    val accent =
        ColorProvider(
            day = Color(0xFF5B4FC7),
            night = Color(0xFF9B8CFF),
        )

    Column(
        modifier =
            GlanceModifier
                .fillMaxSize()
                .background(bg)
                .padding(12.dp),
        verticalAlignment = Alignment.Vertical.CenterVertically,
        horizontalAlignment = Alignment.Horizontal.Start,
    ) {
        Text(
            text = "CorrelCore",
            style =
                TextStyle(
                    color = muted,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Medium,
                ),
        )
        Spacer(modifier = GlanceModifier.height(4.dp))

        when (summary.status) {
            WidgetCredentialsStore.STATUS_SIGNED_OUT -> {
                Text(
                    text = "Sign in to see mood",
                    style =
                        TextStyle(
                            color = primary,
                            fontSize = 18.sp,
                            fontWeight = FontWeight.Bold,
                        ),
                )
            }
            else -> {
                val headline =
                    when {
                        !summary.hasEntry -> "No entry yet"
                        summary.moodAvg7d != null ->
                            String.format("%.1f", summary.moodAvg7d)
                        else -> "—"
                    }
                val subtitle =
                    when {
                        !summary.hasEntry && summary.moodAvg7d != null ->
                            "7-day avg ${String.format("%.1f", summary.moodAvg7d)}"
                        summary.hasEntry && summary.moodAvg7d != null ->
                            "7-day mood average"
                        summary.status == WidgetCredentialsStore.STATUS_ERROR ->
                            "Update failed — retry soon"
                        summary.status == WidgetCredentialsStore.STATUS_LOADING ->
                            "Updating…"
                        else -> "Mood"
                    }

                Text(
                    text = headline,
                    style =
                        TextStyle(
                            color = primary,
                            fontSize = 28.sp,
                            fontWeight = FontWeight.Bold,
                        ),
                )
                Spacer(modifier = GlanceModifier.height(2.dp))
                Text(
                    text = subtitle,
                    style = TextStyle(color = muted, fontSize = 12.sp),
                )
            }
        }

        Spacer(modifier = GlanceModifier.height(8.dp))

        Row(
            modifier = GlanceModifier.fillMaxWidth(),
            verticalAlignment = Alignment.Vertical.CenterVertically,
        ) {
            Text(
                text = "+ Add entry",
                style =
                    TextStyle(
                        color = accent,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold,
                    ),
                modifier = GlanceModifier.clickable(actionStartActivity(addEntryIntent)),
            )
            Spacer(modifier = GlanceModifier.width(12.dp))
            if (summary.updatedAtMs > 0L) {
                val stamp =
                    DateFormat.getTimeInstance(DateFormat.SHORT)
                        .format(Date(summary.updatedAtMs))
                Text(
                    text = "Updated $stamp",
                    style = TextStyle(color = muted, fontSize = 11.sp),
                )
            }
        }
    }
}

class CorrelCoreWidgetReceiver : GlanceAppWidgetReceiver() {
    override val glanceAppWidget: GlanceAppWidget = CorrelCoreWidget()

    override fun onEnabled(context: Context) {
        super.onEnabled(context)
        // First instance placed — force, since it may not be visible to
        // AppWidgetManager at this point yet.
        WidgetRefreshWorker.enqueueImmediate(context, force = true)
    }

    override fun onDisabled(context: Context) {
        super.onDisabled(context)
        // Last instance removed — stop the 15-minute poll (#446).
        WidgetRefreshWorker.cancelPeriodic(context)
    }
}
