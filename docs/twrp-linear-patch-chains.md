# Explicit linear patch chains

The source tools support explicitly linked patches without rewriting an approved
predecessor. Each source transition still requires reviewed controls, an exact
starting state and a recorded result. The first twenty-three patch entries and
payloads form an unchanged validation baseline. The schema remains version 1.
Every real successor needs its own reviewed payload and metadata; test fixtures
do not authorize source changes.

A file may appear in more than one patch only when every later file record has
`predecessor_patch_id` naming the immediately preceding patch for that exact
owner and path. Its before SHA256, byte count and Git blob must exactly equal
the predecessor's after values. Every participating record needs explicit
before/after Git blobs and full matching Git index headers. A first touch must
not have the predecessor field. The owner and original pinned base never change.

For example, a synthetic successor record could include:

```json
{
  "path": "Android.bp",
  "predecessor_patch_id": "0001-synthetic-resource-restoration",
  "before_sha256": "<exact predecessor after SHA256>",
  "before_size_bytes": 123,
  "before_git_blob": "<exact predecessor after Git blob>",
  "after_sha256": "<reviewed successor after SHA256>",
  "after_size_bytes": 456,
  "after_git_blob": "<reviewed successor after Git blob>"
}
```

The placeholders are not valid controls. Other files in that patch can be
first touches without predecessors. The implementation rejects implicit
overlap, orphan/self/forward/skipped/other-file predecessors, branches,
duplicate paths, changed bases, incomplete blobs and reversions to the original
file. Existing path, payload, mode, owner, origin, source selection and target
checks remain. An old queue must stay an exact unchanged prefix; without an
append even its raw series digest must remain unchanged.

Queues without chains retain their existing validation and transition path.
For a queue with a chain, preparation or revision reads each original regular
Git blob at the pinned commit, bounds and hashes the raw bytes, and creates an
ordinary scratch copy with canonical modes. Git runs there with an empty HOME,
no inherited GIT overrides, no global/system configuration, no hooks, no source
attributes, and no source index or hardlinks. The whole queue is rehearsed in
global order, then reversed in reverse order. Every boundary must have exact
bytes, blobs and modes and no undeclared files. The old receipt boundary must
match independently verified live bytes.

A queue that would copy any `.gitattributes` file into that scratch tree is
rejected before rehearsal. Disabling the global attributes file alone does not
disable directory attributes; the tooling does not import that behavior.

Both forward and reverse apply use `--whitespace=error-all`. A patch that removes
invalid whitespace from the original source may therefore be rejected when
reverse rehearsal tries to restore it. This is intentional failure behavior;
the tooling does not relax Git checks or edit the original baseline.

Only after the complete rehearsal passes may the live suffix run. Each step
checks both control bundles, the still-active old receipt, archived evidence,
the complete expected source prefix and canonical modes. It writes a separate
intent before the forward apply and a completion only after the postimage and
owner checks pass. Initial source bytes are archived once; repeated after-images
use numeric `steps/0001/source-after/...` paths. Patch IDs remain JSON data and
never form archive paths. The final receipt is still compile-only, and does not
claim graph, image, SELinux runtime or phone verification.

Dependency fetching still uses the explicit previous control bundle and active
receipt. It never applies patches or adopts a proposed successor's matching
bytes. Already prepared owners cannot be recreated as clean fetches. The new
shared plan counts unique modified paths while preserving supplemental root,
origin, HEAD, raw NUL status, ignored-file and index-flag checks.

If a step fails, original output/cache, initial backups, step evidence and the
old receipt remain. Source changes already made also remain. There is no live
reverse, reset, force option, inferred resume or automatic rollback. A retry
after a partial transition fails the old-state check; a completed retry verifies
the committed full state without applying anything.

The tooling preserves the existing durability contract. Exclusive writes
and close-before-apply evidence protect against ordinary process failures; they
do not promise power-loss durability. It does not add fsync, an atomic
no-replace first-receipt publisher, or filesystem transactions. Initial
preparation still publishes with the existing exclusive report writer; revision
retains its checked pending file, last old-byte comparison and atomic replace.
The operation lock coordinates cooperating writers, not arbitrary outside
processes. Base verification retains its existing, narrower index/ignored-file
coverage; the supplemental verifier's stronger checks are not falsely claimed
for all base projects.

Tests use synthetic public text, the Python standard library and mocked
processes. Independent real Git checks live only in ignored prototype reports.
The composed synthetic resource/auth/SELinux fixture checks interactions in its
own final bytes; it is not proof that a future real packaging patch preserves
the actual recovery semantics. Before admission, that concrete composed patch
needs review, the full frozen offline suite, strict graph/build validation and
later artifact checks. No device, private key or proprietary content is used.

The integration tests freeze the complete first-23 queue at commit
`738fc3468f79c31926a488e4f3506e44dcd01fa6`; no successor is added to that queue.
Fixture-only tests model the existing resource change at slot 20 followed by
the packaging successor at slot 24, across unrelated slots 21 through 23. A
second synthetic fixture models a later USB-only transport change following
the authentication change at slot 4. The authentication and root restrictions
are explicitly retained in that synthetic final text. This checks transition
and failure handling, not the security semantics of an unreviewed real ADB
payload. The exact currently approved ID list remains a separate test and must
be updated only when a concrete successor is admitted.
