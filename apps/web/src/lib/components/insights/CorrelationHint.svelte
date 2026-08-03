<script lang="ts">
  import { _ } from 'svelte-i18n';

  /**
   * Persistent, single-line correlation hint (#632 Phase 2). One per statement
   * surface — the descriptive framing plus a ≤1-click link to the canonical
   * CorrelationDisclaimer page. Used where a statement is shown outside the
   * InsightFeed (which has its own header hint + i button): Home daily brief,
   * digest, history.
   */
</script>

<p class="correlation-hint" data-testid="correlation-hint">
  {$_('insights.feed.correlation_header')}
  <a href="/insights/disclaimer" data-testid="correlation-hint-link"
    >{$_('insights.feed.correlation_link')}</a
  >
</p>

<style>
  .correlation-hint {
    margin: var(--space-1) 0 0;
    font-size: var(--text-xs);
    color: var(--color-text-muted);
    line-height: 1.5;
  }

  .correlation-hint a {
    color: var(--color-primary);
    text-decoration: underline;
  }
</style>
