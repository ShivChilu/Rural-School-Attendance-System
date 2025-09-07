from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Depends, Request, Response, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import aiofiles
import json
import numpy as np
import cv2
import base64
from io import BytesIO
from PIL import Image
import requests
import asyncio
import traceback
import mediapipe as mp

# For now, let's use a simple OpenCV-based approach without DeepFace
# We'll use MediaPipe for face detection and basic face comparison
DEEPFACE_AVAILABLE = False

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer(auto_error=False)

# Initialize Mediapipe Face Detection and Face Mesh
mp_face_detection = mp.solutions.face_detection
mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils
face_detection = mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5)
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1, min_detection_confidence=0.5)

# Helper Functions
def validate_face_quality(image_array: np.ndarray):
    """Validate face quality using Mediapipe Face Mesh"""
    try:
        # Convert RGB to BGR for mediapipe
        image_bgr = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
        
        # Detect face mesh
        results = face_mesh.process(image_bgr)
        
        if not results.multi_face_landmarks:
            return False, "No face detected"
        
        face_landmarks = results.multi_face_landmarks[0]
        h, w, _ = image_array.shape
        
        # Get key landmark points
        landmarks = []
        for landmark in face_landmarks.landmark:
            x = int(landmark.x * w)
            y = int(landmark.y * h)
            landmarks.append((x, y))
        
        # Check face visibility and quality
        # Eye landmarks (approximate indices)
        left_eye_indices = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
        right_eye_indices = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
        
        # Calculate eye openness (simple approach)
        left_eye_openness = calculate_eye_openness(landmarks, left_eye_indices)
        right_eye_openness = calculate_eye_openness(landmarks, right_eye_indices)
        
        # Check if eyes are sufficiently open
        min_eye_openness = 0.15  # Threshold for eye openness
        if left_eye_openness < min_eye_openness or right_eye_openness < min_eye_openness:
            return False, "Eyes not sufficiently open or visible"
        
        # Check face pose (using nose and mouth landmarks)
        nose_tip = landmarks[1]  # Nose tip
        chin = landmarks[18]      # Chin
        
        # Simple face angle check
        face_center_x = nose_tip[0]
        if face_center_x < w * 0.3 or face_center_x > w * 0.7:
            return False, "Face not centered or at extreme angle"
        
        return True, "Face quality validation passed"
        
    except Exception as e:
        print(f"Face quality validation error: {str(e)}")
        return False, f"Validation error: {str(e)}"

def calculate_eye_openness(landmarks, eye_indices):
    """Calculate eye openness ratio"""
    try:
        if len(eye_indices) < 6:
            return 0.5  # Default value if not enough landmarks
        
        # Get eye corner points (simplified)
        left_corner = landmarks[eye_indices[0]]
        right_corner = landmarks[eye_indices[3]]
        top_point = landmarks[eye_indices[1]]
        bottom_point = landmarks[eye_indices[4]]
        
        # Calculate eye width and height
        eye_width = abs(right_corner[0] - left_corner[0])
        eye_height = abs(top_point[1] - bottom_point[1])
        
        # Return eye openness ratio
        return eye_height / eye_width if eye_width > 0 else 0.5
        
    except Exception:
        return 0.5  # Default value on error

def detect_and_crop_face_mediapipe(image_array: np.ndarray):
    """Use Mediapipe to detect and crop faces from image"""
    try:
        # Convert RGB to BGR for mediapipe
        image_bgr = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
        
        # Detect faces using Mediapipe
        results = face_detection.process(image_bgr)
        
        if not results.detections:
            return None
        
        # Get the first (most confident) face detection
        detection = results.detections[0]
        
        # Get bounding box
        bbox = detection.location_data.relative_bounding_box
        h, w, _ = image_array.shape
        
        # Convert relative coordinates to absolute
        x = int(bbox.xmin * w)
        y = int(bbox.ymin * h)
        width = int(bbox.width * w)
        height = int(bbox.height * h)
        
        # Add some padding around the face
        padding = 20
        x = max(0, x - padding)
        y = max(0, y - padding)
        width = min(w - x, width + 2 * padding)
        height = min(h - y, height + 2 * padding)
        
        # Crop the face
        face_crop = image_array[y:y+height, x:x+width]
        
        return face_crop
        
    except Exception as e:
        print(f"Mediapipe face detection error: {str(e)}")
        return None

