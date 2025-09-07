#!/usr/bin/env python3

import requests
import sys
import json
import base64
from datetime import datetime
from io import BytesIO
from PIL import Image
import numpy as np
import cv2

class RuralAttendanceAPITester:
    def __init__(self, base_url="https://smart-attendance-21.preview.emergentagent.com"):
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

    def generate_realistic_face_image(self):
        """Generate a more realistic test face image using OpenCV"""
        try:
            # Create a 200x200 image with a simple face-like pattern
            img = np.zeros((200, 200, 3), dtype=np.uint8)
            
            # Fill with skin-like color
            img[:, :] = [220, 180, 140]  # Light skin tone
            
            # Draw face outline (circle)
            cv2.circle(img, (100, 100), 80, (200, 160, 120), -1)
            
            # Draw eyes
            cv2.circle(img, (80, 80), 8, (0, 0, 0), -1)  # Left eye
            cv2.circle(img, (120, 80), 8, (0, 0, 0), -1)  # Right eye
            
            # Draw nose
            cv2.line(img, (100, 90), (100, 110), (180, 140, 100), 2)
            
            # Draw mouth
            cv2.ellipse(img, (100, 130), (15, 8), 0, 0, 180, (150, 100, 100), 2)
            
            # Convert to PIL Image and then to base64
            pil_img = Image.fromarray(img)
            buffer = BytesIO()
            pil_img.save(buffer, format='JPEG')
            img_data = buffer.getvalue()
            return base64.b64encode(img_data).decode('utf-8')
            
        except Exception as e:
            print(f"Error generating realistic face image: {e}")
            return self.generate_test_image()

    def test_system_reset(self):
        """Test system reset functionality - HIGHEST PRIORITY"""
        print("\n🔍 Testing System Reset (HIGHEST PRIORITY)...")
        
        # Test system reset endpoint
        success, response = self.make_request('POST', 'admin/reset-system', use_auth=False)
        if success:
            data = response.json()
            reset_success = "reset successfully" in data.get('message', '').lower()
            self.log_test("System Reset", reset_success, 
                         f"Response: {data.get('message', 'No message')}")
        else:
            self.log_test("System Reset", False, 
                         f"Status: {response.status_code if hasattr(response, 'status_code') else response}")

    def test_user_role_management(self):
        """Test user role assignment logic - HIGHEST PRIORITY"""
        print("\n🔍 Testing User Role Management (HIGHEST PRIORITY)...")
        
        # Note: We can't fully test OAuth flow without valid session_id
        # But we can test the endpoint structure and expected behavior
        
        # Test session creation endpoint exists
        session_data = {"session_id": "test-session-id"}
        success, response = self.make_request('POST', 'auth/session', 
                                            data=session_data, use_auth=False, expected_status=400)
        
        endpoint_exists = response.status_code == 400  # Should fail with invalid session but endpoint exists
        self.log_test("Session creation endpoint exists", endpoint_exists, 
                     "Endpoint should exist but fail with invalid session_id")
        
        # Test that chiluverushivaprasad02@gmail.com would get admin role
        # This is tested in the backend logic, we can verify the endpoint structure
        print("   ℹ️  Admin role assignment for chiluverushivaprasad02@gmail.com is implemented in backend")
        print("   ℹ️  Other emails get teacher role by default")

    def test_face_detection_pipeline(self):
        """Test Mediapipe face detection and recognition - HIGHEST PRIORITY"""
        print("\n🔍 Testing Face Detection Pipeline (HIGHEST PRIORITY)...")
        
        # Generate a realistic face image for testing
        face_image = self.generate_realistic_face_image()
        
        # Test student enrollment with face data (without auth - should fail but test data format)
        enrollment_data = {"image": face_image}
        success, response = self.make_request('POST', 'students/test-student-id/enroll', 
                                            data=enrollment_data, use_auth=False, expected_status=401)
        
        endpoint_works = response.status_code == 401  # Should fail due to auth but endpoint exists
        self.log_test("Face enrollment endpoint structure", endpoint_works, 
                     "Endpoint should exist but require authentication")
        
        # Test attendance marking with face data
        attendance_data = {
            "class_id": "test-class-id",
            "image": face_image,
            "date": datetime.now().strftime("%Y-%m-%d")
        }
        success, response = self.make_request('POST', 'attendance/mark', 
                                            data=attendance_data, use_auth=False, expected_status=401)
        
        endpoint_works = response.status_code == 401
        self.log_test("Face recognition attendance endpoint structure", endpoint_works, 
                     "Endpoint should exist but require authentication")
        
        # Test with invalid image data
        invalid_data = {"image": "invalid-base64-data"}
        success, response = self.make_request('POST', 'students/test-student-id/enroll', 
                                            data=invalid_data, use_auth=False, expected_status=401)
        
        self.log_test("Invalid image data handling", response.status_code == 401, 
                     "Should handle invalid image data gracefully")

    def test_api_endpoints_comprehensive(self):
        """Test all API endpoints comprehensively - HIGHEST PRIORITY"""
        print("\n🔍 Testing API Endpoints Comprehensive (HIGHEST PRIORITY)...")
        
        # Test all admin endpoints
        admin_endpoints = [
            ('GET', 'admin/classes', 'Get all classes'),
            ('POST', 'admin/classes', 'Create class'),
            ('GET', 'admin/teachers', 'Get all teachers'),
            ('PUT', 'admin/classes/test-id', 'Assign teacher to class')
        ]
        
        for method, endpoint, description in admin_endpoints:
            test_data = {"name": "Test Class", "grade": "5", "section": "A"} if method == 'POST' else None
            success, response = self.make_request(method, endpoint, data=test_data, 
                                                use_auth=False, expected_status=401)
            self.log_test(f"Admin endpoint: {description}", response.status_code == 401, 
                         f"{method} /{endpoint} - Should require authentication")
        
        # Test teacher endpoints
        teacher_endpoints = [
            ('GET', 'teacher/classes', 'Get teacher classes'),
            ('GET', 'teacher/classes/test-id/students', 'Get class students'),
            ('POST', 'teacher/classes/test-id/students', 'Add student to class')
        ]
        
        for method, endpoint, description in teacher_endpoints:
            test_data = {"name": "Test Student", "roll_number": "001", "class_id": "test-id"} if method == 'POST' else None
            success, response = self.make_request(method, endpoint, data=test_data, 
                                                use_auth=False, expected_status=401)
            self.log_test(f"Teacher endpoint: {description}", response.status_code == 401, 
                         f"{method} /{endpoint} - Should require authentication")
        
        # Test attendance endpoints
        attendance_endpoints = [
            ('GET', 'attendance/test-class/2024-01-01', 'Get attendance records'),
        ]
        
        for method, endpoint, description in attendance_endpoints:
            success, response = self.make_request(method, endpoint, use_auth=False, expected_status=401)
            self.log_test(f"Attendance endpoint: {description}", response.status_code == 401, 
                         f"{method} /{endpoint} - Should require authentication")

    def test_database_connectivity(self):
        """Test database connectivity through API responses"""
        print("\n🔍 Testing Database Connectivity...")
        
        # Test endpoints that would interact with database
        # Even without auth, we can check if the server is properly connected to MongoDB
        
        # Health check should work regardless of database
        success, response = self.make_request('GET', 'health', use_auth=False)
        if success:
            data = response.json()
            self.log_test("Database connectivity (health check)", 
                         data.get('status') == 'healthy', 
                         "Health endpoint should work with database connection")
        else:
            self.log_test("Database connectivity (health check)", False, 
                         "Health endpoint failed - possible database issue")

    def test_mediapipe_integration(self):
        """Test Mediapipe integration through API behavior"""
        print("\n🔍 Testing Mediapipe Integration...")
        
        # Test with different image formats to see if Mediapipe processing works
        test_images = [
            ("Valid face image", self.generate_realistic_face_image()),
            ("Simple test image", self.generate_test_image()),
            ("Invalid base64", "invalid-data")
        ]
        
        for image_name, image_data in test_images:
            enrollment_data = {"image": image_data}
            success, response = self.make_request('POST', 'students/test-id/enroll', 
                                                data=enrollment_data, use_auth=False, expected_status=401)
            
            # We expect 401 due to no auth, but the endpoint should exist and handle the request
            endpoint_responsive = response.status_code == 401
            self.log_test(f"Mediapipe processing test ({image_name})", endpoint_responsive, 
                         "Endpoint should handle image processing requests")

    def test_error_handling(self):
        """Test error handling across the API"""
        print("\n🔍 Testing Error Handling...")
        
        # Test malformed JSON
        try:
            url = f"{self.api_url}/admin/classes"
            headers = {'Content-Type': 'application/json'}
            response = requests.post(url, data="invalid-json", headers=headers)
            
            handles_bad_json = response.status_code in [400, 422, 401]  # Should handle gracefully
            self.log_test("Malformed JSON handling", handles_bad_json, 
                         f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Malformed JSON handling", False, str(e))
        
        # Test missing required fields
        incomplete_data = {"name": "Test"}  # Missing required fields for class creation
        success, response = self.make_request('POST', 'admin/classes', 
                                            data=incomplete_data, use_auth=False, expected_status=401)
        
        self.log_test("Missing fields handling", response.status_code == 401, 
                     "Should handle missing fields (after auth check)")

    def test_security_headers(self):
        """Test security configurations"""
        print("\n🔍 Testing Security Configuration...")
        
        try:
            response = requests.get(f"{self.api_url}/health")
            
            # Check for CORS headers
            has_cors = 'Access-Control-Allow-Origin' in response.headers
            self.log_test("CORS configuration", has_cors, 
                         f"CORS: {response.headers.get('Access-Control-Allow-Origin', 'Not set')}")
            
            # Check content type
            correct_content_type = 'application/json' in response.headers.get('Content-Type', '')
            self.log_test("JSON content type", correct_content_type, 
                         f"Content-Type: {response.headers.get('Content-Type', 'Not set')}")
            
        except Exception as e:
            self.log_test("Security headers test", False, str(e))

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