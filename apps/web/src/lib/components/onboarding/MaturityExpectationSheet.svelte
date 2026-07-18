<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import BottomSheet from '$lib/components/common/BottomSheet.svelte';
  import Button from '$lib/components/common/Button.svelte';
  import {
    MATURITY_INTRO_PHASES,
    MATURITY_INTRO_THUMBS,
  } from '$lib/utils/maturityExpectationIntro';

  export let open = false;

  const dispatch = createEventDispatcher<{ close: void; dismiss: void }>();

  function onSheetClose() {
    // Backdrop / Escape also count as dismiss so the sheet does not re-open.
    dispatch('dismiss');
  }

  function onCta() {
    dispatch('dismiss');
  }
</script>

<BottomSheet
  {open}
  labelledBy="maturity-expectation-title"
  testId="maturity-expectation-sheet"
  closeAriaLabel={$_('onboarding.maturity_intro.close')}
  on:close={onSheetClose}
>
  <header class="maturity-intro__header">
    <h2 id="maturity-expectation-title">{$_('onboarding.maturity_intro.title')}</h2>
  </header>

  <p class="maturity-intro__intro">{$_('onboarding.maturity_intro.intro')}</p>

  <ol class="maturity-intro__phases">
    {#each MATURITY_INTRO_PHASES as phase, index}
      <li class="maturity-intro__phase" data-testid={`maturity-intro-phase-${phase}`}>
        <img
          class="maturity-intro__thumb"
          src={MATURITY_INTRO_THUMBS[phase]}
          alt={$_('onboarding.maturity_intro.thumb_alt', { values: { n: index + 1 } })}
          width="72"
          height="72"
          loading="lazy"
          decoding="async"
        />
        <div class="maturity-intro__copy">
          <div class="maturity-intro__title-row">
            <span class="maturity-intro__index" aria-hidden="true">{index + 1}</span>
            <div>
              <h3>{$_(`maturity.${phase}.label`)}</h3>
              <p class="maturity-intro__range">{$_(`maturity.${phase}.range`)}</p>
            </div>
          </div>
          <p>{$_(`onboarding.maturity_intro.${phase}.expectation`)}</p>
          <p class="maturity-intro__example">{$_(`onboarding.maturity_intro.${phase}.example`)}</p>
        </div>
      </li>
    {/each}
  </ol>

  <Button
    type="button"
    variant="primary"
    size="md"
    fullWidth
    data-testid="maturity-expectation-cta"
    on:click={onCta}
  >
    {$_('onboarding.maturity_intro.cta')}
  </Button>
  <p class="maturity-intro__footer">{$_('onboarding.maturity_intro.footer')}</p>
</BottomSheet>

<style>
  .maturity-intro__header {
    margin-bottom: var(--space-3);
  }

  .maturity-intro__header h2 {
    margin: 0;
    font-size: var(--text-lg);
    font-weight: 700;
  }

  .maturity-intro__intro,
  .maturity-intro__phase p,
  .maturity-intro__footer {
    margin: 0;
    color: var(--color-text-muted);
    line-height: 1.5;
  }

  .maturity-intro__intro {
    margin-bottom: var(--space-4);
  }

  .maturity-intro__phases {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding: 0;
    margin: 0 0 var(--space-4);
    list-style: none;
  }

  .maturity-intro__phase {
    display: grid;
    grid-template-columns: 4.5rem 1fr;
    gap: var(--space-3);
    padding: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    background: var(--color-surface-chart-bg);
  }

  .maturity-intro__thumb {
    width: 4.5rem;
    height: 4.5rem;
    object-fit: cover;
    border-radius: var(--radius-md);
    border: 1px solid var(--color-border);
    background: var(--color-surface-offset);
  }

  .maturity-intro__copy {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
    min-width: 0;
  }

  .maturity-intro__title-row {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: var(--space-2);
    align-items: start;
  }

  .maturity-intro__index {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.75rem;
    height: 1.75rem;
    border-radius: var(--radius-full);
    background: var(--color-primary-highlight);
    color: var(--color-primary);
    font-size: var(--text-sm);
    font-weight: 700;
  }

  .maturity-intro__phase h3 {
    margin: 0;
    font-size: var(--text-sm);
    font-weight: 700;
    color: var(--color-text);
  }

  .maturity-intro__range {
    font-size: var(--text-xs);
  }

  .maturity-intro__example {
    color: var(--color-text);
    font-size: var(--text-sm);
  }

  .maturity-intro__footer {
    margin-top: var(--space-3);
    text-align: center;
    font-size: var(--text-xs);
  }
</style>
