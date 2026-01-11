"""
Unit tests for SecondBrain API
"""

import pytest
import json
import uuid
from datetime import datetime


@pytest.fixture
def client(app):
    """Create a test client"""
    return app.test_client()


@pytest.fixture
def app():
    """Create application for testing"""
    import os
    os.environ['FLASK_ENV'] = 'testing'
    
    from app import app as flask_app
    
    with flask_app.app_context():
        yield flask_app


class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_check_success(self, client):
        """Test that health check returns OK"""
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['status'] in ['healthy', 'degraded']


class TestAuthenticationEndpoints:
    """Test authentication endpoints"""
    
    def test_auth_status_not_authenticated(self, client):
        """Test auth status when not logged in"""
        response = client.get('/api/v1/auth/status')
        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['authenticated'] is False
    
    def test_options_request(self, client):
        """Test CORS preflight request"""
        response = client.options('/api/v1/login')
        assert response.status_code == 200
        assert 'Access-Control-Allow-Origin' in response.headers
    
    def test_register_missing_fields(self, client):
        """Test registration with missing fields"""
        response = client.post(
            '/api/v1/register',
            data=json.dumps({}),
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
    
    def test_login_missing_credentials(self, client):
        """Test login with missing credentials"""
        response = client.post(
            '/api/v1/login',
            data=json.dumps({'username': 'test'}),
            content_type='application/json'
        )
        assert response.status_code == 400


class TestAPIRoot:
    """Test API root endpoints"""
    
    def test_api_v1_documentation(self, client):
        """Test API v1 documentation endpoint"""
        response = client.get('/api/v1')
        assert response.status_code == 200
        data = response.get_json()
        assert 'endpoints' in data['data']
    
    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get('/')
        assert response.status_code == 200


class TestErrorHandling:
    """Test error handling"""
    
    def test_404_not_found(self, client):
        """Test 404 error handling"""
        response = client.get('/api/v1/nonexistent')
        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False
        assert 'NOT_FOUND' in str(data)


# Integration tests (require database)
@pytest.mark.skipif(
    not pytest.config.getoption("--integration"),
    reason="only run with --integration flag"
)
class TestIntegration:
    """Integration tests with database"""
    
    def test_user_registration_and_login(self, client):
        """Test full registration and login flow"""
        # Generate unique username
        username = f"testuser_{uuid.uuid4().hex[:8]}"
        password = "testpassword123"
        
        # Register
        register_response = client.post(
            '/api/v1/register',
            data=json.dumps({
                'username': username,
                'password': password
            }),
            content_type='application/json'
        )
        assert register_response.status_code in [201, 200]
        
        # Check authenticated
        status_response = client.get('/api/v1/auth/status')
        assert status_response.status_code == 200
        assert status_response.get_json()['data']['authenticated'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
