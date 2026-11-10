"""
Assessment Management API Documentation.

Complete reference for all assessment, assignment, and result endpoints
for the Geeta University Coding Assessment Portal.
"""

# ============================================================================
# ASSESSMENT MANAGEMENT API DOCUMENTATION
# ============================================================================

"""
BASE URL: http://localhost:8000/api/assessments/

All endpoints require authentication and appropriate user role.
Authentication: JWT token in Authorization header
    Authorization: Bearer <access_token>

============================================================================
1. ASSESSMENT MANAGEMENT
============================================================================

### Create Assessment
POST /api/assessments/assessments/

Create a new assessment with optional questions.

Request Body:
{
    "title": "Python Basics Quiz",
    "description": "Test your understanding of Python fundamentals",
    "instructions": "You have 2 hours to complete this assessment. All questions are mandatory.",
    "start_datetime": "2024-11-10T10:00:00Z",
    "end_datetime": "2024-11-10T12:00:00Z",
    "duration_minutes": 120,
    "total_marks": 100,
    "is_open_to_all_students": true,
    "passing_marks": 60,
    "resubmission_policy": "not_allowed",  # not_allowed, once, unlimited
    "shuffle_questions": false,
    "show_results_to_students": true,
    "questions": [
        {
            "question": "uuid-of-question",
            "marks": 50,
            "is_mandatory": true,
            "show_to_students": true
        }
    ]
}

Response (201 Created):
{
    "message": "Assessment created successfully",
    "assessment": {
        "id": "uuid",
        "title": "Python Basics Quiz",
        "description": "...",
        "instructions": "...",
        "start_datetime": "2024-11-10T10:00:00Z",
        "end_datetime": "2024-11-10T12:00:00Z",
        "duration_minutes": 120,
        "total_marks": 100,
        "passing_marks": 60,
        "status": "draft",
        "status_display": "Draft",
        "resubmission_policy": "not_allowed",
        "resubmission_policy_display": "Not Allowed",
        "shuffle_questions": false,
        "show_results_to_students": true,
        "is_published": false,
        "is_open_to_all_students": true,
        "created_by_name": "John Doe",
        "created_at": "2024-11-06T10:00:00Z",
        "updated_at": "2024-11-06T10:00:00Z",
        "questions": [...],
        "question_count": 1,
        "assignment_count": 0
    }
}

Permission: IsApprovedFaculty (faculty only)

Validation:
- Title: Required, non-empty
- Start datetime: Must be in future
- End datetime: Must be after start datetime
- Duration: 1-480 minutes
- Total marks: 1-1000
- Passing marks: <= total marks
- Questions optional at creation

Status: Created in DRAFT status

---

### Get Assessment Details
GET /api/assessments/assessments/{id}/

Retrieve complete assessment details including all questions.

Response (200 OK):
{
    "id": "uuid",
    "title": "Python Basics Quiz",
    "description": "...",
    "instructions": "...",
    "start_datetime": "...",
    "end_datetime": "...",
    "duration_minutes": 120,
    "total_marks": 100,
    "passing_marks": 60,
    "status": "active",
    "status_display": "Active",
    "resubmission_policy": "not_allowed",
    "resubmission_policy_display": "Not Allowed",
    "shuffle_questions": false,
    "show_results_to_students": true,
    "is_published": true,
    "created_by_name": "John Doe",
    "created_at": "...",
    "updated_at": "...",
    "questions": [
        {
            "id": "uuid",
            "question": "uuid",
            "question_details": {
                "id": "uuid",
                "title": "Sum of Numbers",
                "description": "...",
                "input_format": "...",
                "output_format": "...",
                "constraints": "...",
                "sample_input": "...",
                "sample_output": "...",
                "difficulty": "easy",
                "language": "c"
            },
            "question_order": 1,
            "marks": 50,
            "is_mandatory": true,
            "show_to_students": true
        }
    ],
    "question_count": 1,
    "assignment_count": 5
}

Permissions:
- Faculty: Can view their own assessments
- Student: Can view published assessments assigned to them

---

### List Assessments
GET /api/assessments/assessments/

List assessments based on user role.

Query Parameters:
- page: Page number (default: 1)
- page_size: Results per page (default: 10)
- status: Filter by status (draft, active, archived)
- ordering: Sort by field (-created_at, title, total_marks)

Response (200 OK):
{
    "count": 15,
    "next": "http://localhost:8000/api/assessments/assessments/?page=2",
    "previous": null,
    "results": [
        {
            "id": "uuid",
            "title": "Python Basics Quiz",
            "start_datetime": "...",
            "end_datetime": "...",
            "duration_minutes": 120,
            "total_marks": 100,
            "status": "active",
            "status_display": "Active",
            "is_published": true,
            "created_by_name": "John Doe",
            "created_at": "...",
            "question_count": 5,
            "assignment_count": 20,
            "is_active_now": true,
            "is_started": true,
            "is_ended": false
        }
    ]
}

Faculty permissions:
- See only their own assessments

Student permissions:
- See published assessments assigned to them and assessments open to all students

`is_open_to_all_students` defaults to `true`. Published open assessments are
visible to students who register later as well. Set it to `false` to make the
assessment available only to students explicitly assigned through the assign
endpoint. Student access cannot be changed after publication.

---

### Update Assessment
PUT /api/assessments/assessments/{id}/
PATCH /api/assessments/assessments/{id}/

Update assessment details (questions managed via separate endpoints).

Request Body:
{
    "title": "Updated Title",
    "description": "Updated description",
    "passing_marks": 70,
    "show_results_to_students": true
}

Response (200 OK):
{
    "message": "Assessment updated successfully",
    "assessment": {...}
}

Restrictions:
- Cannot change datetime of published active assessments
- Cannot change total marks if assignments exist
- Cannot edit archived assessments

---

### Delete Assessment
DELETE /api/assessments/assessments/{id}/

Delete an assessment (only DRAFT and without assignments).

Response (204 No Content):
(empty response)

Errors:
- 400: Only draft assessments can be deleted
- 400: Cannot delete assessment with active assignments

---

### Publish Assessment
POST /api/assessments/assessments/{id}/publish/

Publish assessment (change to ACTIVE and make visible to students).

Validation:
- Assessment must be in DRAFT status
- Must have at least one question
- Total question marks must equal assessment marks

Response (200 OK):
{
    "message": "Assessment published successfully",
    "assessment": {...}
}

---

### Archive Assessment
POST /api/assessments/assessments/{id}/archive/

Archive assessment (don't use for new assignments but keep in existing).

Response (200 OK):
{
    "message": "Assessment archived successfully",
    "assessment": {...}
}

---

### Get Assessment Statistics
GET /api/assessments/assessments/statistics/

Get statistics about faculty's assessments.

Response (200 OK):
{
    "total_assessments": 10,
    "active_assessments": 3,
    "completed_assessments": 5,
    "upcoming_assessments": 2,
    "total_assignments": 120,
    "completed_assignments": 85,
    "pending_assignments": 35,
    "average_score": 72.5,
    "pass_rate": 78.3
}

Permission: IsApprovedFaculty

---

============================================================================
2. ASSIGNMENT MANAGEMENT
============================================================================

### Assign Assessment to Students
POST /api/assessments/assessments/{id}/assign/

Assign a published assessment to individual students or batches.

Request Body:
{
    "student_ids": ["uuid-1", "uuid-2"],  # Individual students
    "batch_ids": ["uuid-batch-1"],         # OR batches (not both required)
    "deadline": "2024-11-10T14:00:00Z"     # Optional: custom deadline per student
}

Response (201 Created):
{
    "message": "3 assignment(s) created successfully",
    "assignments": [
        {
            "id": "uuid",
            "assessment": "uuid",
            "assessment_title": "Python Basics Quiz",
            "student": "uuid",
            "student_name": "Jane Doe",
            "student_email": "student@geetauniversity.edu.in",
            "status": "assigned",
            "status_display": "Assigned",
            "assigned_at": "2024-11-06T10:00:00Z",
            "started_at": null,
            "submitted_at": null,
            "deadline": null,  # Uses assessment end_datetime if not set
            "marks_obtained": null,
            "passed": null,
            "attempt_number": 1,
            "is_active": false,
            "is_overdue": false
        }
    ]
}

Validation:
- Assessment must be published
- Must provide student_ids OR batch_ids (or both)
- Cannot assign to same student multiple times (same attempt)

Permission: IsAssessmentCreator (assessment creator only)

---

### Get Assessment Assignments
GET /api/assessments/assessments/{id}/assignments/

Get all assignments for an assessment.

Response (200 OK):
{
    "assessment_id": "uuid",
    "assessment_title": "Python Basics Quiz",
    "total_assignments": 50,
    "assignments": [...]
}

Permission: IsAssessmentCreator

---

### Start Assignment
POST /api/assessments/assignments/{id}/start/

Student marks assignment as started (begins timer).

Response (200 OK):
{
    "message": "Assignment started successfully",
    "assignment": {
        "id": "uuid",
        "status": "started",
        "status_display": "Started",
        "started_at": "2024-11-06T10:15:00Z",
        "is_active": true,
        ...
    }
}

Validation:
- Student can only start own assignment
- Assignment must be ASSIGNED status
- Assessment must have started (start_datetime <= now)
- Assessment must not be ended (now <= end_datetime)
- Respects resubmission policy

Permission: Own assignment (student)

---

### Submit Assignment
POST /api/assessments/assignments/{id}/submit/

Student submits completed assignment.

Response (200 OK):
{
    "message": "Assignment submitted successfully",
    "assignment": {
        "id": "uuid",
        "status": "submitted",
        "status_display": "Submitted",
        "submitted_at": "2024-11-06T11:45:00Z",
        ...
    }
}

Validation:
- Student can only submit own assignment
- Assignment must be in STARTED status

Permission: Own assignment (student)

---

### Evaluate Assignment
POST /api/assessments/assignments/{id}/evaluate/

Faculty evaluates submitted assignment and assigns marks.

Request Body:
{
    "marks_obtained": 85,
    "feedback": "Excellent work! All test cases passed."
}

Response (200 OK):
{
    "message": "Assignment evaluated successfully",
    "assignment": {
        "id": "uuid",
        "status": "graded",
        "status_display": "Graded",
        "marks_obtained": 85,
        "passed": true,
        ...
    }
}

Validation:
- Faculty can only evaluate own assessment's assignments
- Assignment must be SUBMITTED status
- marks_obtained must be 0 to total_marks
- Creates/updates AssessmentResult

Permission: IsAssessmentCreator (faculty only)

---

### Get Pending Assignments
GET /api/assessments/assignments/pending/

Get all submitted but not yet evaluated assignments for faculty.

Response (200 OK):
{
    "count": 10,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": "uuid",
            "assessment_title": "Python Basics Quiz",
            "student_name": "Jane Doe",
            "student_email": "student@...",
            "status": "submitted",
            "submitted_at": "2024-11-06T11:45:00Z",
            "marks_obtained": null,
            ...
        }
    ]
}

Permission: IsApprovedFaculty

---

============================================================================
3. STUDENT BATCH MANAGEMENT
============================================================================

### Create Batch
POST /api/assessments/batches/

Create a student batch for bulk assignment.

Request Body:
{
    "name": "CSE 2024 - Batch A",
    "description": "Computer Science batch, year 2, section A",
    "department": "Computer Science",
    "year": 2
}

Response (201 Created):
{
    "message": "Batch created successfully",
    "batch": {
        "id": "uuid",
        "name": "CSE 2024 - Batch A",
        "description": "...",
        "department": "Computer Science",
        "year": 2,
        "created_at": "2024-11-06T10:00:00Z",
        "updated_at": "2024-11-06T10:00:00Z",
        "student_count": 0
    }
}

Permission: IsApprovedFaculty

---

### List Batches
GET /api/assessments/batches/

List all batches (shared resource).

Response (200 OK):
{
    "count": 5,
    "results": [...]
}

---

### Add Students to Batch
POST /api/assessments/batches/{id}/add_students/

Add students to existing batch.

Request Body:
{
    "student_ids": ["uuid-1", "uuid-2", "uuid-3"]
}

Response (200 OK):
{
    "message": "3 student(s) added to batch",
    "batch": {...}
}

---

### Remove Students from Batch
POST /api/assessments/batches/{id}/remove_students/

Remove students from batch.

Request Body:
{
    "student_ids": ["uuid-1"]
}

Response (200 OK):
{
    "message": "Student(s) removed from batch",
    "batch": {...}
}

---

### Get Batch Students
GET /api/assessments/batches/{id}/students/

Get all students in a batch.

Response (200 OK):
{
    "batch_id": "uuid",
    "batch_name": "CSE 2024 - Batch A",
    "student_count": 45,
    "students": [
        {
            "id": "uuid",
            "first_name": "John",
            "last_name": "Doe",
            "email": "student@geetauniversity.edu.in",
            "role": "student"
        }
    ]
}

---

============================================================================
4. ASSESSMENT RESULTS
============================================================================

### Get Results for Assessment
GET /api/assessments/results/?assessment_id={id}

Get results for specific assessment.

Faculty: See all student results for their assessment
Student: See only their own result (if results are visible)

Response (200 OK):
{
    "count": 45,
    "results": [
        {
            "id": "uuid",
            "assessment": "uuid",
            "assessment_title": "Python Basics Quiz",
            "student": "uuid",
            "student_name": "Jane Doe",
            "student_email": "student@...",
            "total_marks_obtained": 85,
            "percentage": 85.0,
            "passed": true,
            "attempted_at": "2024-11-06T11:45:00Z",
            "evaluated_at": "2024-11-06T12:15:00Z",
            "feedback": "Excellent work!"
        }
    ]
}

---

### List My Assessments (Student)
GET /api/assessments/assessments/my_assessments/

Get student's assigned assessments with status.

Response (200 OK):
{
    "count": 8,
    "results": [
        {
            "id": "uuid",
            "title": "Python Basics Quiz",
            "description": "...",
            "instructions": "...",
            "start_datetime": "2024-11-10T10:00:00Z",
            "end_datetime": "2024-11-10T12:00:00Z",
            "duration_minutes": 120,
            "total_marks": 100,
            "passing_marks": 60,
            "assignment_status": "assigned",  # assigned, started, submitted, graded, expired
            "assignment_id": "uuid",
            "can_start": true,
            "started_at": null,
            "submitted_at": null,
            "time_remaining": 3600  # seconds remaining (null if not started)
        }
    ]
}

Permission: Student only

---

============================================================================
5. COMPLETE FACULTY WORKFLOW
============================================================================

### Create, Configure, and Assign Assessment

1. Create Assessment (DRAFT):
POST /api/assessments/assessments/
{
    "title": "...",
    "description": "...",
    "start_datetime": "...",
    "end_datetime": "...",
    "duration_minutes": 120,
    "total_marks": 100,
    "passing_marks": 60
}

2. View Details:
GET /api/assessments/assessments/{id}/

3. Add Questions (if not done during creation):
POST /api/assessments/assessments/{id}/add_question/
{
    "question": "uuid",
    "marks": 50,
    "is_mandatory": true
}

4. Publish Assessment:
POST /api/assessments/assessments/{id}/publish/

5. Assign to Students:
POST /api/assessments/assessments/{id}/assign/
{
    "student_ids": ["uuid-1", "uuid-2"],
    "batch_ids": ["uuid-batch"]
}

6. Monitor Submissions:
GET /api/assessments/assignments/pending/

7. Evaluate Assignments:
POST /api/assessments/assignments/{id}/evaluate/
{
    "marks_obtained": 85,
    "feedback": "Good job"
}

8. View Results:
GET /api/assessments/results/?assessment_id={id}

---

============================================================================
6. COMPLETE STUDENT WORKFLOW
============================================================================

### Take Assessment

1. View My Assessments:
GET /api/assessments/assessments/my_assessments/

2. Start Assessment:
POST /api/assessments/assignments/{assignment_id}/start/

3. View Assessment Questions:
GET /api/assessments/assessments/{id}/
(Contains all questions with sample test cases, never hidden ones)

4. Submit Assignment:
POST /api/assessments/assignments/{assignment_id}/submit/

5. View Results (if enabled):
GET /api/assessments/results/?assessment_id={id}

6. Resubmit if Allowed:
- Check resubmission_policy
- Start new attempt if allowed

---

============================================================================
7. PERMISSION RULES
============================================================================

Faculty can:
- Create assessments
- Edit own draft assessments
- Publish assessments
- Archive assessments
- Add/remove questions from assessments
- Assign assessments to students or batches
- View all assignments for their assessments
- Evaluate submitted assignments
- View all results for their assessments
- Manage student batches

Faculty cannot:
- Access other faculty's assessments
- Modify published assessments
- See hidden test cases before grading

Students can:
- View published assessments assigned to them
- Start assessment within time window
- Submit assessment
- View results if enabled
- Resubmit if allowed per policy
- Cannot access hidden test cases

Cannot see:
- Question bank management
- Assessment creation (no permission)
- Other students' assignments/results

---

============================================================================
8. IMPORTANT RULES
============================================================================

✓ Time Windows
  - Assessments have start and end datetime
  - Students cannot start before start_datetime
  - Students cannot submit after end_datetime
  - Individual deadline can override assessment end_datetime

✓ Duration Enforcement
  - Student must complete within duration_minutes
  - Server enforces deadline = started_at + duration_minutes
  - Server enforces assessment end_datetime (whichever is earlier)

✓ Resubmission Policy
  - NOT_ALLOWED: Student gets one attempt
  - ONCE: Student can resubmit once (2 total attempts)
  - UNLIMITED: Student can resubmit as many times

✓ Marks Configuration
  - Assessment has total_marks and passing_marks
  - Total marks must match sum of question marks
  - Passing marks must be <= total marks
  - Marks assigned per question in assessment

✓ Question Versioning
  - Question snapshot created when added to assessment
  - If original question changes, assessment keeps snapshot
  - Students see snapshot (consistent question)
  - Faculty can change question after assessment (won't affect existing)

✓ Hidden Test Cases
  - Never exposed to students
  - Used only during grading
  - Sample test cases shown for learning

✓ Status Workflow
  - DRAFT: Can edit, cannot assign
  - ACTIVE: Can assign, cannot modify
  - ARCHIVED: Cannot assign, keep in history

---

============================================================================
9. ERROR RESPONSES
============================================================================

All errors follow this format:

{
    "error": "Error title",
    "details": "Detailed error message"
}

Or field-specific errors:

{
    "field_name": ["Error message"],
    "another_field": ["Error message"]
}

Common HTTP Status Codes:
- 200: Success
- 201: Created
- 204: No Content (deleted)
- 400: Bad Request (validation error)
- 401: Unauthorized (not authenticated)
- 403: Forbidden (not faculty or not approved)
- 404: Not Found
- 500: Internal Server Error

---

============================================================================
10. EXAMPLE API CALLS
============================================================================

### Create and Assign Assessment

1. Create assessment:
curl -X POST http://localhost:8000/api/assessments/assessments/ \\
  -H "Authorization: Bearer {token}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "title": "Python Basics",
    "description": "Test Python skills",
    "start_datetime": "2024-11-10T10:00:00Z",
    "end_datetime": "2024-11-10T12:00:00Z",
    "duration_minutes": 120,
    "total_marks": 100,
    "passing_marks": 60
  }'

2. Publish:
curl -X POST http://localhost:8000/api/assessments/assessments/{id}/publish/ \\
  -H "Authorization: Bearer {token}"

3. Assign:
curl -X POST http://localhost:8000/api/assessments/assessments/{id}/assign/ \\
  -H "Authorization: Bearer {token}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "student_ids": ["uuid1", "uuid2"],
    "batch_ids": ["uuid-batch"]
  }'

---

### Student Takes Assessment

1. View assessments:
curl -X GET http://localhost:8000/api/assessments/assessments/my_assessments/ \\
  -H "Authorization: Bearer {student-token}"

2. Start:
curl -X POST http://localhost:8000/api/assessments/assignments/{assignment-id}/start/ \\
  -H "Authorization: Bearer {student-token}"

3. Submit:
curl -X POST http://localhost:8000/api/assessments/assignments/{assignment-id}/submit/ \\
  -H "Authorization: Bearer {student-token}"

---

### Faculty Grades Assessment

1. Get pending:
curl -X GET http://localhost:8000/api/assessments/assignments/pending/ \\
  -H "Authorization: Bearer {faculty-token}"

2. Evaluate:
curl -X POST http://localhost:8000/api/assessments/assignments/{assignment-id}/evaluate/ \\
  -H "Authorization: Bearer {faculty-token}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "marks_obtained": 85,
    "feedback": "Great work!"
  }'

============================================================================
"""
