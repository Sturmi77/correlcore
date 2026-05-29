# M13 Notes — Photo & Media

Last updated: 2026-05-29

Photo and media integration was moved from the former M6 slot to **M13**
(post-M10 selfhost v1.0 and post-M12 SaaS) so core tracking, insights, and
deployment paths ship without photo storage complexity first.

## Scope (M13)

- Local photo upload to MinIO with mandatory server-side EXIF strip (GPS,
  biometric metadata)
- Thumbnail gallery per day entry
- Pre-signed URL access model (no direct public MinIO exposure)
- Export ZIP includes populated `photos` section
- Account delete cascades to MinIO objects

## Out of scope for M13 exit (follow-up / backlog)

- Immich reference integration (asset_id + thumbnail proxy) — optional M13+
- End-to-end client-side encryption for photos (see ADR-0005 backlog)

## Prerequisites

- M10 public selfhost release complete (or explicit product decision to ship
  photos earlier on private instances only)
- MinIO bucket policy and SSE-S3 verified in production compose
- DSGVO checkpoints in `docs/DSGVO.md` § M13

## Canonical references

- [`docs/DESIGN_DOCUMENT.md`](DESIGN_DOCUMENT.md#m13--fotos--medien-post-saas)
- [`docs/DSGVO.md`](DSGVO.md) — M13 photo checkpoints
- [`docs/DATA_EXPORT_FORMAT.md`](DATA_EXPORT_FORMAT.md) — `photos` array shape
