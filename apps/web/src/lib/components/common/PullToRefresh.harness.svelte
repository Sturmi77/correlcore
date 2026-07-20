<script lang="ts">
  import PullToRefresh from './PullToRefresh.svelte';

  export let disabled = false;
  export let withIgnoreTarget = false;

  let scrollElement: HTMLElement | null = null;
</script>

<div bind:this={scrollElement} data-testid="ptr-scroll" style="overflow:auto;height:200px">
  <PullToRefresh {scrollElement} {disabled}>
    {#if withIgnoreTarget}
      <div data-ptr-ignore data-testid="ptr-ignore-target">
        <p>sheet</p>
      </div>
    {:else}
      <p>content</p>
    {/if}
  </PullToRefresh>
</div>
