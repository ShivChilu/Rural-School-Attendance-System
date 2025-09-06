#!/usr/bin/env python3

import requests
import sys
import json
import base64
from datetime import datetime
from io import BytesIO
from PIL import Image
import numpy as np

class RuralAttendanceAPITester:
    def __init__(self, base_url="https://ruralattend.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.session_token = None
        self.user_data = None
        self.tests_run = 0
        self.tests_passed = 0
        self.created_resources = {
            'classes': [],
            'students': [],
            'teachers': []
        }

    def log_test(self, name, success, details=""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
        if details:
            print(f"   Details: {details}")

    def make_request(self, method, endpoint, data=None, expected_status=200, use_auth=True):
        """Make HTTP request with proper headers"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if use_auth and self.session_token:
            headers['Authorization'] = f'Bearer {self.session_token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            return success, response

        except Exception as e:
            return False, str(e)

    def generate_test_image(self):
        """Generate a simple test image as base64"""
        # Create a simple 100x100 RGB image
        img = Image.new('RGB', (100, 100), color='red')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        img_data = buffer.getvalue()
        return base64.b64encode(img_data).decode('utf-8')

    def test_health_endpoints(self):
        """Test basic health endpoints"""
        print("\n🔍 Testing Health Endpoints...")
        
        # Test root endpoint
        success, response = self.make_request('GET', '', use_auth=False)
        if success:
            data = response.json()
            self.log_test("Root endpoint", 
                         "Rural School Attendance System API" in data.get('message', ''))
        else:
            self.log_test("Root endpoint", False, f"Status: {response.status_code if hasattr(response, 'status_code') else response}")

        # Test health endpoint
        success, response = self.make_request('GET', 'health', use_auth=False)
        if success:
            data = response.json()
            self.log_test("Health endpoint", 
                         data.get('status') == 'healthy')
        else:
            self.log_test("Health endpoint", False, f"Status: {response.status_code if hasattr(response, 'status_code') else response}")

    def test_auth_endpoints(self):
        """Test authentication endpoints"""
        print("\n🔍 Testing Authentication Endpoints...")
        
        # Test login endpoint (should return auth URL)
        success, response = self.make_request('GET', 'auth/login', use_auth=False)
        if success:
            data = response.json()
            has_auth_url = 'auth_url' in data and 'emergentagent.com' in data['auth_url']
            self.log_test("Login endpoint", has_auth_url, 
                         f"Auth URL: {data.get('auth_url', 'Not found')}")
        else:
            self.log_test("Login endpoint", False, f"Status: {response.status_code if hasattr(response, 'status_code') else response}")

        # Test auth/me without token (should fail)
        success, response = self.make_request('GET', 'auth/me', use_auth=False, expected_status=401)
        self.log_test("Auth/me without token", success, "Should return 401")

        # Note: We can't test the full OAuth flow without actual OAuth tokens
        print("   ⚠️  OAuth session creation requires valid Emergent session_id")

    def test_admin_endpoints_without_auth(self):
        """Test admin endpoints without authentication (should fail)"""
        print("\n🔍 Testing Admin Endpoints (Unauthorized)...")
        
        endpoints = [
            ('GET', 'admin/classes'),
            ('POST', 'admin/classes'),
            ('GET', 'admin/teachers'),
        ]
        
        for method, endpoint in endpoints:
            success, response = self.make_request(method, endpoint, use_auth=False, expected_status=401)
            self.log_test(f"Admin {endpoint} without auth", success, "Should return 401")

    def test_teacher_endpoints_without_auth(self):
        """Test teacher endpoints without authentication (should fail)"""
        print("\n🔍 Testing Teacher Endpoints (Unauthorized)...")
        
        endpoints = [
            ('GET', 'teacher/classes'),
            ('GET', 'teacher/classes/test-id/students'),
            ('POST', 'teacher/classes/test-id/students'),
        ]
        
        for method, endpoint in endpoints:
            success, response = self.make_request(method, endpoint, use_auth=False, expected_status=401)
            self.log_test(f"Teacher {endpoint} without auth", success, "Should return 401")

    def test_student_endpoints_without_auth(self):
        """Test student endpoints without authentication (should fail)"""
        print("\n🔍 Testing Student Endpoints (Unauthorized)...")
        
        success, response = self.make_request('POST', 'students/test-id/enroll', 
                                            data={'image': 'test'}, use_auth=False, expected_status=401)
        self.log_test("Student enrollment without auth", success, "Should return 401")

    def test_attendance_endpoints_without_auth(self):
        """Test attendance endpoints without authentication (should fail)"""
        print("\n🔍 Testing Attendance Endpoints (Unauthorized)...")
        
        endpoints = [
            ('POST', 'attendance/mark'),
            ('GET', 'attendance/test-class/2024-01-01'),
        ]
        
        for method, endpoint in endpoints:
            success, response = self.make_request(method, endpoint, use_auth=False, expected_status=401)
            self.log_test(f"Attendance {endpoint} without auth", success, "Should return 401")

    def test_face_recognition_data_format(self):
        """Test face recognition data format handling"""
        print("\n🔍 Testing Face Recognition Data Format...")
        
        # Test with invalid image data (should fail gracefully)
        invalid_data = {'image': 'invalid-base64-data'}
        success, response = self.make_request('POST', 'students/test-id/enroll', 
                                            data=invalid_data, use_auth=False, expected_status=401)
        # This will fail due to auth, but we're testing the endpoint exists
        self.log_test("Face enrollment endpoint exists", 
                     response.status_code == 401, "Endpoint should exist but require auth")

        # Test attendance marking endpoint
        attendance_data = {
            'class_id': 'test-class',
            'image': 'invalid-base64-data',
            'date': '2024-01-01'
        }
        success, response = self.make_request('POST', 'attendance/mark', 
                                            data=attendance_data, use_auth=False, expected_status=401)
        self.log_test("Attendance marking endpoint exists", 
                     response.status_code == 401, "Endpoint should exist but require auth")

    def test_cors_headers(self):
        """Test CORS configuration"""
        print("\n🔍 Testing CORS Configuration...")
        
        try:
            response = requests.options(f"{self.api_url}/health")
            has_cors = 'Access-Control-Allow-Origin' in response.headers
            self.log_test("CORS headers present", has_cors, 
                         f"CORS Origin: {response.headers.get('Access-Control-Allow-Origin', 'Not found')}")
        except Exception as e:
            self.log_test("CORS test", False, str(e))

    def test_api_structure(self):
        """Test API structure and routing"""
        print("\n🔍 Testing API Structure...")
        
        # Test that /api prefix is working
        success, response = self.make_request('GET', '', use_auth=False)
        self.log_test("API prefix routing", success, "Root API endpoint should be accessible")
        
        # Test non-existent endpoint
        success, response = self.make_request('GET', 'non-existent-endpoint', 
                                            use_auth=False, expected_status=404)
        self.log_test("404 handling", success, "Non-existent endpoints should return 404")

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Rural School Attendance System Backend Tests")
        print(f"📍 Testing against: {self.base_url}")
        print("=" * 60)

        # Run all test suites
        self.test_health_endpoints()
        self.test_auth_endpoints()
        self.test_admin_endpoints_without_auth()
        self.test_teacher_endpoints_without_auth()
        self.test_student_endpoints_without_auth()
        self.test_attendance_endpoints_without_auth()
        self.test_face_recognition_data_format()
        self.test_cors_headers()
        self.test_api_structure()

        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            print("⚠️  Some tests failed. Check the details above.")
            return 1

def main():
    """Main test runner"""
    tester = RuralAttendanceAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())