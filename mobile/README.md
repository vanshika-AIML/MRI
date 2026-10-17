# MRI Analysis Mobile Application (Flutter)

A cross-platform mobile application for **AI-Assisted MRI Image Enhancement and Abnormality Detection**, built with Flutter, Provider state management, and the clinical light design system.

---

## 1. Capabilities & Architecture

The mobile application connects directly to the existing FastAPI backend (`/api/v1`) and shares identical API contracts and data models with the web frontend:

- **State Management:** `Provider` (`AuthProvider`, `AnalysisProvider`)
- **Design System:** `ClinicalTheme` — Accessible, high-contrast, light clinical theme by default.
- **Authentication & Security:** Secure token storage via `flutter_secure_storage`, JWT bearer authorization headers, and role-based permissions (`viewer`, `radiologist`, `admin`).
- **MRI File Ingestion:** Validates supported formats (`.dcm`, `.nii`, `.nii.gz`, `.png`, `.jpg`, `.jpeg`, `.npy`, `.npz`) and enforces a 100MB file limit before upload.
- **Analysis mode:** Select the baseline heuristic pipeline or explicitly opt in to research FLAIR segmentation. The research mode requires sign-in, database persistence, a configured model, and a FLAIR NIfTI volume; it never silently falls back.
- **Pipeline Parameter Tuning:** Fine-tune normalization, soft-tissue enhancement (CLAHE), and abnormality detection thresholds for the baseline workflow.
- **Results & Provenance:** Visualizes baseline scores/findings or the research mask preview, predicted voxel count, pipeline duration, and NIfTI mask download.
- **Controlled Modification & Annotations:** Allows authorized radiologists to attach clinical observation notes with versioning and audit trails.
- **Mandatory Clinical Disclaimer:** Prominently displays safety notices disclaiming autonomous diagnostic validity.

Research-model behavior is unit/widget-tested and the Android debug APK builds successfully, but the model workflow has not been exercised on a physical Android device or emulator. iOS is not supported in this checkout.

---

## 2. Directory Structure

```
mobile/
├── pubspec.yaml                 # Dependencies and asset declarations
├── lib/
│   ├── main.dart                # Application entry point & MultiProvider setup
│   ├── core/
│   │   ├── constants.dart       # API routes, supported formats, limits, disclaimers
│   │   └── theme.dart           # Clinical Light Theme definition
│   ├── models/
│   │   ├── user.dart            # UserPublic & TokenResponse models
│   │   ├── analysis.dart        # AnalysisResponse, DetectedRegion, InputMetadata
│   │   └── annotation.dart      # AnnotationItem model with versioning
│   ├── services/
│   │   ├── api_client.dart      # Secure HTTP client with FlutterSecureStorage
│   │   ├── auth_service.dart    # Login, registration, profile, and token refresh
│   │   └── analysis_service.dart# Multipart inference uploads and annotations
│   ├── providers/
│   │   ├── auth_provider.dart   # Authentication session lifecycle provider
│   │   └── analysis_provider.dart# Analysis request & results provider
│   ├── screens/
│   │   ├── upload_screen.dart   # File selection, parameter tuning, upload trigger
│   │   ├── results_screen.dart  # Findings dashboard, annotations, provenance
│   │   ├── login_screen.dart    # Clinical sign-in interface
│   │   ├── register_screen.dart # Account creation with real-time validation
│   │   └── settings_screen.dart # Server URL configuration & account details
│   └── widgets/
│       ├── clinical_disclaimer.dart # Reusable mandatory clinical disclaimer
│       └── severity_badge.dart      # Standardized severity level badges
└── test/
    └── model_test.dart          # Unit tests verifying model parsing
```

---

## 3. Platform Prerequisites & Setup

### Environment Status
> [!NOTE]
> Android project files are included. Use `flutter doctor` to check the toolchain; `flutter config --android-sdk` is a one-time configuration command, and its editor restart reminder appears whenever it is repeated.

### Prerequisites
1. **Flutter SDK:** `>= 3.47.0`, Dart `>= 3.11.0` (validated with Flutter **3.47.7** / Dart **3.13.5**).
2. **Android Development:** Android Studio + Android SDK / Command Line Tools, Android Emulator or USB Debugging device.
3. **iOS Development (macOS only):** Xcode 15+, CocoaPods, iOS Simulator.

### Running the Application

1. **Install Dependencies:**
   ```bash
   cd mobile
   flutter pub get
   ```

2. **Run Unit Tests:**
   ```bash
   flutter test
   ```

3. **Run on Android Emulator:**
   The app defaults to `http://10.0.2.2:8000` (which maps to localhost on the host machine):
   ```bash
   flutter emulators
   flutter emulators --launch <emulator-id>
   flutter devices
   flutter run -d <android-device-id>
   ```

4. **iOS status (unverified):**
   This checkout currently contains Android platform scaffolding only. An iOS host project, macOS/Xcode build, signing, and simulator verification remain required before iOS support can be claimed. The intended simulator API address is shown below for future setup.
   The app defaults to `http://127.0.0.1:8000`:
   ```bash
   flutter run -d ios
   ```

5. **Configuring Backend URL on Physical Device:**
   Open the **Settings** screen (gear icon in the top right) to input the local network IP of the FastAPI server (e.g. `http://192.168.1.100:8000`).

### Local Android backend

Start the API from the repository root in a separate PowerShell terminal:

```powershell
$env:DEBUG = 'false'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

The Android debug build allows HTTP to `10.0.2.2`, `127.0.0.1`, and `localhost` for local development. Release builds retain Android's default cleartext restrictions; use HTTPS for a deployed backend. Physical-device HTTP development requires a separate debug network configuration for the intended host.

### Reproducible Android build

Keep `pubspec.lock` in version control. The compatible dependency set uses `file_picker` 11.0.3 and `flutter_secure_storage` 9.2.4; both accept `win32` 5.x through their desktop implementations. Do not independently force `win32` 6.x or upgrade the file picker across a major version without reviewing secure storage's Windows dependency constraints. Desktop dependencies are resolved even for an Android build.

The Android build uses Gradle 9.3.1, AGP 9.1.0, built-in Kotlin with compiler 2.4.0, Android SDK 36, minimum API 24, and Java/JVM target 17. Android libraries receive a compile SDK floor of 36 and Java target 17 through AGP's `finalizeDsl` API, so older plugin defaults do not require Pub cache edits. `android.newDsl=false` retains Flutter's supported legacy DSL compatibility. The local build uses Android Studio's bundled JDK 25.0.3 and NDK 28.2.13676358.

Run these commands from `mobile/`:

```powershell
flutter clean
flutter pub get
dart format --output=none --set-exit-if-changed .
flutter analyze
flutter test
flutter build apk --debug
```

The APK is generated at `build/app/outputs/flutter-apk/app-debug.apk`.

`file_picker` 11 uses `FilePicker.pickFiles()` directly. Its legacy Kotlin branch can trigger Flutter 3.47's source-text-based KGP warning even when built-in Kotlin is active; do not patch the Pub cache or disable build validation to hide it. Java 25 can also report Gradle's native-library access warning. See [BUILD_VALIDATION.md](BUILD_VALIDATION.md) for executed checks, runtime results, and remaining third-party warnings.

### Connected Android acceptance test

With the Compose API and database healthy at port 8000, run `flutter test integration_test/system_workflow_test.dart -d emulator-5554`. The test creates a synthetic account and scan, runs the UI workflow, retrieves the owned report, and logs out. It is a development test, not a test to point at a production clinical database.
