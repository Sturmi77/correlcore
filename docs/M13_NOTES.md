# M13 Notes — Photo & Media

Last updated: 2026-07-15

Photo and media integration was moved from the former M6 slot to **M13**
(post-M10 selfhost v1.0 and post-M12 SaaS) so core tracking, insights, and
deployment paths ship without photo storage complexity first.

## Foundation status (landed #28)

Server-side EXIF strip is available now — before full MinIO/gallery scope:

| Piece | Status |
| ----- | ------ |
| `POST /api/v1/media/photos` | Landed — auth required, MIME/size guards |
| Pillow EXIF strip (GPS / biometric metadata) | Landed — `app/services/exif_strip.py` + tests |
| Object storage persist | **Stub** — response `stored: false` until MinIO client wiring |
| Thumbnail gallery / pre-signed URLs / export photos | Remaining M13 exit |

## Scope (M13 exit)

- Local photo upload to MinIO with mandatory server-side EXIF strip (GPS,
  biometric metadata) — strip done; MinIO persist pending
- Thumbnail gallery per day entry
- Pre-signed URL access model (no direct public MinIO exposure)
- Export ZIP includes populated `photos` section
- Account delete cascades to MinIO objects

## Out of scope for M13 exit (follow-up / backlog)

- Immich reference integration (asset_id + thumbnail proxy) — optional M13+
- End-to-end client-side encryption for photos (see ADR-0005 backlog)

## Prerequisites

- M10 public selfhost release complete — **done**
- MinIO bucket policy and SSE-S3 verified in production compose (for persist path)
- DSGVO checkpoints in `docs/DSGVO.md` § M13

## Canonical references

- [`docs/DESIGN_DOCUMENT.md`](DESIGN_DOCUMENT.md#m13--fotos--medien-post-saas)
- [`docs/DSGVO.md`](DSGVO.md) — M13 photo checkpoints
- [`docs/DATA_EXPORT_FORMAT.md`](DATA_EXPORT_FORMAT.md) — `photos` array shape
- [`docs/API.md`](API.md) §10b — `/media/photos`
