"""Security regression tests using synthetic inputs only."""
import io
from datetime import datetime, timedelta, timezone
import numpy as np
import pytest
import jwt
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.core.security import verify_access_token
from app.services.analysis import AnalysisService
from app.api.dependencies import get_db_optional


def test_expired_and_unsigned_tokens_rejected():
    payload = {'sub': 'test', 'type': 'access', 'iat': datetime.now(timezone.utc), 'exp': datetime.now(timezone.utc) - timedelta(seconds=10)}
    assert verify_access_token(jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')) is None
    assert verify_access_token(jwt.encode(payload, '', algorithm='none')) is None


def test_password_never_reflected_in_validation_errors():
    with TestClient(app) as client:
        response = client.post('/api/v1/auth/register', json={'password': 'SensitiveSecretValue'})
        assert response.status_code == 422
        assert 'SensitiveSecretValue' not in response.text
        assert '"input"' not in response.text


def test_registration_rate_limit_is_enforced():
    from app.core.rate_limit import limiter
    app.dependency_overrides[get_db_optional] = lambda: None
    limiter.enabled = True
    limiter.reset()
    try:
        with TestClient(app) as client:
            payload = {'email': 'rate@example.com', 'username': 'ratetest', 'password': 'RatePassword42'}
            statuses = [client.post('/api/v1/auth/register', json=payload).status_code for _ in range(6)]
            assert statuses[:5] == [503] * 5
            assert statuses[5] == 429
    finally:
        limiter.enabled = False
        limiter.reset()
        app.dependency_overrides.pop(get_db_optional, None)


def test_object_numpy_and_oversized_declared_shape_rejected():
    stream = io.BytesIO()
    np.save(stream, np.array([[{'arbitrary': 'object'}]], dtype=object))
    with pytest.raises(ValueError):
        AnalysisService().parse_and_validate_file(stream.getvalue(), 'unsafe.npy')
    stream = io.BytesIO()
    np.lib.format.write_array_header_1_0(stream, {'descr': '<f4', 'fortran_order': False, 'shape': (100000, 100000)})
    with pytest.raises(ValueError, match='limits'):
        AnalysisService().parse_and_validate_file(stream.getvalue(), 'huge.npy')


def test_chunked_upload_limit_before_parser():
    from fastapi import FastAPI, Request
    from app.core.upload_limit import UploadLimitMiddleware
    isolated = FastAPI()
    isolated.add_middleware(UploadLimitMiddleware, limit=8)
    @isolated.post('/analysis')
    async def upload(request: Request):
        return {'bytes': len(await request.body())}
    with TestClient(isolated) as client:
        assert client.post('/analysis', content=iter([b'12345', b'6789'])).status_code == 413
        assert client.post('/analysis', content=b'1234').json() == {'bytes': 4}


def test_unauthenticated_user_cannot_attach_to_arbitrary_study():
    app.dependency_overrides[get_db_optional] = lambda: None
    try:
        with TestClient(app) as client:
            response = client.post('/api/v1/analysis', files={'file': ('test.npy', b'bad')}, data={'study_id': 'arbitrary'})
            assert response.status_code == 401
    finally:
        app.dependency_overrides.pop(get_db_optional, None)


def test_failed_login_counter_survives_401(db_engine):
    import uuid
    from sqlalchemy.orm import Session
    from app.models.user import User
    suffix = uuid.uuid4().hex[:12]
    def database():
        with Session(db_engine) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
    app.dependency_overrides[get_db_optional] = database
    try:
        with TestClient(app) as client:
            email = suffix + '@example.com'
            registration = client.post('/api/v1/auth/register', json={'email': email, 'username': suffix, 'password': 'CorrectPassword42'})
            assert registration.status_code == 201
            for _ in range(5):
                assert client.post('/api/v1/auth/login', json={'email': email, 'password': 'WrongPassword42'}).status_code == 401
            assert client.post('/api/v1/auth/login', json={'email': email, 'password': 'CorrectPassword42'}).status_code == 401
            with Session(db_engine) as session:
                user = session.get(User, uuid.UUID(registration.json()['id']))
                assert user.failed_login_count == 5 and user.locked_until is not None
                session.delete(user)
                session.commit()
    finally:
        app.dependency_overrides.pop(get_db_optional, None)
