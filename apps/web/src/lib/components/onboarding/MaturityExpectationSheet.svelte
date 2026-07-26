<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import BottomSheet from '$lib/components/common/BottomSheet.svelte';
  import Button from '$lib/components/common/Button.svelte';
  import MaturityExpectationContent from './MaturityExpectationContent.svelte';

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

  <MaturityExpectationContent headingId="maturity-expectation-title" />

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
</style>
