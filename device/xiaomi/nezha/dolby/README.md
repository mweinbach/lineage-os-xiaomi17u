# Nezha Dolby test controller

Opt-in, independently authored platform-source controller for the **existing**
vendor Dolby effect. This is not a Dolby implementation or a stock app transplant.
It ships no proprietary files, libraries, native service, SELinux exceptions or
signature-verification bypass. The Soong platform certificate grants the declared
signature-level audio permission through normal platform signing.

Integrators may select `NezhaDolbyController` in `PRODUCT_PACKAGES` explicitly.
It belongs in system-ext and requires platform APIs; a public-SDK build cannot
resolve the hidden `AudioEffect` parameter methods. Do not silently enable it as
a replacement for missing vendor effect/HAL components.

Opening the activity creates UI only. **Inspect / refresh effect** attaches the
vendor effect at priority 0, session 0, requires control and reads current state.
The enable switch and profile Apply button are the only write entry points.
Every change validates status and reads state back. Invalid lengths, unavailable
control, unexpected values and mismatched readbacks fail visibly. No boot receiver,
background service, saved setting restoration, route listener or automatic write
exists. Leaving the screen releases the handle; retention of a setting thereafter
is unproven and the UI says so. Tests do not establish audible output, route
behavior, startup persistence or hardware functionality.

The small protocol uses effect type `ec7178ec-e5e1-4432-a3f4-4657e6795210` and
implementation `9d4921da-8225-4f29-aefa-39537a04bcaa`. Query keys are parameter + 5;
the 12-byte little-endian query buffer is `[parameter, 0, 0]`. A query must return
at least four bytes before the first little-endian integer is read. Writes use
key 5 and `[parameter, 1, value]`. Writable parameters are enable (0) and current
profile (`0x0a000000`); profile count (`0x03000000`) is read-only. Enable changes
also call the framework effect enable API. A partial failure is not rolled back
or reported as success: the user must explicitly inspect again.

Profile ID/name facts were inspected from the exact factory XML in private stock
evidence: 0 Dynamic, 1 Movie, 2 Music, 3 Custom, 4 Mobility_default,
5 Mobility_on_the_go, 6 Mobility_commute, 7 Mobility_travel, 8 Voice. No XML tuning
tables or decompiled application implementation are included. Runtime counts are
bounded to 1–32; only reported IDs can be selected. Unknown IDs use numeric labels.
These static names are not a guarantee of runtime availability or behavior.

Run the focused host tests with:

```sh
python3 -m unittest discover -s tests -p 'test_dolby_controller.py' -v
```

The Python standard-library tests check the manifest/build boundaries and, when a
JDK is present, compile and exercise the actual protocol/controller sources against
an explicitly fake AudioEffect. That is host behavior proof, not a platform Soong
build, permission-grant proof or phone qualification.
