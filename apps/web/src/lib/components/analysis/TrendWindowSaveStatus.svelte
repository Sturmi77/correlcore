<script lang="ts">
  import { _ } from 'svelte-i18n';
  import { trendWindowPreference } from '$lib/stores/trendWindowPreference';
</script>

{#if $trendWindowPreference === 'error'}
  <div class="range-save-status" role="alert" data-testid="trend-window-save-error">
    <span>{$_('trends.range_save_error')}</span>
    <button type="button" on:click={() => trendWindowPreference.retry()}>
      {$_('trends.range_retry')}
    </button>
  </div>
{/if}

<style>
  .range-save-status {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: var(--space-2);
    color: var(--color-error);
    font-size: var(--text-sm);
  }
  button {
    border: 0;
    background: none;
    color: inherit;
    text-decoration: underline;
    cursor: pointer;
    font: inherit;
  }
</style>
