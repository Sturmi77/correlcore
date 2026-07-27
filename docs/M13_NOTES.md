# M13 Notes — Photo & Media

Last updated: 2026-07-16

Photo and media integration was moved from the former M6 slot to **M13**
(post-M10 selfhost v1.0 and post-M12 SaaS) so core tracking, insights, and
deployment paths ship without photo storage complexity first.

## Deferral status (post-v1.0)

**End-user photo storage is not shipped.** A security-oriented API stub exists
so M13 can land without redesigning the contract:

| Piece                                               | Status                                                                                            |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `POST /api/v1/media/photos`                         | Landed — auth required, MIME/size guards                                                          |
| Pillow EXIF strip (GPS / biometric metadata)        | Landed — `app/services/exif_strip.py` + tests                                                     |
| Object storage persist (`stored`)                   | Always `false` — MinIO client not wired                                                           |
| Frontend upload UI                                  | None                                                                                              |
| MinIO in compose                                    | Removed until M13; production validates `MINIO_SECRET_KEY` only when `PHOTOS_ENABLED=true` (#543) |
| Thumbnail gallery / pre-signed URLs / export photos | Remaining M13 exit                                                                                |

Operators and agents: do not advertise photo gallery / MinIO as a live
selfhost feature. Track completion under this milestone only.

Open decisions tracker: [`docs/quality/OPEN_DECISIONS_AND_BACKLOG_2026-07-16.md`](quality/OPEN_DECISIONS_AND_BACKLOG_2026-07-16.md).

## Scope (M13 exit)

- Local photo upload to MinIO with mandatory server-side EXIF strip (GPS,
  biometric metadata) — **replace the stub with real storage**
- Thumbnail gallery per day entry (web UI)
- Pre-signed URL access model (no direct public MinIO exposure)
- Export ZIP includes populated `photos` section
- Account delete cascades to MinIO objects
- Align env naming (`MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` vs compose `MINIO_ROOT_*`)

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
- Stub endpoint: `backend/app/api/v1/endpoints/media.py`
