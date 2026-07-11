<script lang="ts">
  import { _ } from 'svelte-i18n';
  import Button from '$lib/components/common/Button.svelte';
  import Panel from '$lib/components/common/Panel.svelte';
  import ScreenHeader from '$lib/components/common/ScreenHeader.svelte';

  const sectionKeys = [
    'controller',
    'data',
    'legal',
    'security',
    'rights',
    'sharing',
    'retention',
    'changes',
    'contact',
  ] as const;
</script>

<svelte:head>
  <title>{$_('privacy.page_title')} — {$_('app.name')}</title>
</svelte:head>

<div class="privacy-page">
  <ScreenHeader title={$_('privacy.page_title')} subtitle={$_('privacy.page_subtitle')} />

  <Panel>
    <p class="privacy-page__intro">{$_('privacy.intro')}</p>

    {#each sectionKeys as key}
      <section class="privacy-page__section" data-testid={`privacy-section-${key}`}>
        <h2>{$_(`privacy.sections.${key}.heading`)}</h2>
        <p>{$_(`privacy.sections.${key}.body`)}</p>
      </section>
    {/each}

    <div class="privacy-page__actions">
      <Button href="/settings" variant="secondary" data-testid="privacy-back-settings">
        {$_('privacy.back_settings')}
      </Button>
    </div>
  </Panel>
</div>

<style>
  .privacy-page {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
    padding: var(--space-4);
    max-width: 48rem;
    margin: 0 auto;
  }

  .privacy-page__intro {
    margin: 0 0 var(--space-4);
    color: var(--color-text-muted);
    line-height: 1.6;
  }

  .privacy-page__section {
    margin-bottom: var(--space-5);
  }

  .privacy-page__section h2 {
    margin: 0 0 var(--space-2);
    font-size: var(--text-lg);
  }

  .privacy-page__section p {
    margin: 0;
    color: var(--color-text-muted);
    line-height: 1.6;
    white-space: pre-line;
  }

  .privacy-page__actions {
    margin-top: var(--space-2);
  }
</style>
