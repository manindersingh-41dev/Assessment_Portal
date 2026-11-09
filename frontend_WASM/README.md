# Geeta University Coding Assessment Portal - Frontend

**Modern, Professional React.js Frontend for Coding Assessments**

---

## 📋 Project Overview

A feature-rich, responsive frontend for the Geeta University Coding Assessment Portal. This application provides a comprehensive coding assessment experience for students and management tools for faculty.

- **React 19.3** - Modern UI development
- **Vite** - High-performance build tool
- **Tailwind CSS** - Utility-first styling
- **React Router** - Client-side routing
- **Zustand** - Global state management
- **Axios** - HTTP client for API interaction
- **Monaco Editor** - Professional coding environment

---

## 🎯 Key Features

### Authentication & Authorization
- University email-based registration and login (`@geetauniversity.edu.in`)
- Role-based access control (Student/Faculty)
- Secure JWT-based authentication with auto-refresh mechanism

### Student Portal
- Dashboard for viewing upcoming, active, and completed assessments
- Immersive coding environment with Monaco Editor (C support)
- Timer-based assessments with automatic submission
- Submission history and evaluation results tracking

### Faculty Portal
- Question Bank management (Create, Edit, Delete)
- Comprehensive Assessment Wizard (5-step creation, student assignment)
- Dashboard analytics and student performance tracking
- CSV export for assessment results

---

## 🚀 Getting Started

### Prerequisites
- Node.js (v18+)
- npm
- Django backend running at `http://localhost:8000`

### Installation
```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Configure environment variables
cp .env.example .env
# Set VITE_API_URL in .env to your backend URL (e.g., http://localhost:8000/api)

# Start development server
npm run dev
```

### Build for Production
```bash
npm run build
```

---

## 📁 Project Structure

```
frontend/
├── src/
│   ├── api/            # API services and Axios configuration
│   ├── components/     # Reusable UI components (Button, Input, Editor, etc.)
│   ├── constants/      # App-wide constants and API configurations
│   ├── layouts/        # Page layouts (AppLayout, AuthLayout, CodingLayout)
│   ├── pages/          # Feature-specific pages (Student/Faculty/Auth)
│   ├── store/          # Zustand state management
│   └── utils/          # Helper functions and route protection
├── public/             # Static assets
└── vite.config.js      # Vite build configuration
```

---

## 🔗 Backend Integration

The frontend is fully integrated with the Django backend. All API interactions are managed through `src/api/client.js` with centralized endpoint definitions in `src/constants/config.js`.

---

**Status**: ✅ System Fully Integrated and Verified
