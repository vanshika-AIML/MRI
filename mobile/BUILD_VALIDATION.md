# Mobile build validation

The Android client was checked with Flutter 3.47.7 / Dart 3.13.5, Android SDK 36, and the Android Studio bundled JDK 25.0.3.

The Phase 15 verification run completed the following commands successfully from `mobile/`:

| Check | Result |
|---|---|
| `flutter pub get` | Passed |
| `dart format --output=none --set-exit-if-changed .` | Passed |
| `flutter analyze` | Passed with no issues |
| `flutter test` | Passed |
| `flutter build apk --debug` | Passed |

The connected Android integration workflow also passed against the local API and database: account registration and login, synthetic scan selection/upload, analysis, stored report retrieval, and logout. See the [release verification report](../docs/verification/RELEASE_REPORT.md) and its phase evidence.

Only Android was built and exercised. This checkout has no iOS host project; iOS, physical-device networking, release signing, and store distribution remain unverified. The debug build may show third-party Flutter/Kotlin and Java/Gradle warnings described in the mobile README; they were not suppressed or hidden.

## Follow-up research segmentation UI

The client now explicitly selects the nonclinical FLAIR segmentation mode, parses its provenance, renders the returned overlay preview, and offers the compressed NIfTI mask for download. The updated verification run completed `flutter analyze` with no issues, `flutter test` with 9 passing tests, and `flutter build apk --debug`. A live model-to-API workflow on an Android device/emulator has not been run; the backend's authenticated model/report workflow is verified separately in [the Phase 16–23 tracker](../docs/PHASE_16_23_EXECUTION.md).
