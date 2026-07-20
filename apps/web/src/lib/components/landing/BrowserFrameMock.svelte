<script lang="ts">
  /** Lightweight browser-chrome mock for marketing product shots. */
  export let address = 'app.correlcore.example/insights';
</script>

<div class="cc-frame" data-testid="landing-browser-frame">
  <div class="cc-frame__bar" aria-hidden="true">
    <span class="cc-frame__dot"></span>
    <span class="cc-frame__dot"></span>
    <span class="cc-frame__dot"></span>
    <span class="cc-frame__addr">{address}</span>
  </div>
  <div class="cc-frame__body">
    <slot />
  </div>
</div>

<style>
  .cc-frame {
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
    overflow: hidden;
    text-align: left;
  }

  .cc-frame__bar {
    display: flex;
    align-items: center;
    gap: var(--space-1);
    padding: var(--space-2) var(--space-3);
    border-bottom: 1px solid var(--color-border);
    background: var(--color-surface-2);
  }

  .cc-frame__dot {
    width: 0.5rem;
    height: 0.5rem;
    border-radius: var(--radius-full);
    background: var(--color-border);
    display: inline-block;
  }

  .cc-frame__addr {
    margin-left: var(--space-2);
    font-size: var(--text-2xs);
    color: var(--color-text-faint);
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  }

  .cc-frame__body {
    padding: var(--space-4);
  }
</style>
