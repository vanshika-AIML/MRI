# Model Card: FLAIR Whole-Tumor Research Segmenter

**Status:** Experimental research model; not clinically validated or approved for patient care.  
**Model family:** Compact 2D U-Net, binary whole-tumor segmentation.  
**Current run:** `msd-flair-pilot`  
**Checkpoint SHA-256:** `036ac63641c4aeeb1dd8e2c0087208feaf8b42ff525b8cb16032ef33e2f48ecf`

## Intended use

This model produces a research visualization mask for whole-tumor labels (`label > 0`) from a 3D FLAIR NIfTI volume. It is exposed only through the explicit `research_flair_segmentation` API mode. Its output is not a diagnosis, clinical probability, tumor classification, grade, treatment recommendation, or substitute for expert interpretation.

The existing heuristic analysis remains the default, but it is not a clinical abnormality classifier. An empty candidate list is reported as `not_assessed`; it must not be interpreted as a normal scan. Every analysis requires an authenticated account. Selecting this model additionally requires a user confirmation that the NIfTI contains a brain FLAIR volume and a reachable database so the owner-scoped report can be saved. That confirmation is self-declared, not independent sequence verification. The model verifies its checkpoint against its evaluation metadata, returns a geometry-preserving NIfTI mask and preview, and does not silently fall back to heuristics.

## Training data and method

- **Source:** Medical Segmentation Decathlon Task01 BrainTumour public dataset, distributed under CC BY-SA 4.0; see the [training guide](../../ml/training/README.md) for source attribution and reproduction.
- **Subset:** 64 deterministically selected labeled cases, split at patient level into 48 train, 8 validation and 8 test cases.
- **Input/target:** FLAIR channel 0; binary whole-tumor target is `label > 0`.
- **Method:** Compact 2D U-Net trained for 10 epochs on 96×96 resized axial slices, sampling every sixth slice, CPU, seed `20261016`. Validation Dice selected the checkpoint; the test split was not used for optimization.
- **Inference:** Canonical NIfTI orientation and affine are retained for the returned mask; preprocessing is versioned as `flair-zscore-ras-v1`.

## Evaluation

- Held-out mean patient Dice: **0.7735**.
- Patient bootstrap 95% interval: **[0.6630, 0.8614]**, based on only 8 test patients.
- Best validation Dice: **0.7315**.
- Reported Dice is at the sampled/resized slice resolution, not full-resolution volumetric clinical performance.
- A held-out full-volume geometry/inference check used `BRATS_096` (240×240×155) and verified input, checkpoint and mask hashes and the canonical affine. Its 2.605-second CPU timing is one local engineering observation, excluding model cold start, HTTP serialization, database work and concurrent traffic.

See the [pilot evaluation](../verification/msd-flair-pilot-evaluation.json) and [full-volume inference evidence](../verification/phase16-model-api-inference.json) for recorded details.

## Limitations and risks

The cohort is small and comes from a single public dataset. There is no independent-site validation, reader study, healthy-control cohort, scanner/subgroup calibration, clinical outcome assessment, or regulatory clearance. Performance may change with acquisition protocols, populations, preprocessing, artifacts and pathology distribution. A predicted mask may be empty, incomplete, or inaccurate; voxel count and visualization do not establish tumor presence.

Do not use outputs to diagnose, triage, treat, or make patient-care decisions. Use only synthetic or appropriately authorized data in this research deployment. Do not upload identifiable scans to third-party services.

## Deployment and governance

The default backend does not load PyTorch or this checkpoint. The optional Compose overlay mounts the selected run read-only. The current local pilot stack passed authenticated synthetic inference and report-persistence/recovery checks; the updated stack also applied the additive profession migration and passed isolated-database auth, inference, report-owner and Android emulator workflows. These checks do not validate clinical performance or production capacity. Candidate activation and rollback are manual immutable run-path changes with checkpoint preflight. The verified candidate exercise used a copy of the active pilot and tested deployment controls only, not a new model's quality.

The local deployment uses HTTP and a generated runtime-only test secret. Configure a persistent secret, TLS, restricted network access, external monitoring, backup/retention policy and production resource limits before any production use. See the [deployment guide](../DEPLOYMENT.md) and [release verification report](../verification/RELEASE_REPORT.md).
