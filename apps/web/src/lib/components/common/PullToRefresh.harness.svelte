<script lang="ts">
  import PullToRefresh from './PullToRefresh.svelte';

  export let disabled = false;

  let scrollElement: HTMLElement | null = null;
</script>

<div bind:this={scrollElement} data-testid="ptr-scroll" style="overflow:auto;height:200px">
  <PullToRefresh {scrollElement} {disabled}>
    <p>content</p>
  </PullToRefresh>
</div>
