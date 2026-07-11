<script lang="ts">
  import { _ } from 'svelte-i18n';
  import Button from '$lib/components/common/Button.svelte';
  import LegalFooter from '$lib/components/common/LegalFooter.svelte';
  import Panel from '$lib/components/common/Panel.svelte';
  import ScreenHeader from '$lib/components/common/ScreenHeader.svelte';
  import { auth } from '$lib/stores/auth';

  const sectionKeys = [
    'operator',
    'contact',
    'register',
    'content',
    'dispute',
    'liability',
    'software',
  ] as const;
</script>

<svelte:head>
  <title>{$_('impressum.page_title')} — {$_('app.name')}</title>
</svelte:head>

<div class="impressum-page" data-testid="impressum-page">
  <ScreenHeader title={$_('impressum.page_title')} subtitle={$_('impressum.page_subtitle')} />

  <Panel>
    <p class="impressum-page__intro">{$_('impressum.intro')}</p>

    {#each sectionKeys as key}
      <section class="impressum-page__section" data-testid={`impressum-section-${key}`}>
        <h2>{$_(`impressum.sections.${key}.heading`)}</h2>
        <p>{$_(`impressum.sections.${key}.body`)}</p>
      </section>
    {/each}

    <div class="impressum-page__actions">
      {#if $auth.status === 'authenticated'}
        <Button href="/settings" variant="secondary" data-testid="impressum-back-settings">
          {$_('privacy.back_settings')}
        </Button>
      {:else}
        <Button href="/" variant="secondary" data-testid="impressum-back-home">
          {$_('impressum.back_home')}
        </Button>
      {/if}
    </div>
  </Panel>

  <LegalFooter />
</div>

<style>
  .impressum-page {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
    padding: var(--space-4);
    max-width: 48rem;
    margin: 0 auto;
  }

  .impressum-page__intro {
    margin: 0 0 var(--space-4);
    color: var(--color-text-muted);
    line-height: 1.6;
  }

  .impressum-page__section {
    margin-bottom: var(--space-5);
  }

  .impressum-page__section h2 {
    margin: 0 0 var(--space-2);
    font-size: var(--text-lg);
  }

  .impressum-page__section p {
    margin: 0;
    color: var(--color-text-muted);
    line-height: 1.6;
    white-space: pre-line;
  }

  .impressum-page__actions {
    margin-top: var(--space-2);
  }
</style>
