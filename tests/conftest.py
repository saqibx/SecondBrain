"""
Test configuration and fixtures
"""

import pytest
import os
from dotenv import load_dotenv
from app import app
from config import TestingConfig


@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    app.config.from_object(TestingConfig)
    
    with app.test_client() as client:
        yield client


@pytest.fixture
def runner():
    """Create test CLI runner"""
    return app.test_cli_runner()


@pytest.fixture
def test_user_data():
    """Sample user data for testing"""
    return {
        "username": "testuser",
        "password": "TestPass123!"
    }
