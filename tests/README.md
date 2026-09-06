# Workspace checks

Use `make test-current` while iterating on the working Package7 baseline. Its
explicit selection in `Makefile` covers the source lock, working76 recovery and
ROM inputs, boot/DLKM construction, signing, image layout, target-files delivery,
the Package7 APK corrections, bundle verification and read-only collectors.
Add the affected module's tests when working outside that selection:

```sh
python3 -m unittest discover -s tests -p 'test_camera_dependencies.py' -v
```

Run `make test` once before completing a change. It runs full offline discovery,
about four minutes for 4820 checks, then the Linux setup script's syntax check:

```sh
python3 -m unittest discover -s tests -v
```

Historical bring-up and source-experiment checks remain in full discovery. They
preserve the contracts behind retained tooling and dated evidence; they do not
select an old build path. Keeping their small source files avoids losing useful
regression checks while the focused target makes everyday iteration shorter.

`AGENTS.md` describes what a check has to do to belong here: exercise a tool in
`scripts/` or `tools/`, recompute a hash, link or total from the artifact on
disk, or pin a measured value that carries a build decision. Shared walkers and
record-safety helpers live in `support.py`, which discovery does not collect.

These tests use Python's standard library and mocked process/device calls. They
do not contact the phone, run a full Android build or qualify device features.
Passing them does not replace checking the resulting images or testing the
specific fix on the device under the user's authorization.
