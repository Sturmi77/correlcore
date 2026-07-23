/**
 * Session-expired notifier — breaks the api client ↔ auth store cycle.
 *
 * The API client calls `notifySessionExpired()` after a definitive auth
 * rejection (failed refresh). The auth store registers a handler that flips
 * the UI to anonymous so the layout guard can send the user to login.
 */

type SessionExpiredHandler = () => void;

let handler: SessionExpiredHandler | null = null;

export function onSessionExpired(next: SessionExpiredHandler): void {
  handler = next;
}

export function notifySessionExpired(): void {
  handler?.();
}

/** Test-only. */
export function _resetSessionExpiredHandlerForTests(): void {
  handler = null;
}
