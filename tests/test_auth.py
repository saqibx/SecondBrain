"""
Authentication and user tests
"""

import pytest
import json


class TestAuthentication:
    """Test authentication endpoints"""
    
    def test_register_success(self, client, test_user_data):
        """Test successful user registration"""
        response = client.post(
            '/api/v1/register',
            data=json.dumps(test_user_data),
            content_type='application/json'
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['data']['username'] == test_user_data['username']
    
    def test_register_duplicate_user(self, client, test_user_data):
        """Test registration with duplicate username"""
        # First registration
        client.post(
            '/api/v1/register',
            data=json.dumps(test_user_data),
            content_type='application/json'
        )
        
        # Second registration with same username
        response = client.post(
            '/api/v1/register',
            data=json.dumps(test_user_data),
            content_type='application/json'
        )
        
        assert response.status_code == 409
        data = json.loads(response.data)
        assert data['success'] == False
    
    def test_register_weak_password(self, client):
        """Test registration with weak password"""
        response = client.post(
            '/api/v1/register',
            data=json.dumps({
                "username": "testuser",
                "password": "weak"
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] == False
    
    def test_register_invalid_username(self, client):
        """Test registration with invalid username"""
        response = client.post(
            '/api/v1/register',
            data=json.dumps({
                "username": "user@invalid#name",
                "password": "ValidPass123!"
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 400
    
    def test_login_success(self, client, test_user_data):
        """Test successful login"""
        # Register first
        client.post(
            '/api/v1/register',
            data=json.dumps(test_user_data),
            content_type='application/json'
        )
        
        # Login
        response = client.post(
            '/api/v1/login',
            data=json.dumps(test_user_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
    
    def test_login_wrong_password(self, client, test_user_data):
        """Test login with wrong password"""
        # Register first
        client.post(
            '/api/v1/register',
            data=json.dumps(test_user_data),
            content_type='application/json'
        )
        
        # Login with wrong password
        response = client.post(
            '/api/v1/login',
            data=json.dumps({
                "username": test_user_data['username'],
                "password": "WrongPass123!"
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['success'] == False
    
    def test_logout(self, client, test_user_data):
        """Test logout"""
        # Register and login
        client.post(
            '/api/v1/register',
            data=json.dumps(test_user_data),
            content_type='application/json'
        )
        
        # Logout
        response = client.post('/api/v1/logout')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True


class TestAuthStatus:
    """Test authentication status endpoint"""
    
    def test_auth_status_not_authenticated(self, client):
        """Test auth status when not authenticated"""
        response = client.get('/api/v1/auth/status')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['data']['authenticated'] == False
