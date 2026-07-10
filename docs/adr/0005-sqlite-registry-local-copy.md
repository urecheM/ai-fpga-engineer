# ADR 0005 — SQLite registry with local working copy

## Status
Accepted

## Context
SQLite requires POSIX locking that some networked/fuse filesystems do not
provide, causing "disk I/O error" when the DB lives on a mounted directory.

## Decision
`ExperimentDB` operates on a local temp-dir working copy and mirrors it to the
destination on each commit and on close.

## Consequences
+ The registry is portable across filesystems.
− A final `close()` (or context exit) is required to persist the last writes.
