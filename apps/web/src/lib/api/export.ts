import { apiBlob } from './client';

export type ExportKind = 'zip' | 'json' | 'csv';

export function exportFilename(kind: ExportKind, date = new Date()): string {
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  const dd = String(date.getDate()).padStart(2, '0');
  return `correlcore-export-${yyyy}-${mm}-${dd}.${kind}`;
}

export async function downloadExport(kind: ExportKind): Promise<Blob> {
  if (kind === 'zip') return apiBlob('/user/export');
  return apiBlob(`/export/${kind}`);
}

export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
