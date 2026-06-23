<script context="module" lang="ts">
  import type { UiDataStateKind } from '$lib/ui/surfaceContract';

  export type DataStateKind = UiDataStateKind;
</script>

<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import EmptyState from './EmptyState.svelte';
  import InlineAlert from './InlineAlert.svelte';
  import Panel from './Panel.svelte';

  export let state: DataStateKind = 'ready';
  export let loadingText = 'Loading...';
  export let error = '';
  export let emptyTitle = '';
  export let emptyBody = '';
  export let offlineTitle = '';
  export let offlineBody = '';
  export let partialMessage = '';
  export let retryLabel = '';
  export let actionTestId = '';
  export let testId: string | undefined = undefined;

  const dispatch = createEventDispatcher<{ retry: void }>();
</script>

{#if state === 'loading'}
  <Panel aria-busy="true" data-testid={testId} variant="bordered">
    <p class="data-state__text">{loadingText}</p>
  </Panel>
{:else if state === 'error'}
  <InlineAlert
    variant="error"
    message={error}
    actionLabel={retryLabel}
    {actionTestId}
    {testId}
    on:action={() => dispatch('retry')}
  />
{:else if state === 'empty'}
  <EmptyState title={emptyTitle} body={emptyBody} {testId} />
{:else if state === 'offline'}
  <EmptyState title={offlineTitle} body={offlineBody} {testId} />
{:else if state === 'partial'}
  <div class="data-state__partial" data-testid={testId}>
    <InlineAlert variant="warning" message={partialMessage} />
    <slot />
  </div>
{:else}
  <slot />
{/if}

<style>
  .data-state__text {
    margin: 0;
    color: var(--color-text-muted);
    font-size: var(--text-sm);
  }

  .data-state__partial {
    display: grid;
    gap: var(--space-3);
  }
</style>
