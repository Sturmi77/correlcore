import type { HandleClientError } from '@sveltejs/kit';

import {
  captureClientException,
  initClientErrorTracking,
} from '$lib/observability/errorTracking.client';

initClientErrorTracking();

export const handleError: HandleClientError = ({ error }) => {
  captureClientException(error);
  return { message: 'Something went wrong' };
};
