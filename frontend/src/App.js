import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { Card, CardHeader, CardTitle, CardContent } from './components/ui/card';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './components/ui/select';
import { Badge } from './components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from './components/ui/avatar';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from './components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Alert, AlertDescription } from './components/ui/alert';
import { Camera, Users, BookOpen, CheckCircle, XCircle, UserPlus, Settings, LogOut, School, Eye, EyeOff } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Axios interceptor for handling authentication
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('user');
      window.location.href = '/';
    }
    return Promise.reject(error);
  }
);

// Auth Context
const AuthContext = React.createContext();

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`, { withCredentials: true });
      setUser(response.data.user);
    } catch (error) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (sessionId) => {
    try {
      const response = await axios.post(
        `${API}/auth/session`,
        { session_id: sessionId },
        { withCredentials: true }
      );
      setUser(response.data.user);
      return response.data.user;
    } catch (error) {
      throw error;
    }
  };

  const logout = async () => {
    try {
      await axios.post(`${API}/auth/logout`, {}, { withCredentials: true });
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading, checkAuth }}>
      {children}
    </AuthContext.Provider>
  );
};

const useAuth = () => {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Landing Page Component
const LandingPage = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  useEffect(() => {
    if (user) {
      if (user.role === 'admin') {
        navigate('/admin');
      } else {
        navigate('/teacher');
      }
    }
  }, [user, navigate]);

  const handleLogin = async () => {
    try {
      const response = await axios.get(`${API}/auth/login`);
      window.location.href = response.data.auth_url;
    } catch (error) {
      console.error('Login error:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-blue-50 to-indigo-100">
      <div className="container mx-auto px-6 py-16">
        <div className="text-center max-w-4xl mx-auto">
          <div className="mb-8">
            <School className="h-20 w-20 text-emerald-600 mx-auto mb-6" />
            <h1 className="text-5xl font-bold text-gray-900 mb-6 font-inter">
              Rural School Attendance System
            </h1>
            <p className="text-xl text-gray-600 mb-8 leading-relaxed">
              Revolutionizing attendance tracking in rural schools with advanced facial recognition technology. 
              Accurate, efficient, and designed for educators.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 mb-12">
            <Card className="border-2 border-emerald-100 hover:border-emerald-200 transition-all duration-300 hover:shadow-lg">
              <CardContent className="p-6 text-center">
                <Camera className="h-12 w-12 text-emerald-600 mx-auto mb-4" />
                <h3 className="text-lg font-semibold mb-2">Smart Recognition</h3>
                <p className="text-gray-600">AI-powered facial recognition for accurate student identification</p>
              </CardContent>
            </Card>

            <Card className="border-2 border-blue-100 hover:border-blue-200 transition-all duration-300 hover:shadow-lg">
              <CardContent className="p-6 text-center">
                <Users className="h-12 w-12 text-blue-600 mx-auto mb-4" />
                <h3 className="text-lg font-semibold mb-2">Easy Management</h3>
                <p className="text-gray-600">Simple class and student management for teachers and administrators</p>
              </CardContent>
            </Card>

            <Card className="border-2 border-indigo-100 hover:border-indigo-200 transition-all duration-300 hover:shadow-lg">
              <CardContent className="p-6 text-center">
                <BookOpen className="h-12 w-12 text-indigo-600 mx-auto mb-4" />
                <h3 className="text-lg font-semibold mb-2">Real-time Reports</h3>
                <p className="text-gray-600">Instant attendance reports and analytics for better insights</p>
              </CardContent>
            </Card>
          </div>

          <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md mx-auto">
            <h2 className="text-2xl font-bold text-gray-900 mb-6">Get Started</h2>
            <Button 
              onClick={handleLogin}
              className="w-full py-3 text-lg bg-gradient-to-r from-emerald-600 to-blue-600 hover:from-emerald-700 hover:to-blue-700 transition-all duration-300"
            >
              Sign in with Google
            </Button>
            <p className="text-sm text-gray-500 mt-4">
              Secure authentication powered by Google OAuth
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

// Profile Page Component (OAuth callback handler)
const ProfilePage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const handleCallback = async () => {
      try {
        console.log('OAuth callback - Full URL:', window.location.href);
        console.log('OAuth callback - Hash:', location.hash);
        console.log('OAuth callback - Search:', location.search);
        
        let sessionId = null;
        
        // Try to extract session_id from URL fragment first
        if (location.hash) {
          const hash = location.hash;
          const params = new URLSearchParams(hash.substring(1));
          sessionId = params.get('session_id');
          console.log('Session ID from hash:', sessionId);
        }
        
        // If not found in hash, try search params
        if (!sessionId && location.search) {
          const searchParams = new URLSearchParams(location.search);
          sessionId = searchParams.get('session_id');
          console.log('Session ID from search:', sessionId);
        }
        
        // Also check for common OAuth callback parameters
        if (!sessionId) {
          const searchParams = new URLSearchParams(location.search);
          const hashParams = new URLSearchParams(location.hash.substring(1));
          
          // Check various possible parameter names
          sessionId = sessionId || 
                     searchParams.get('code') || 
                     hashParams.get('code') ||
                     searchParams.get('session') ||
                     hashParams.get('session') ||
                     searchParams.get('token') ||
                     hashParams.get('token');
          
          console.log('Session ID from alternative params:', sessionId);
        }

        if (!sessionId) {
          console.error('No session ID found in URL');
          console.log('Full location object:', location);
          throw new Error('No session ID found in callback URL. The authentication process may have failed. Please try logging in again.');
        }

        console.log('Attempting to login with session_id:', sessionId);
        
        // Login with session ID
        const user = await login(sessionId);
        
        console.log('Login successful, user:', user);
        
        // Redirect based on role
        if (user.role === 'admin') {
          navigate('/admin');
        } else {
          navigate('/teacher');
        }
      } catch (error) {
        console.error('Authentication error details:', error);
        let errorMessage = 'Authentication failed. Please try again.';
        
        if (error.response?.data?.detail) {
          errorMessage = error.response.data.detail;
        } else if (error.message) {
          errorMessage = error.message;
        }
        
        setError(errorMessage);
        
        // Longer timeout and redirect to home
        setTimeout(() => {
          navigate('/');
        }, 8000);
      } finally {
        setLoading(false);
      }
    };

    // Add a small delay to ensure the URL is fully loaded
    const timer = setTimeout(handleCallback, 100);
    
    return () => clearTimeout(timer);
  }, [location, login, navigate]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-emerald-50 to-blue-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-emerald-600 border-t-transparent mx-auto mb-4"></div>
          <p className="text-lg text-gray-600">Completing authentication...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-emerald-50 to-blue-50">
        <Card className="max-w-md mx-auto">
          <CardContent className="p-6 text-center">
            <XCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold mb-2">Authentication Error</h2>
            <p className="text-gray-600 mb-4">{error}</p>
            <Button onClick={() => navigate('/')}>Return to Home</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return null;
};

// Camera Component for capturing photos
const CameraCapture = ({ onCapture, onClose }) => {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [stream, setStream] = useState(null);
  const [capturing, setCapturing] = useState(false);

  useEffect(() => {
    startCamera();
    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  const startCamera = async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          width: 640, 
          height: 480,
          facingMode: 'user'
        } 
      });
      setStream(mediaStream);
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
    } catch (error) {
      console.error('Camera access error:', error);
    }
  };

  const capturePhoto = () => {
    if (videoRef.current && canvasRef.current) {
      setCapturing(true);
      const canvas = canvasRef.current;
      const context = canvas.getContext('2d');
      
      canvas.width = videoRef.current.videoWidth;
      canvas.height = videoRef.current.videoHeight;
      
      context.drawImage(videoRef.current, 0, 0);
      
      const imageData = canvas.toDataURL('image/jpeg', 0.8);
      onCapture(imageData);
      
      setTimeout(() => {
        setCapturing(false);
      }, 500);
    }
  };

  return (
    <div className="space-y-4">
      <div className="relative">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="w-full rounded-lg"
        />
        <canvas ref={canvasRef} style={{ display: 'none' }} />
        {capturing && (
          <div className="absolute inset-0 bg-white opacity-70 rounded-lg flex items-center justify-center">
            <div className="text-2xl font-bold text-gray-800">📸</div>
          </div>
        )}
      </div>
      
      <div className="flex gap-2 justify-center">
        <Button onClick={capturePhoto} className="bg-emerald-600 hover:bg-emerald-700">
          <Camera className="h-4 w-4 mr-2" />
          Capture Photo
        </Button>
        <Button onClick={onClose} variant="outline">
          Cancel
        </Button>
      </div>
    </div>
  );
};

// Admin Dashboard Component
const AdminDashboard = () => {
  const { user, logout } = useAuth();
  const [classes, setClasses] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [showCreateClass, setShowCreateClass] = useState(false);
  const [newClass, setNewClass] = useState({ name: '', grade: '', section: '', teacher_id: '' });

  useEffect(() => {
    fetchClasses();
    fetchTeachers();
  }, []);

  const fetchClasses = async () => {
    try {
      const response = await axios.get(`${API}/admin/classes`, { withCredentials: true });
      setClasses(response.data);
    } catch (error) {
      console.error('Error fetching classes:', error);
    }
  };

  const fetchTeachers = async () => {
    try {
      const response = await axios.get(`${API}/admin/teachers`, { withCredentials: true });
      setTeachers(response.data);
    } catch (error) {
      console.error('Error fetching teachers:', error);
    }
  };

  const createClass = async () => {
    try {
      await axios.post(`${API}/admin/classes`, newClass, { withCredentials: true });
      setNewClass({ name: '', grade: '', section: '', teacher_id: '' });
      setShowCreateClass(false);
      fetchClasses();
    } catch (error) {
      console.error('Error creating class:', error);
    }
  };

  const assignTeacher = async (classId, teacherId) => {
    try {
      await axios.put(`${API}/admin/classes/${classId}?teacher_id=${teacherId}`, {}, { withCredentials: true });
      fetchClasses();
    } catch (error) {
      console.error('Error assigning teacher:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <School className="h-8 w-8 text-emerald-600" />
              <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Avatar className="h-8 w-8">
                  <AvatarImage src={user?.picture} />
                  <AvatarFallback>{user?.name?.charAt(0)}</AvatarFallback>
                </Avatar>
                <span className="text-sm font-medium">{user?.name}</span>
                <Badge variant="secondary">Admin</Badge>
              </div>
              <Button onClick={logout} variant="outline" size="sm">
                <LogOut className="h-4 w-4 mr-2" />
                Logout
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-6 py-8">
        <div className="grid lg:grid-cols-4 gap-6">
          {/* Stats Cards */}
          <div className="lg:col-span-4 grid md:grid-cols-3 gap-6 mb-8">
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center gap-4">
                  <div className="p-3 rounded-full bg-emerald-100">
                    <BookOpen className="h-6 w-6 text-emerald-600" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Total Classes</p>
                    <p className="text-2xl font-bold">{classes.length}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center gap-4">
                  <div className="p-3 rounded-full bg-blue-100">
                    <Users className="h-6 w-6 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Total Teachers</p>
                    <p className="text-2xl font-bold">{teachers.length}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center gap-4">
                  <div className="p-3 rounded-full bg-indigo-100">
                    <Settings className="h-6 w-6 text-indigo-600" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">System Status</p>
                    <p className="text-2xl font-bold text-green-600">Active</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Classes Management */}
          <div className="lg:col-span-4">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Class Management</CardTitle>
                  <Dialog open={showCreateClass} onOpenChange={setShowCreateClass}>
                    <DialogTrigger asChild>
                      <Button className="bg-emerald-600 hover:bg-emerald-700">
                        <UserPlus className="h-4 w-4 mr-2" />
                        Create Class
                      </Button>
                    </DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>Create New Class</DialogTitle>
                      </DialogHeader>
                      <div className="space-y-4">
                        <div>
                          <Label htmlFor="className">Class Name</Label>
                          <Input
                            id="className"
                            value={newClass.name}
                            onChange={(e) => setNewClass({ ...newClass, name: e.target.value })}
                            placeholder="e.g., Mathematics"
                          />
                        </div>
                        <div>
                          <Label htmlFor="grade">Grade</Label>
                          <Input
                            id="grade"
                            value={newClass.grade}
                            onChange={(e) => setNewClass({ ...newClass, grade: e.target.value })}
                            placeholder="e.g., 5"
                          />
                        </div>
                        <div>
                          <Label htmlFor="section">Section</Label>
                          <Input
                            id="section"
                            value={newClass.section}
                            onChange={(e) => setNewClass({ ...newClass, section: e.target.value })}
                            placeholder="e.g., A"
                          />
                        </div>
                        <div>
                          <Label htmlFor="teacher">Assign Teacher (Optional)</Label>
                          <Select onValueChange={(value) => setNewClass({ ...newClass, teacher_id: value })}>
                            <SelectTrigger>
                              <SelectValue placeholder="Select a teacher" />
                            </SelectTrigger>
                            <SelectContent>
                              {teachers.map((teacher) => (
                                <SelectItem key={teacher.id} value={teacher.id}>
                                  {teacher.name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <Button onClick={createClass} className="w-full">
                          Create Class
                        </Button>
                      </div>
                    </DialogContent>
                  </Dialog>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {classes.map((classItem) => (
                    <div key={classItem.id} className="border rounded-lg p-4 hover:bg-gray-50">
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="font-semibold">
                            {classItem.name} - Grade {classItem.grade}{classItem.section}
                          </h3>
                          <p className="text-sm text-gray-600">
                            {classItem.teacher_name ? `Teacher: ${classItem.teacher_name}` : 'No teacher assigned'}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          {classItem.teacher_name ? (
                            <Badge variant="default">Assigned</Badge>
                          ) : (
                            <Select onValueChange={(value) => assignTeacher(classItem.id, value)}>
                              <SelectTrigger className="w-48">
                                <SelectValue placeholder="Assign teacher" />
                              </SelectTrigger>
                              <SelectContent>
                                {teachers.map((teacher) => (
                                  <SelectItem key={teacher.id} value={teacher.id}>
                                    {teacher.name}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                  {classes.length === 0 && (
                    <div className="text-center py-8 text-gray-500">
                      No classes created yet. Create your first class to get started.
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

// Teacher Dashboard Component
const TeacherDashboard = () => {
  const { user, logout } = useAuth();
  const [classes, setClasses] = useState([]);
  const [selectedClass, setSelectedClass] = useState(null);
  const [students, setStudents] = useState([]);
  const [showAddStudent, setShowAddStudent] = useState(false);
  const [showEnrollStudent, setShowEnrollStudent] = useState(false);
  const [showAttendance, setShowAttendance] = useState(false);
  const [newStudent, setNewStudent] = useState({ name: '', roll_number: '' });
  const [enrollingStudent, setEnrollingStudent] = useState(null);
  const [attendanceDate, setAttendanceDate] = useState(new Date().toISOString().split('T')[0]);
  const [attendanceRecords, setAttendanceRecords] = useState(null);

  useEffect(() => {
    fetchClasses();
  }, []);

  useEffect(() => {
    if (selectedClass) {
      fetchStudents(selectedClass.id);
    }
  }, [selectedClass]);

  const fetchClasses = async () => {
    try {
      const response = await axios.get(`${API}/teacher/classes`, { withCredentials: true });
      setClasses(response.data);
      if (response.data.length > 0) {
        setSelectedClass(response.data[0]);
      }
    } catch (error) {
      console.error('Error fetching classes:', error);
    }
  };

  const fetchStudents = async (classId) => {
    try {
      const response = await axios.get(`${API}/teacher/classes/${classId}/students`, { withCredentials: true });
      setStudents(response.data);
    } catch (error) {
      console.error('Error fetching students:', error);
    }
  };

  const addStudent = async () => {
    try {
      await axios.post(
        `${API}/teacher/classes/${selectedClass.id}/students`,
        { ...newStudent, class_id: selectedClass.id },
        { withCredentials: true }
      );
      setNewStudent({ name: '', roll_number: '' });
      setShowAddStudent(false);
      fetchStudents(selectedClass.id);
    } catch (error) {
      console.error('Error adding student:', error);
    }
  };

  const enrollStudentFace = async (imageData) => {
    try {
      await axios.post(
        `${API}/students/${enrollingStudent.id}/enroll`,
        { image: imageData },
        { withCredentials: true }
      );
      setShowEnrollStudent(false);
      setEnrollingStudent(null);
      fetchStudents(selectedClass.id);
    } catch (error) {
      console.error('Error enrolling student:', error);
    }
  };

  const fetchAttendance = async () => {
    try {
      const response = await axios.get(
        `${API}/attendance/${selectedClass.id}/${attendanceDate}`,
        { withCredentials: true }
      );
      setAttendanceRecords(response.data);
    } catch (error) {
      console.error('Error fetching attendance:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <School className="h-8 w-8 text-emerald-600" />
              <h1 className="text-2xl font-bold text-gray-900">Teacher Dashboard</h1>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Avatar className="h-8 w-8">
                  <AvatarImage src={user?.picture} />
                  <AvatarFallback>{user?.name?.charAt(0)}</AvatarFallback>
                </Avatar>
                <span className="text-sm font-medium">{user?.name}</span>
                <Badge variant="secondary">Teacher</Badge>
              </div>
              <Button onClick={logout} variant="outline" size="sm">
                <LogOut className="h-4 w-4 mr-2" />
                Logout
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-6 py-8">
        {classes.length === 0 ? (
          <Card>
            <CardContent className="p-8 text-center">
              <BookOpen className="h-16 w-16 text-gray-400 mx-auto mb-4" />
              <h2 className="text-xl font-semibold mb-2">No Classes Assigned</h2>
              <p className="text-gray-600">Please contact your administrator to assign classes to you.</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-6">
            {/* Class Selector */}
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center gap-4">
                  <Label htmlFor="classSelect">Select Class:</Label>
                  <Select 
                    value={selectedClass?.id} 
                    onValueChange={(value) => setSelectedClass(classes.find(c => c.id === value))}
                  >
                    <SelectTrigger className="w-64">
                      <SelectValue placeholder="Select a class" />
                    </SelectTrigger>
                    <SelectContent>
                      {classes.map((classItem) => (
                        <SelectItem key={classItem.id} value={classItem.id}>
                          {classItem.name} - Grade {classItem.grade}{classItem.section}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>

            {selectedClass && (
              <Tabs defaultValue="students" className="space-y-6">
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="students">Students</TabsTrigger>
                  <TabsTrigger value="attendance">Mark Attendance</TabsTrigger>
                  <TabsTrigger value="reports">View Reports</TabsTrigger>
                </TabsList>

                {/* Students Tab */}
                <TabsContent value="students">
                  <Card>
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <CardTitle>Students in {selectedClass.name}</CardTitle>
                        <Button onClick={() => setShowAddStudent(true)} className="bg-emerald-600 hover:bg-emerald-700">
                          <UserPlus className="h-4 w-4 mr-2" />
                          Add Student
                        </Button>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        {students.map((student) => (
                          <div key={student.id} className="border rounded-lg p-4 hover:bg-gray-50">
                            <div className="flex items-center justify-between">
                              <div>
                                <h3 className="font-semibold">{student.name}</h3>
                                <p className="text-sm text-gray-600">Roll No: {student.roll_number}</p>
                              </div>
                              <div className="flex items-center gap-2">
                                {student.is_enrolled ? (
                                  <Badge variant="default" className="bg-green-500">
                                    <CheckCircle className="h-3 w-3 mr-1" />
                                    Enrolled
                                  </Badge>
                                ) : (
                                  <>
                                    <Badge variant="secondary">
                                      <XCircle className="h-3 w-3 mr-1" />
                                      Not Enrolled
                                    </Badge>
                                    <Button
                                      size="sm"
                                      onClick={() => {
                                        setEnrollingStudent(student);
                                        setShowEnrollStudent(true);
                                      }}
                                      className="bg-blue-600 hover:bg-blue-700"
                                    >
                                      <Camera className="h-3 w-3 mr-1" />
                                      Enroll Face
                                    </Button>
                                  </>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                        {students.length === 0 && (
                          <div className="text-center py-8 text-gray-500">
                            No students added yet. Add students to get started.
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* Attendance Tab */}
                <TabsContent value="attendance">
                  <AttendanceMarking classId={selectedClass.id} />
                </TabsContent>

                {/* Reports Tab */}
                <TabsContent value="reports">
                  <Card>
                    <CardHeader>
                      <CardTitle>Attendance Reports</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        <div className="flex items-center gap-4">
                          <Label htmlFor="reportDate">Select Date:</Label>
                          <Input
                            id="reportDate"
                            type="date"
                            value={attendanceDate}
                            onChange={(e) => setAttendanceDate(e.target.value)}
                            className="w-40"
                          />
                          <Button onClick={fetchAttendance} className="bg-emerald-600 hover:bg-emerald-700">
                            View Attendance
                          </Button>
                        </div>
                        
                        {attendanceRecords && (
                          <div className="border rounded-lg p-4">
                            <div className="mb-4">
                              <h3 className="font-semibold mb-2">
                                Attendance for {attendanceDate}
                              </h3>
                              <div className="grid grid-cols-3 gap-4 text-sm">
                                <div>Total Students: {attendanceRecords.total_students}</div>
                                <div className="text-green-600">Present: {attendanceRecords.present_count}</div>
                                <div className="text-red-600">Absent: {attendanceRecords.absent_count}</div>
                              </div>
                            </div>
                            
                            <div className="space-y-2">
                              {attendanceRecords.attendance.map((record) => (
                                <div key={record.student_id} className="flex items-center justify-between py-2 border-b">
                                  <div>
                                    <span className="font-medium">{record.student_name}</span>
                                    <span className="text-sm text-gray-600 ml-2">({record.roll_number})</span>
                                  </div>
                                  <div className="flex items-center gap-2">
                                    {record.is_present ? (
                                      <>
                                        <Badge variant="default" className="bg-green-500">Present</Badge>
                                        {record.confidence && (
                                          <span className="text-xs text-gray-500">
                                            {Math.round(record.confidence * 100)}% confidence
                                          </span>
                                        )}
                                      </>
                                    ) : (
                                      <Badge variant="secondary">Absent</Badge>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>
              </Tabs>
            )}
          </div>
        )}
      </div>

      {/* Add Student Dialog */}
      <Dialog open={showAddStudent} onOpenChange={setShowAddStudent}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add New Student</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="studentName">Student Name</Label>
              <Input
                id="studentName"
                value={newStudent.name}
                onChange={(e) => setNewStudent({ ...newStudent, name: e.target.value })}
                placeholder="Enter student name"
              />
            </div>
            <div>
              <Label htmlFor="rollNumber">Roll Number</Label>
              <Input
                id="rollNumber"
                value={newStudent.roll_number}
                onChange={(e) => setNewStudent({ ...newStudent, roll_number: e.target.value })}
                placeholder="Enter roll number"
              />
            </div>
            <Button onClick={addStudent} className="w-full">
              Add Student
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Enroll Student Dialog */}
      <Dialog open={showEnrollStudent} onOpenChange={setShowEnrollStudent}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Enroll {enrollingStudent?.name} - Face Recognition</DialogTitle>
          </DialogHeader>
          <CameraCapture
            onCapture={enrollStudentFace}
            onClose={() => setShowEnrollStudent(false)}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
};

// Attendance Marking Component
const AttendanceMarking = ({ classId }) => {
  const [showCamera, setShowCamera] = useState(false);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [date] = useState(new Date().toISOString().split('T')[0]);

  const markAttendance = async (imageData) => {
    setLoading(true);
    try {
      const response = await axios.post(
        `${API}/attendance/mark`,
        {
          class_id: classId,
          image: imageData,
          date: date
        },
        { withCredentials: true }
      );
      setResult(response.data);
      setShowCamera(false);
    } catch (error) {
      console.error('Error marking attendance:', error);
      setResult({
        recognized: false,
        message: error.response?.data?.detail || 'Failed to mark attendance'
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Mark Attendance - {date}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {!showCamera && (
            <div className="text-center">
              <Button
                onClick={() => setShowCamera(true)}
                className="bg-emerald-600 hover:bg-emerald-700 text-lg px-8 py-3"
                disabled={loading}
              >
                <Camera className="h-5 w-5 mr-2" />
                Start Camera
              </Button>
              <p className="text-sm text-gray-600 mt-2">
                Position student's face in front of the camera for recognition
              </p>
            </div>
          )}

          {showCamera && (
            <CameraCapture
              onCapture={markAttendance}
              onClose={() => setShowCamera(false)}
            />
          )}

          {loading && (
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-4 border-emerald-600 border-t-transparent mx-auto mb-2"></div>
              <p>Processing facial recognition...</p>
            </div>
          )}

          {result && (
            <Alert className={result.recognized ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}>
              <div className="flex items-center gap-2">
                {result.recognized ? (
                  <CheckCircle className="h-5 w-5 text-green-600" />
                ) : (
                  <XCircle className="h-5 w-5 text-red-600" />
                )}
                <AlertDescription>
                  <div>
                    <p className="font-medium">{result.message}</p>
                    {result.student && (
                      <div className="mt-2">
                        <p>Student: {result.student.name} (Roll: {result.student.roll_number})</p>
                        <p>Confidence: {Math.round(result.confidence * 100)}%</p>
                        {result.already_marked && (
                          <p className="text-amber-600 font-medium">Already marked present today</p>
                        )}
                      </div>
                    )}
                  </div>
                </AlertDescription>
              </div>
            </Alert>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

// Protected Route Component
const ProtectedRoute = ({ children, requiredRole }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-emerald-50 to-blue-50">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-emerald-600 border-t-transparent"></div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/" replace />;
  }

  if (requiredRole && user.role !== requiredRole) {
    return <Navigate to={user.role === 'admin' ? '/admin' : '/teacher'} replace />;
  }

  return children;
};

// Main App Component
function App() {
  return (
    <div className="App">
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route
              path="/admin"
              element={
                <ProtectedRoute requiredRole="admin">
                  <AdminDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/teacher"
              element={
                <ProtectedRoute requiredRole="teacher">
                  <TeacherDashboard />
                </ProtectedRoute>
              }
            />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </div>
  );
}

export default App;