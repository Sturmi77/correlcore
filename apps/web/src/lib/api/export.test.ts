import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./client', () => ({
  apiBlob: vi.fn(),
}));

import { apiBlob } from './client';
import { downloadExport, exportFilename } from './export';

beforeEach(() => {
  vi.clearAllMocks();
});

describe('export API client', () => {
  it('builds stable local filenames', () => {
    expect(exportFilename('zip', new Date('2026-05-09T12:00:00'))).toBe(
      'moodsync-export-2026-05-09.zip'
    );
  });

  it('uses canonical ZIP endpoint', async () => {
    vi.mocked(apiBlob).mockResolvedValueOnce(new Blob());
    await downloadExport('zip');
    expect(apiBlob).toHaveBeenCalledWith('/user/export');
  });

  it('uses convenience JSON/CSV endpoints', async () => {
    vi.mocked(apiBlob).mockResolvedValue(new Blob());
    await downloadExport('json');
    await downloadExport('csv');
    expect(apiBlob).toHaveBeenNthCalledWith(1, '/export/json');
    expect(apiBlob).toHaveBeenNthCalledWith(2, '/export/csv');
  });
});