def generate_face_embedding_simple(face_image: np.ndarray):
    """Generate a simple face representation using basic image features"""
    try:
        # Convert to grayscale
        if len(face_image.shape) == 3:
            gray = cv2.cvtColor(face_image, cv2.COLOR_RGB2GRAY)
        else:
            gray = face_image
            
        # Resize to standard size
        resized = cv2.resize(gray, (100, 100))
        
        # Normalize pixel values
        normalized = resized.astype(np.float32) / 255.0
        
        # Flatten to create a simple "embedding"
        embedding = normalized.flatten().tolist()
        
        return embedding
        
    except Exception as e:
        print(f"Simple face embedding generation error: {str(e)}")
        return None

def decode_base64_image(base64_string: str) -> np.ndarray:
    """Decode base64 image to numpy array for image processing"""
    try:
        # Remove data URL prefix if present
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        
        # Decode base64
        image_data = base64.b64decode(base64_string)
        
        # Convert to PIL Image
        pil_image = Image.open(BytesIO(image_data))
        
        # Convert to RGB if necessary
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        # Convert to numpy array
        image_array = np.array(pil_image)
        
        return image_array
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image format: {str(e)}")

async def get_current_user(authorization: HTTPAuthorizationCredentials = Depends(security), session_token: Optional[str] = Cookie(None)):
    """Get current user from session token"""
    token = None
    if authorization:
        token = authorization.credentials
    elif session_token:
        token = session_token
    
    if not token:
        raise HTTPException(status_code=401, detail="No authentication token provided")
    
    # Find user session in database
    session = await db.sessions.find_one({"session_token": token})
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session token")
    
    # Check if session is expired
    expires_at = session['expires_at']
    current_time = datetime.now(timezone.utc)
    
    # Ensure both datetimes are timezone-aware for comparison
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if expires_at < current_time:
        await db.sessions.delete_one({"session_token": token})
        raise HTTPException(status_code=401, detail="Session expired")
    
    # Get user data
    user_doc = await db.users.find_one({"id": session['user_id']})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Remove MongoDB _id field to avoid serialization issues
    if '_id' in user_doc:
        del user_doc['_id']
    
    return user_doc

async def require_admin(current_user: dict = Depends(get_current_user)):
    """Require admin role"""
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# Pydantic Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    picture: Optional[str] = None
    role: str = "teacher"  # admin, teacher
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserCreate(BaseModel):
    email: str
    name: str
    picture: Optional[str] = None
    role: str = "teacher"

