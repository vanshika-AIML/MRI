"""Connected PostgreSQL/authentication/inference/report integration tests."""
import io
import gzip
import uuid
from pathlib import Path
import numpy as np
import nibabel as nib
from fastapi.testclient import TestClient
from app.main import app
from app.api.dependencies import get_db_optional
from app.models.user import User


def test_authenticated_analysis_report_and_annotation_workflow(db_session, monkeypatch):
    app.dependency_overrides[get_db_optional] = lambda: db_session
    try:
        with TestClient(app) as client:
            suffix = uuid.uuid4().hex[:12]
            credentials = {"email": f"{suffix}@example.com", "password": "IntegrationTest42!"}
            registered = client.post(
                '/api/v1/auth/register',
                json={**credentials, "username": suffix, "profession": "researcher"},
            )
            assert registered.status_code == 201, registered.text
            assert registered.json()["profession"] == "researcher"
            assert registered.json()["role"] == "viewer"
            user_id = registered.json()['id']
            login = client.post('/api/v1/auth/login', json=credentials)
            assert login.status_code == 200, login.text
            tokens = login.json()
            headers = {'Authorization': 'Bearer ' + tokens['access_token']}
            assert client.get('/api/v1/auth/me', headers=headers).json()['id'] == user_id
            refreshed = client.post('/api/v1/auth/refresh', json={'refresh_token': tokens['refresh_token']})
            assert refreshed.status_code == 200
            assert client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401
            headers = {"Authorization": "Bearer " + refreshed.json()["access_token"]}
            array = np.zeros((64, 64), dtype=np.float32)
            array[20:30, 20:30] = 10
            stream = io.BytesIO()
            np.save(stream, array)
            response = client.post('/api/v1/analysis', headers=headers, files={'file': ('synthetic.npy', stream.getvalue())})
            assert response.status_code == 200, response.text
            report = response.json()
            assert report['success'] and report['is_baseline']
            path = '/api/v1/analysis/' + report['analysis_id']
            assert client.get(path + '/report', headers=headers).json() == report
            assert client.get(path + '/report').status_code == 401

            model_report_path = None
            run_dir = Path(__file__).resolve().parents[2] / "ml" / "runs" / "msd-flair-pilot"
            if (run_dir / "weights.pt").is_file():
                from app.core.config import settings

                monkeypatch.setattr(settings, "MRI_TUMOR_MODEL_RUN_DIR", str(run_dir))
                volume = np.zeros((24, 20, 5), dtype=np.float32)
                volume[3:21, 2:18, 1:4] = 1
                nifti = gzip.compress(
                    nib.Nifti1Image(volume, np.diag([1.5, 2.0, 2.5, 1.0])).to_bytes(),
                    mtime=0,
                )
                model_response = client.post(
                    "/api/v1/analysis",
                    headers=headers,
                    files={"file": ("research_flair.nii.gz", nifti, "application/gzip")},
                    data={
                        "analysis_method": "research_flair_segmentation",
                        "flair_sequence_confirmed": "true",
                    },
                )
                assert model_response.status_code == 200, model_response.text
                model_report = model_response.json()
                assert model_report["is_baseline"] is False
                model_report_path = f"/api/v1/analysis/{model_report['analysis_id']}"
                assert client.get(model_report_path + "/report", headers=headers).json() == model_report

            annotation = {'annotation_text': 'Synthetic engineering validation only.'}
            assert client.post(path + '/annotations', headers=headers, json=annotation).status_code == 403
            user = db_session.get(User, uuid.UUID(user_id))
            user.role = 'radiologist'
            db_session.flush()
            assert client.post(path + '/annotations', headers=headers, json=annotation).status_code == 201
            assert len(client.get(path + '/annotations', headers=headers).json()) == 1
            assert client.get(path + '/report', headers=headers).json() == report
            # A different user cannot read the report or its annotations.
            other = {"email": f"other{suffix}@example.com", "password": credentials['password'], "username": 'other' + suffix}
            assert client.post('/api/v1/auth/register', json=other).status_code == 201
            other_tokens = client.post('/api/v1/auth/login', json=other).json()
            other_headers = {'Authorization': 'Bearer ' + other_tokens['access_token']}
            assert client.get(path + '/report', headers=other_headers).status_code == 404
            assert client.get(path + '/annotations', headers=other_headers).status_code == 404
            if model_report_path is not None:
                assert client.get(model_report_path + '/report', headers=other_headers).status_code == 404
            assert client.post('/api/v1/auth/logout', headers=headers).status_code == 200
            assert client.get('/api/v1/auth/me', headers=headers).status_code == 401
    finally:
        app.dependency_overrides.pop(get_db_optional, None)
