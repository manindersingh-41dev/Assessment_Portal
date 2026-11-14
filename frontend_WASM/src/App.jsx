/** Application route tree. */

import React, { useEffect } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { useAuthStore } from './store/authStore.js';
import { useThemeStore } from './store/themeStore.js';
import ToastContainer from './components/Toast.jsx';
import ProtectedRoute from './utils/ProtectedRoute.jsx';

import AuthLayout from './layouts/AuthLayout.jsx';
import AppLayout from './layouts/AppLayout.jsx';
import CodingLayout from './layouts/CodingLayout.jsx';
import StudentPortalProtection from './layouts/StudentPortalProtection.jsx';

import LoginPage from './pages/LoginPage.jsx';
import RegisterPage from './pages/RegisterPage.jsx';
import VerifyOTPPage from './pages/VerifyOTPPage.jsx';
import ForgotPasswordPage from './pages/ForgotPasswordPage.jsx';
import ResetPasswordPage from './pages/ResetPasswordPage.jsx';

import StudentDashboard from './pages/student/StudentDashboard.jsx';
import StudentSubmissionsPage from './pages/student/StudentSubmissionsPage.jsx';
import StudentResultsPage from './pages/student/StudentResultsPage.jsx';
import StudentAssessmentDetailsPage from './pages/student/StudentAssessmentDetailsPage.jsx';
import AssessmentAttemptPage from './pages/student/AssessmentAttemptPage.jsx';
import ChildrenDayPage from './pages/student/ChildrenDayPage.jsx';

import FacultyDashboard from './pages/faculty/FacultyDashboard.jsx';
import QuestionBankPage from './pages/faculty/QuestionBankPage.jsx';
import CreateQuestionPage from './pages/faculty/CreateQuestionPage.jsx';
import AssessmentsPage from './pages/faculty/AssessmentsPage.jsx';
import AssessmentDetailsPage from './pages/faculty/AssessmentDetailsPage.jsx';
import CreateAssessmentPage from './pages/faculty/CreateAssessmentPage.jsx';
import AssessmentEditPage from './pages/faculty/AssessmentEditPage.jsx';
import ResultsPage from './pages/faculty/ResultsPage.jsx';
import StudentAccessPage from './pages/faculty/StudentAccessPage.jsx';
import FacultyProfilePage from './pages/faculty/FacultyProfilePage.jsx';
import NotFoundPage from './pages/NotFoundPage.jsx';

export function App() {
  useEffect(() => {
    useAuthStore.getState().initialize();
    useThemeStore.getState().initializeTheme();
  }, []);

  return (
    <>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/login" replace />} />

          <Route element={<ProtectedRoute guestOnly><AuthLayout /></ProtectedRoute>}>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/verify-otp" element={<VerifyOTPPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
          </Route>

          <Route element={<ProtectedRoute requiredRole="student"><StudentPortalProtection /></ProtectedRoute>}>
            <Route path="/childrens-day" element={<ChildrenDayPage />} />
            <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
              <Route path="/dashboard" element={<StudentDashboard />} />
              <Route path="/student/dashboard" element={<StudentDashboard />} />
              <Route path="/student/assessments" element={<StudentDashboard />} />
              <Route path="/student/assessments/active" element={<StudentDashboard filter="active" />} />
              <Route path="/student/assessments/upcoming" element={<StudentDashboard filter="upcoming" />} />
              <Route path="/student/assessments/completed" element={<StudentDashboard filter="completed" />} />
              <Route path="/student/assessments/:id" element={<StudentAssessmentDetailsPage />} />
              <Route path="/student/submissions" element={<StudentSubmissionsPage />} />
              <Route path="/student/results" element={<StudentResultsPage />} />
              <Route path="/student/profile" element={<FacultyProfilePage />} />
            </Route>
            <Route element={<CodingLayout />}>
              <Route path="/assessment/:id" element={<AssessmentAttemptPage />} />
            </Route>
          </Route>

          <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
            <Route element={<ProtectedRoute requiredRole="faculty" />}>
              <Route path="/faculty/dashboard" element={<FacultyDashboard />} />
              <Route path="/faculty/questions" element={<QuestionBankPage />} />
              <Route path="/faculty/questions/create" element={<CreateQuestionPage />} />
              <Route path="/faculty/questions/:id/edit" element={<CreateQuestionPage />} />
              <Route path="/faculty/assessments" element={<AssessmentsPage />} />
              <Route path="/faculty/assessments/create" element={<CreateAssessmentPage />} />
              <Route path="/faculty/assessments/:id" element={<AssessmentDetailsPage />} />
              <Route path="/faculty/assessments/:id/edit" element={<AssessmentEditPage />} />
              <Route path="/faculty/results" element={<ResultsPage />} />
              <Route path="/faculty/students" element={<StudentAccessPage />} />
              <Route path="/faculty/profile" element={<FacultyProfilePage />} />
            </Route>
          </Route>

          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
      <ToastContainer />
    </>
  );
}

export default App;