class Class(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    grade: str
    section: str
    teacher_id: Optional[str] = None
    teacher_name: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ClassCreate(BaseModel):
    name: str
    grade: str
    section: str
    teacher_id: Optional[str] = None

class Student(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    roll_number: str
    class_id: str
    is_enrolled: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StudentCreate(BaseModel):
    name: str
    roll_number: str
    class_id: str

class FaceEmbedding(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    embedding: List[float]
    model_name: str = "Simple_CV"  # Simple OpenCV-based approach
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AttendanceRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    student_name: str
    class_id: str
    date: str  # YYYY-MM-DD format
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: float
    marked_by: str

class AttendanceRecordCreate(BaseModel):
    class_id: str
    date: str

class SessionData(BaseModel):
    session_id: str

class LoginResponse(BaseModel):
    user: User
    redirect_url: str

# Authentication Routes
@api_router.get("/auth/login")
async def login():
    """Redirect to Emergent OAuth"""
    preview_url = os.environ.get('PREVIEW_URL', 'https://smart-attendance-21.preview.emergentagent.com')
    auth_url = f"https://auth.emergentagent.com/?redirect={preview_url}/profile"
    return {"auth_url": auth_url}

@api_router.post("/auth/session")
async def create_session(session_data: SessionData, response: Response):
    """Create session from OAuth callback"""
    try:
        logger.info(f"Creating session for session_id: {session_data.session_id}")
        
        # Call Emergent auth API to get user data
        headers = {"X-Session-ID": session_data.session_id}
        logger.info(f"Calling Emergent auth API with headers: {headers}")
        
        auth_response = requests.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers=headers
        )
        
        logger.info(f"Emergent auth API response status: {auth_response.status_code}")
        logger.info(f"Emergent auth API response: {auth_response.text}")
        
        if auth_response.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Invalid session ID. Auth API returned: {auth_response.status_code} - {auth_response.text}")
        
        user_data = auth_response.json()
        logger.info(f"User data from auth API: {user_data}")
        
        # Check if user exists, if not create new user
        existing_user = await db.users.find_one({"email": user_data["email"]})
        
        if not existing_user:
            # Determine role: chiluverushivaprasad02@gmail.com is admin, others are teachers
            if user_data["email"] == "chiluverushivaprasad02@gmail.com":
                role = "admin"
            else:
                role = "teacher"
            
            logger.info(f"Creating new user with role: {role}")
            
            new_user = User(
                id=str(uuid.uuid4()),
                email=user_data["email"],
                name=user_data["name"],
                picture=user_data.get("picture"),
                role=role
            )
            user_dict = new_user.dict()
            await db.users.insert_one(user_dict)
            user = user_dict
        else:
            logger.info(f"Found existing user: {existing_user['email']}")
            # Remove MongoDB _id field to avoid serialization issues
            user = existing_user.copy()
            if '_id' in user:
                del user['_id']
        
        # Create session
        session_token = user_data["session_token"]
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        
        session = {
            "session_token": session_token,
            "user_id": user["id"],
            "expires_at": expires_at
        }
        
        # Remove old sessions and create new one
        await db.sessions.delete_many({"user_id": user["id"]})
        await db.sessions.insert_one(session)
        
        logger.info(f"Created session for user: {user['email']}")
        
        # Set secure cookie
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=True,
            samesite="none",
            max_age=7 * 24 * 60 * 60,  # 7 days
            path="/"
        )
        
        return {"user": user, "session_token": session_token}
        
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")

@api_router.post("/auth/logout")
async def logout(response: Response, current_user: dict = Depends(get_current_user)):
    """Logout user"""
    # Delete session from database
    await db.sessions.delete_many({"user_id": current_user["id"]})
    
    # Clear cookie
    response.delete_cookie(key="session_token", path="/")
    
    return {"message": "Logged out successfully"}

@api_router.get("/auth/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    return {"user": current_user}

# Admin Routes
@api_router.post("/admin/reset-system")
async def reset_system():
    """Reset system by clearing all users, sessions, classes, students, and attendance data"""
    try:
        # Clear all collections
        await db.users.delete_many({})
        await db.sessions.delete_many({})
        await db.classes.delete_many({})
        await db.students.delete_many({})
        await db.face_embeddings.delete_many({})
        await db.attendance_records.delete_many({})
        
        return {"message": "System reset successfully. All data cleared."}
        
    except Exception as e:
        logger.error(f"Error resetting system: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to reset system: {str(e)}")

@api_router.get("/admin/classes", response_model=List[Class])
async def get_classes(admin: dict = Depends(require_admin)):
    """Get all classes"""
    classes = await db.classes.find().to_list(1000)
    # Remove MongoDB _id fields
    for class_doc in classes:
        if '_id' in class_doc:
            del class_doc['_id']
    return [Class(**class_doc) for class_doc in classes]

@api_router.post("/admin/classes", response_model=Class)
async def create_class(class_data: ClassCreate, admin: dict = Depends(require_admin)):
    """Create new class"""
    try:
        # Get teacher info if teacher_id provided
        teacher_name = None
        if class_data.teacher_id:
            teacher = await db.users.find_one({"id": class_data.teacher_id})
            if teacher:
                teacher_name = teacher["name"]
        
        new_class = Class(
            name=class_data.name,
            grade=class_data.grade,
            section=class_data.section,
            teacher_id=class_data.teacher_id,
            teacher_name=teacher_name
        )
        
        class_dict = new_class.dict()
        await db.classes.insert_one(class_dict)
        
        # Remove _id for response
        if '_id' in class_dict:
            del class_dict['_id']
        
        return Class(**class_dict)
        
    except Exception as e:
        logger.error(f"Error creating class: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create class: {str(e)}")

@api_router.get("/admin/teachers")
async def get_teachers(admin: dict = Depends(require_admin)):
    """Get all teachers"""
    teachers = await db.users.find({"role": "teacher"}).to_list(1000)
    # Remove MongoDB _id fields and return only necessary fields
    return [{"id": t["id"], "name": t["name"], "email": t["email"]} for t in teachers]

@api_router.put("/admin/classes/{class_id}")
async def assign_teacher(class_id: str, teacher_id: str, admin: dict = Depends(require_admin)):
    """Assign teacher to class"""
    # Get teacher info
    teacher = await db.users.find_one({"id": teacher_id})
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    # Update class
    result = await db.classes.update_one(
        {"id": class_id},
        {"$set": {"teacher_id": teacher_id, "teacher_name": teacher["name"]}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Class not found")
    
    return {"message": "Teacher assigned successfully"}

# Teacher Routes
@api_router.get("/teacher/classes")
async def get_teacher_classes(current_user: dict = Depends(get_current_user)):
    """Get classes assigned to current teacher"""
    classes = await db.classes.find({"teacher_id": current_user["id"]}).to_list(1000)
    # Remove MongoDB _id fields
    for class_doc in classes:
        if '_id' in class_doc:
            del class_doc['_id']
    return [Class(**class_doc) for class_doc in classes]

@api_router.get("/teacher/classes/{class_id}/students")
async def get_class_students(class_id: str, current_user: dict = Depends(get_current_user)):
    """Get students in a class"""
    # Check if teacher has access to this class (or is admin)
    if current_user["role"] != "admin":
        class_doc = await db.classes.find_one({"id": class_id, "teacher_id": current_user["id"]})
        if not class_doc:
            raise HTTPException(status_code=403, detail="Access denied to this class")
    
    students = await db.students.find({"class_id": class_id}).to_list(1000)
    # Remove MongoDB _id fields
    for student in students:
        if '_id' in student:
            del student['_id']
    return [Student(**student) for student in students]

@api_router.post("/teacher/classes/{class_id}/students")
async def add_student(class_id: str, student_data: StudentCreate, current_user: dict = Depends(get_current_user)):
    """Add student to class"""
    # Check if teacher has access to this class (or is admin)
    if current_user["role"] != "admin":
        class_doc = await db.classes.find_one({"id": class_id, "teacher_id": current_user["id"]})
        if not class_doc:
            raise HTTPException(status_code=403, detail="Access denied to this class")
    
    # Check if roll number is unique in class
    existing = await db.students.find_one({"class_id": class_id, "roll_number": student_data.roll_number})
    if existing:
        raise HTTPException(status_code=400, detail="Roll number already exists in this class")
    
    new_student = Student(
        name=student_data.name,
        roll_number=student_data.roll_number,
        class_id=class_id
    )
    
    await db.students.insert_one(new_student.dict())
    return new_student

# Student Enrollment Routes
@api_router.post("/students/{student_id}/enroll")
async def enroll_student_face(student_id: str, image_data: dict, current_user: dict = Depends(get_current_user)):
    """Enroll student with face data"""
    try:
        # Get student
        student = await db.students.find_one({"id": student_id})
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        
        # Check teacher access to this class
        if current_user["role"] != "admin":
            class_doc = await db.classes.find_one({"id": student["class_id"], "teacher_id": current_user["id"]})
            if not class_doc:
                raise HTTPException(status_code=403, detail="Access denied to this class")
        
        # Decode image
        image_array = decode_base64_image(image_data["image"])
        
        # Step 1: Detect and crop face using Mediapipe
        face_crop = detect_and_crop_face_mediapipe(image_array)
        if face_crop is None:
            raise HTTPException(status_code=400, detail="No face detected in image. Please ensure the face is clearly visible and try again.")
        
        # Step 2: Generate face embedding (currently disabled)
        embedding = generate_face_embedding_simple(face_crop)
        if embedding is None:
            raise HTTPException(status_code=400, detail="Failed to generate face embedding. Please try with a clearer image.")
        
        # Store embedding
        face_embedding = FaceEmbedding(
            student_id=student_id,
            embedding=embedding,
            model_name="Simple_CV"
        )
        
        # Remove old embeddings and add new one
        await db.face_embeddings.delete_many({"student_id": student_id})
        await db.face_embeddings.insert_one(face_embedding.dict())
        
        # Mark student as enrolled
        await db.students.update_one(
            {"id": student_id},
            {"$set": {"is_enrolled": True}}
        )
        
        return {"message": "Student enrolled successfully", "embedding_id": face_embedding.id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enrollment failed: {str(e)}")

# Attendance Routes
@api_router.post("/attendance/mark")
async def mark_attendance(attendance_data: dict, current_user: dict = Depends(get_current_user)):
    """Mark attendance using face recognition"""
    try:
        class_id = attendance_data["class_id"]
        image_data = attendance_data["image"]
        date = attendance_data["date"]
        
        # Check teacher access to this class
        if current_user["role"] != "admin":
            class_doc = await db.classes.find_one({"id": class_id, "teacher_id": current_user["id"]})
            if not class_doc:
                raise HTTPException(status_code=403, detail="Access denied to this class")
        
        # Decode image
        image_array = decode_base64_image(image_data)
        
        # Step 1: Detect and crop face using Mediapipe
        face_crop = detect_and_crop_face_mediapipe(image_array)
        if face_crop is None:
            raise HTTPException(status_code=400, detail="No face detected in image. Please ensure the face is clearly visible and try again.")
        
        # Step 2: Generate embedding for the input image (currently disabled)
        input_embedding = generate_face_embedding_simple(face_crop)
        if input_embedding is None:
            raise HTTPException(status_code=400, detail="Failed to process face. Please try with a clearer image.")
        
        input_vector = np.array(input_embedding)
        
        # Get all enrolled students in this class
        students = await db.students.find({"class_id": class_id, "is_enrolled": True}).to_list(1000)
        
        if not students:
            raise HTTPException(status_code=400, detail="No enrolled students in this class")
        
        # Find matching student using simplified comparison
        best_match = None
        best_distance = float('inf')
        recognition_threshold = 0.3  # Adjusted threshold for simple CV approach
        
        for student in students:
            # Get student's face embedding
            embedding_doc = await db.face_embeddings.find_one({"student_id": student["id"]})
            if not embedding_doc:
                continue
            
            stored_vector = np.array(embedding_doc["embedding"])
            
            # Calculate Euclidean distance for simple embeddings
            distance = np.linalg.norm(input_vector - stored_vector)
            
            if distance < best_distance:
                best_distance = distance
                best_match = student
        
        if best_match is None or best_distance > recognition_threshold:
            return {
                "recognized": False,
                "message": "Student not recognized",
                "confidence": 0.0
            }
        
        # Check if already marked present today
        existing_record = await db.attendance_records.find_one({
            "student_id": best_match["id"],
            "date": date
        })
        
        if existing_record:
            return {
                "recognized": True,
                "student": best_match,
                "message": "Student already marked present today",
                "confidence": 1.0 - best_distance,
                "already_marked": True
            }
        
        # Create attendance record
        attendance_record = AttendanceRecord(
            student_id=best_match["id"],
            student_name=best_match["name"],
            class_id=class_id,
            date=date,
            confidence=1.0 - best_distance,
            marked_by=current_user["id"]
        )
        
        await db.attendance_records.insert_one(attendance_record.dict())
        
        return {
            "recognized": True,
            "student": best_match,
            "message": "Attendance marked successfully",
            "confidence": 1.0 - best_distance,
            "already_marked": False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Attendance marking failed: {str(e)}")

@api_router.get("/attendance/{class_id}/{date}")
async def get_attendance(class_id: str, date: str, current_user: dict = Depends(get_current_user)):
    """Get attendance for a class on a specific date"""
    # Check teacher access to this class
    if current_user["role"] != "admin":
        class_doc = await db.classes.find_one({"id": class_id, "teacher_id": current_user["id"]})
        if not class_doc:
            raise HTTPException(status_code=403, detail="Access denied to this class")
    
    # Get attendance records
    attendance_records = await db.attendance_records.find({
        "class_id": class_id,
        "date": date
    }).to_list(1000)
    
    # Get all students in class
    all_students = await db.students.find({"class_id": class_id}).to_list(1000)
    
    # Mark present/absent
    present_student_ids = {record["student_id"] for record in attendance_records}
    
    attendance_summary = []
    for student in all_students:
        is_present = student["id"] in present_student_ids
        record = next((r for r in attendance_records if r["student_id"] == student["id"]), None)
        
        attendance_summary.append({
            "student_id": student["id"],
            "student_name": student["name"],
            "roll_number": student["roll_number"],
            "is_present": is_present,
            "timestamp": record["timestamp"] if record else None,
            "confidence": record["confidence"] if record else None
        })
    
    return {
        "class_id": class_id,
        "date": date,
        "total_students": len(all_students),
        "present_count": len(attendance_records),
        "absent_count": len(all_students) - len(attendance_records),
        "attendance": attendance_summary
    }

# Health check
@api_router.get("/")
async def root():
    return {"message": "Rural School Attendance System API", "status": "running"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc)}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()