# Infrastructure & Deployment

This directory contains containerization, orchestration, and cloud deployment configurations for the AI-Assisted MRI Image Enhancement and Abnormality Detection System.

## Structure
- `docker/`: Dockerfiles for containerizing frontend, backend, and ML inference services.
- `docker-compose.yml`: (Located at repository root) Local multi-container orchestration.

## Future Plans (Subsequent Phases)
- Dockerfiles:
  - `docker/Dockerfile.backend`: Multi-stage Python FastAPI container with runtime dependencies.
  - `docker/Dockerfile.frontend`: Multi-stage build with Nginx for production React static asset serving.
  - `docker/Dockerfile.ml`: CUDA-enabled PyTorch container for GPU-accelerated inference.
- Database service: PostgreSQL 16+ with `pgvector` extension for medical report and image embedding retrieval.
- Cache & Queue: Redis for asynchronous MRI enhancement and abnormality inference jobs.
- Cloud / Kubernetes manifests: Helm charts and CI/CD deployment pipelines.
