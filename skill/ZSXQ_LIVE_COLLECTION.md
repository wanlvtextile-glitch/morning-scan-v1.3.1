# ZSXQ Live Collection

## Goal

For ZSXQ, collect all collectable content inside the requested time window first.
Do not apply early market filtering in the collector.

## Simulated Login

Use request-header replay with:

- `Authorization`
- `User-Agent`
- `X-Aduid`
- `X-Request-Id`
- `X-Signature`
- `X-Timestamp`
- `X-Version`
- optional `Cookie`

## Verified Pagination

For `v2/groups/{group_id}/topics`:

1. first page without `end_time`
2. take the last topic `create_time`
3. subtract `timestamp_offset_ms`
4. URL-encode the new `end_time`
5. request the next page with `&end_time=...`

Do not rely on `resp_data.end_time`.

## Important Fix

`end_time` must be URL-encoded.

Without encoding, pagination may silently return incomplete data.

## Collector Policy

- collect all text or attachment-resolvable topics inside the time window
- leave filtering to downstream analysis

## Current Verified Result

Window:

- `2026-05-11 12:00:00` to `15:00:00`

Result:

- raw in-window topics: `66`
- collected topics: `64`
- the remaining `2` were image-only posts without usable text or files
