<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { capacitorNeedsApiBaseConfig, getApiBaseInputForDisplay } from '$lib/api/apiBase';
  import { isCapacitorBuild } from '$lib/api/platform';

  export let value = '';
  export let disabled = false;

  const show = isCapacitorBuild();
  let open = false;

  onMount(() => {
    if (!show) return;
    value = getApiBaseInputForDisplay();
    open = capacitorNeedsApiBaseConfig() || !value;
  });
</script>

{#if show}
  <details class="api-base" data-testid="auth-api-base" bind:open>
    <summary class="api-base__summary">{$_('auth.login.api_base_toggle')}</summary>
    <p class="api-base__hint">{$_('auth.login.api_base_hint')}</p>
    <label class="api-base__field">
      <span class="api-base__label">{$_('settings.app.api_base_label')}</span>
      <input
        type="url"
        class="input"
        bind:value
        placeholder={$_('settings.app.api_base_placeholder')}
        autocomplete="off"
        inputmode="url"
        {disabled}
        data-testid="auth-api-base-input"
      />
    </label>
  </details>
{/if}

<style>
  .api-base {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    padding: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface-2);
  }

  .api-base__summary {
    cursor: pointer;
    font-size: var(--text-sm);
    font-weight: 600;
    color: var(--color-text);
    list-style: none;
  }

  .api-base__summary::-webkit-details-marker {
    display: none;
  }

  .api-base__hint {
    margin: 0;
    font-size: var(--text-xs);
    opacity: 0.75;
    line-height: 1.4;
  }

  .api-base__field {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .api-base__label {
    font-size: var(--text-sm);
    font-weight: 500;
  }
</style>
