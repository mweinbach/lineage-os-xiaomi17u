# Device manifests

Do not add an active Xiaomi 17 Ultra device manifest until the exact codename,
device tree, matching common tree, kernel strategy, and vendor provenance are
verified. Empty manifests must not be presented as a buildable target.

The Evolution X platform manifest is fetched independently from its official
repository. Device-specific projects will be integrated here after validation.

The source wrapper currently rejects unreviewed `.repo/local_manifests` and
alternate manifest selectors. When the device projects are ready, extend that
validation with reviewed paths and pinned revisions before activating them.
Never delete existing local manifests to bypass a check.
