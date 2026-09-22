/** One request generation per independently refreshed view. */
export class RequestGeneration {
  private active: { context: string; controller: AbortController } | null = null;

  begin(context: string): { signal: AbortSignal; isCurrent: () => boolean } {
    this.cancel();
    const generation = { context, controller: new AbortController() };
    this.active = generation;
    return {
      signal: generation.controller.signal,
      isCurrent: () => this.active === generation && !generation.controller.signal.aborted,
    };
  }

  cancel(): void {
    this.active?.controller.abort();
    this.active = null;
  }
}
