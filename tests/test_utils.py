"""
Utility function tests
"""

import pytest
from utils import error_response, success_response


class TestErrorResponse:
    """Test error response formatting"""
    
    def test_error_response_basic(self):
        """Test basic error response"""
        response, status_code = error_response("Test error", status_code=400)
        
        assert status_code == 400
        assert response.status_code == 400
        json_data = response.get_json()
        assert json_data['success'] == False
        assert json_data['error'] == "Test error"
    
    def test_error_response_with_code(self):
        """Test error response with error code"""
        response, status_code = error_response(
            "Test error",
            status_code=400,
            error_code="TEST_ERROR"
        )
        
        json_data = response.get_json()
        assert json_data['error_code'] == "TEST_ERROR"
    
    def test_error_response_with_details(self):
        """Test error response with details"""
        details = {"field": "username", "issue": "already exists"}
        response, status_code = error_response(
            "Validation error",
            status_code=400,
            details=details
        )
        
        json_data = response.get_json()
        assert json_data['details'] == details


class TestSuccessResponse:
    """Test success response formatting"""
    
    def test_success_response_basic(self):
        """Test basic success response"""
        response, status_code = success_response(status_code=200)
        
        assert status_code == 200
        json_data = response.get_json()
        assert json_data['success'] == True
    
    def test_success_response_with_data(self):
        """Test success response with data"""
        data = {"user_id": "123", "username": "testuser"}
        response, status_code = success_response(data=data, status_code=200)
        
        json_data = response.get_json()
        assert json_data['data'] == data
    
    def test_success_response_with_message(self):
        """Test success response with message"""
        response, status_code = success_response(
            message="Operation completed",
            status_code=200
        )
        
        json_data = response.get_json()
        assert json_data['message'] == "Operation completed"
