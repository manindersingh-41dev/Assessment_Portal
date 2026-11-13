/**
 * Central Environment & API Configuration
 * All backend routes and application metadata are declared here.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const APP_NAME = 'Geeta Assessment Portal';
const APP_VERSION = '1.0.0';

export const config = {
  api: {
    baseURL: API_BASE_URL,
    timeout: 30000,
    endpoints: {
      // Authentication & User lifecycle
      auth: {
        login: '/auth/login/',
        token: '/token/',
        refresh: '/token/refresh/',
        verifyToken: '/token/verify/',
        registerStudent: '/auth/register/student/',
        registerFaculty: '/auth/register/faculty/',
        verifyEmail: '/auth/verify-email/',
        resendOtp: '/auth/resend-otp/',
        passwordResetRequest: '/auth/password-reset-request/',
        passwordReset: '/auth/password-reset/',
        logout: '/auth/logout/',
        profile: '/auth/profile/',
        studentProfile: '/auth/profile/student/',
        facultyProfile: '/auth/profile/faculty/',
      },
      // Questions Bank
      questions: {
        list: '/questions/questions/',
        detail: (id) => `/questions/questions/${id}/`,
        create: '/questions/questions/',
        bulkCreate: '/questions/questions/bulk/',
        update: (id) => `/questions/questions/${id}/`,
        delete: (id) => `/questions/questions/${id}/`,
        testCasesForQuestion: (id) => `/questions/questions/${id}/test_cases/`,
        testCaseCreate: '/questions/test-cases/',
        testCaseUpdate: (id) => `/questions/test-cases/${id}/`,
        testCaseDelete: (id) => `/questions/test-cases/${id}/`,
      },
      // Assessments
      assessments: {
        list: '/assessments/assessments/',
        detail: (id) => `/assessments/assessments/${id}/`,
        create: '/assessments/assessments/',
        update: (id) => `/assessments/assessments/${id}/`,
        delete: (id) => `/assessments/assessments/${id}/`,
        publish: (id) => `/assessments/assessments/${id}/publish/`,
        archive: (id) => `/assessments/assessments/${id}/archive/`,
        assign: (id) => `/assessments/assessments/${id}/assign/`,
        assignments: (id) => `/assessments/assessments/${id}/assignments/`,
        myAssignments: '/assessments/assignments/',
        startAssignment: (id) => `/assessments/assignments/${id}/start/`,
        assignmentDetail: (id) => `/assessments/assignments/${id}/`,
        flagCheating: (id) => `/assessments/assignments/${id}/flag-cheating/`,
        clearCheatingFlag: (id) => `/assessments/assignments/${id}/clear-cheating-flag/`,
        submitAssignment: (id) => `/assessments/assignments/${id}/submit/`,
        assignmentDrafts: (id) => `/assessments/assignments/${id}/drafts/`,
        retryNotification: (assignmentId, notificationId) => `/assessments/assignments/${assignmentId}/notifications/${notificationId}/retry/`,
        statistics: '/assessments/assessments/statistics/',
      },
      // Code Execution & Submissions
      submissions: {
        run: '/submissions/run/',
        create: '/submissions/create/',
        executionCases: '/submissions/execution-cases/',
        clientEvaluations: '/submissions/client-evaluations/',
        clientEvaluationResults: (id) => `/submissions/client-evaluations/${id}/results/`,
        list: '/submissions/submissions/',
        byAssignment: (id) => `/submissions/list/by_assignment/${id}/`,
        detail: (id) => `/submissions/submissions/${id}/`,
        status: (id) => `/submissions/status/${id}/`,
        retryEvaluation: (id) => `/submissions/status/${id}/retry/`,
      },
      // Results & Analytics
      results: {
        studentHistory: '/results/submissions/history/',
        studentResults: '/results/submissions/results/',
        studentAssignmentResult: '/results/submissions/assignment_result/',
        facultyOverview: '/results/faculty/assessment_overview/',
        facultyStatistics: '/results/faculty/assessment_statistics/',
        facultySubmissionDetails: '/results/faculty/submission_details/',
        facultyStudentWiseResults: '/results/faculty/student_wise_results/',
        facultyEvaluateAssessment: '/results/faculty/evaluate_assessment/',
        exportCSV: '/results/faculty/export_csv/',
      },
      // User directory
      users: {
        studentsList: '/users/?role=student',
        clearLoginLock: (studentId) => `/users/${studentId}/login-lock/`,
      },
    },
  },
  app: {
    name: APP_NAME,
    version: APP_VERSION,
  },
  auth: {
    tokenKey: 'access_token',
    refreshTokenKey: 'refresh_token',
    tokenExpiry: 60 * 60 * 1000, // 1 hour
  },
  theme: {
    defaultMode: 'light',
  },
  pagination: {
    defaultPageSize: 20,
  },
};

export default config;
