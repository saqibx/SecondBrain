"""
Health check and system tests
"""

import pytest
import json


class TestHealthCheck:
    """Test health check endpoint"""
    
    def test_health_check_endpoint(self, client):
        """Test health check returns valid response"""
        response = client.get('/health')
        
        assert response.status_code in [200, 503]
        data = json.loads(response.data)
        assert 'status' in data['data']
        assert data['data']['status'] in ['healthy', 'degraded']
    
    def test_health_check_has_timestamp(self, client):
        """Test health check includes timestamp"""
        response = client.get('/health')
        data = json.loads(response.data)
        assert 'timestamp' in data['data']


class TestAPIEndpoints:
    """Test API endpoints"""
    
    def test_api_root_endpoint(self, client):
        """Test API root documentation endpoint"""
        response = client.get('/api/v1')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'endpoints' in data['data']
    
    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get('/')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True


class TestCORS:
    """Test CORS configuration"""
    
    def test_options_request(self, client):
        """Test OPTIONS preflight request"""
        response = client.options('/api/v1/login')
        
        assert response.status_code == 200
        assert 'Access-Control-Allow-Methods' in response.headers
        assert 'Access-Control-Allow-Headers' in response.headers
