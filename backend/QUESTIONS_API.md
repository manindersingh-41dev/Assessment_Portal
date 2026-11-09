"""
Question Bank API Documentation.

Complete reference for all question and test case management endpoints
for the Geeta University Coding Assessment Portal.
"""

# ============================================================================
# QUESTION BANK API DOCUMENTATION
# ============================================================================

"""
BASE URL: http://localhost:8000/api/questions/

All endpoints require authentication and faculty role (approved).
Authentication: JWT token in Authorization header
    Authorization: Bearer <access_token>

============================================================================
1. QUESTION MANAGEMENT
============================================================================

### Create Question
POST /api/questions/questions/

Create a new programming question with test cases.

Request Body:
{
    "title": "Sum of Numbers",
    "description": "Given N numbers, find their sum.",
    "input_format": "First line: N (number of integers)\nNext N lines: one integer per line",
    "output_format": "Single line: sum of all numbers",
    "constraints": "1 <= N <= 1000\n1 <= each number <= 10000",
    "sample_input": "3\n1\n2\n3",
    "sample_output": "6",
    "sample_explanation": "1 + 2 + 3 = 6",
    "difficulty": "easy",  # easy, medium, hard
    "topic": "Basic Math",
    "total_marks": 10,
    "time_limit_seconds": 30,
    "memory_limit_mb": 128,
    "test_cases": [
        {
            "input": "3\n1\n2\n3",
            "expected_output": "6",
            "is_sample": true,
            "marks": 5,
            "order": 1
        },
        {
            "input": "5\n1\n2\n3\n4\n5",
            "expected_output": "15",
            "is_sample": false,
            "marks": 5,
            "order": 2
        }
    ]
}

Response (201 Created):
{
    "message": "Question created successfully (DRAFT status)",
    "question": {
        "id": "uuid",
        "title": "Sum of Numbers",
        "description": "Given N numbers, find their sum.",
        "input_format": "...",
        "output_format": "...",
        "constraints": "...",
        "sample_input": "3\n1\n2\n3",
        "sample_output": "6",
        "sample_explanation": "1 + 2 + 3 = 6",
        "difficulty": "easy",
        "difficulty_display": "Easy",
        "topic": "Basic Math",
        "language": "c",
        "total_marks": 10,
        "status": "draft",
        "status_display": "Draft",
        "time_limit_seconds": 30,
        "memory_limit_mb": 128,
        "created_by_name": "John Doe",
        "created_at": "2024-11-06T10:00:00Z",
        "updated_at": "2024-11-06T10:00:00Z",
        "test_cases": [...]
    }
}

Validation:
- Title: Required, non-empty
- Description: Required
- Input/Output formats: Required
- Constraints: Required
- Sample input/output: Required
- Difficulty: easy, medium, or hard
- Total marks: 1-100
- Time limit: 1-3600 seconds
- Memory limit: 1-2048 MB
- Test cases: At least one, with correct total marks
- Sample test cases: At least one must be marked as sample

Status: Created in DRAFT status by default

---

### Get Question Details
GET /api/questions/questions/{id}/

Retrieve complete question details including all test cases.

Response (200 OK):
{
    "id": "uuid",
    "title": "Sum of Numbers",
    "description": "...",
    "input_format": "...",
    "output_format": "...",
    "constraints": "...",
    "sample_input": "...",
    "sample_output": "...",
    "sample_explanation": "...",
    "difficulty": "easy",
    "difficulty_display": "Easy",
    "topic": "Basic Math",
    "language": "c",
    "total_marks": 10,
    "status": "draft",
    "status_display": "Draft",
    "time_limit_seconds": 30,
    "memory_limit_mb": 128,
    "created_by_name": "John Doe",
    "created_at": "2024-11-06T10:00:00Z",
    "updated_at": "2024-11-06T10:00:00Z",
    "test_cases": [
        {
            "id": "uuid",
            "input": "3\n1\n2\n3",
            "expected_output": "6",
            "is_sample": true,
            "marks": 5,
            "order": 1
        },
        ...
    ]
}

Errors:
- 404: Question not found
- 403: You do not have permission (not faculty or not creator)

---

### List Questions
GET /api/questions/questions/

List all questions created by current faculty.

Query Parameters:
- difficulty: Filter by difficulty (easy, medium, hard)
- status: Filter by status (draft, active, archived)
- topic: Filter by topic
- search: Search in title and description
- ordering: Sort by field (-created_at, title, difficulty, total_marks)

Response (200 OK):
{
    "count": 25,
    "next": "http://localhost:8000/api/questions/questions/?page=2",
    "previous": null,
    "results": [
        {
            "id": "uuid",
            "title": "Sum of Numbers",
            "difficulty": "easy",
            "difficulty_display": "Easy",
            "topic": "Basic Math",
            "total_marks": 10,
            "status": "draft",
            "status_display": "Draft",
            "created_by_name": "John Doe",
            "created_at": "2024-11-06T10:00:00Z",
            "test_case_count": 2,
            "sample_test_case_count": 1
        },
        ...
    ]
}

Examples:
- GET /api/questions/questions/?difficulty=easy
- GET /api/questions/questions/?status=active
- GET /api/questions/questions/?topic=Math
- GET /api/questions/questions/?search=sum
- GET /api/questions/questions/?ordering=-created_at

---

### Update Question
PUT /api/questions/questions/{id}/
PATCH /api/questions/questions/{id}/

Update question details (test cases managed separately).

Request Body (example):
{
    "title": "Sum of Numbers - Updated",
    "description": "Updated description...",
    "difficulty": "medium",
    "total_marks": 15
}

Note: Cannot modify test cases here. Use Test Case API.

Response (200 OK):
{
    "message": "Question updated successfully",
    "question": {...}
}

Errors:
- 400: Cannot edit archived questions
- 404: Question not found
- 403: You do not have permission

---

### Delete Question
DELETE /api/questions/questions/{id}/

Delete a question (only DRAFT questions can be deleted).

Response (204 No Content):
(empty response)

Errors:
- 400: Only draft questions can be deleted. Use archive action instead.
- 404: Question not found
- 403: You do not have permission

---

### Publish Question
POST /api/questions/questions/{id}/publish/

Publish a question (change status from DRAFT to ACTIVE).

Validation before publishing:
- Question must have at least one test case
- Question must have at least one sample test case
- Total test case marks must equal question total marks

Response (200 OK):
{
    "message": "Question published successfully",
    "question": {...}
}

Errors:
- 400: Question must have test cases
- 400: Question must have sample test cases
- 400: Test case marks mismatch
- 404: Question not found

---

### Archive Question
POST /api/questions/questions/{id}/archive/

Archive a question (change status to ARCHIVED).

Active questions can still be used in assessments after archiving.

Response (200 OK):
{
    "message": "Question archived successfully",
    "question": {...}
}

---

### Change Question Status
PATCH /api/questions/questions/{id}/change_status/

Change question status directly.

Request Body:
{
    "status": "active"  # draft, active, or archived
}

Valid transitions:
- draft → active, archived
- active → draft, archived
- archived → active

Response (200 OK):
{
    "message": "Question status changed to active",
    "question": {...}
}

---

### Preview Question
POST /api/questions/questions/preview/

Preview question before creating (validation only).

Request Body: (same as create)

Response (200 OK):
{
    "message": "Question validation successful",
    "preview": {...}
}

Errors show validation issues without creating the question.

---

### Get Question Statistics
GET /api/questions/questions/statistics/

Get statistics about all faculty's questions.

Response (200 OK):
{
    "total_questions": 25,
    "by_difficulty": {
        "easy": 10,
        "medium": 10,
        "hard": 5
    },
    "by_status": {
        "draft": 5,
        "active": 15,
        "archived": 5
    },
    "by_topic": {
        "Basic Math": 8,
        "Arrays": 7,
        "Strings": 10
    },
    "average_marks": 12.4
}

---

### Get Test Cases for Question
GET /api/questions/questions/{id}/test_cases/

Get all test cases (sample and hidden) for a question.

Response (200 OK):
{
    "question_id": "uuid",
    "question_title": "Sum of Numbers",
    "test_case_count": 5,
    "sample_count": 1,
    "hidden_count": 4,
    "test_cases": [
        {
            "id": "uuid",
            "input": "3\n1\n2\n3",
            "expected_output": "6",
            "is_sample": true,
            "marks": 5,
            "order": 1
        },
        ...
    ]
}

============================================================================
2. TEST CASE MANAGEMENT
============================================================================

### Create Test Case
POST /api/questions/test-cases/

Add a new test case to an existing question.

Request Body:
{
    "question_id": "uuid",
    "input": "5\n1\n2\n3\n4\n5",
    "expected_output": "15",
    "is_sample": false,
    "marks": 5,
    "order": 3
}

Response (201 Created):
{
    "message": "Test case created successfully",
    "test_case": {
        "id": "uuid",
        "input": "5\n1\n2\n3\n4\n5",
        "expected_output": "15",
        "is_sample": false,
        "marks": 5,
        "order": 3
    }
}

Validation:
- question_id: Must be valid UUID
- Marks: 1-100
- Total marks cannot exceed question total marks
- Input/Output: Must not be empty

Errors:
- 400: Adding these marks would exceed total marks
- 404: Question not found

---

### Update Test Case
PUT /api/questions/test-cases/{id}/
PATCH /api/questions/test-cases/{id}/

Update an existing test case.

Request Body:
{
    "input": "new input",
    "expected_output": "new output",
    "marks": 10
}

Response (200 OK):
{
    "message": "Test case updated successfully",
    "test_case": {...}
}

---

### Delete Test Case
DELETE /api/questions/test-cases/{id}/

Delete a test case.

Validation:
- Cannot delete if only test case remains
- Cannot delete if only sample test case

Response (204 No Content):
(empty response)

Errors:
- 400: Cannot delete the only test case
- 400: Cannot delete the only sample test case
- 403: Cannot delete from active question's last test case

---

============================================================================
3. FACULTY WORKFLOWS
============================================================================

### Complete Question Creation Workflow

1. Create Question (DRAFT):
POST /api/questions/questions/
{
    "title": "...",
    "description": "...",
    "input_format": "...",
    "output_format": "...",
    "constraints": "...",
    "sample_input": "...",
    "sample_output": "...",
    "total_marks": 10,
    "test_cases": [...]
}

2. Verify Creation:
GET /api/questions/questions/{id}/

3. Add More Test Cases (optional):
POST /api/questions/test-cases/
{
    "question_id": "{id}",
    "input": "...",
    "expected_output": "...",
    "marks": 5
}

4. Publish when ready:
POST /api/questions/questions/{id}/publish/

5. Use in Assessment

---

### Search and Filter Workflow

1. Search by title/description:
GET /api/questions/questions/?search=sum

2. Filter by difficulty:
GET /api/questions/questions/?difficulty=easy

3. Filter by status:
GET /api/questions/questions/?status=active

4. Combined filtering:
GET /api/questions/questions/?difficulty=medium&status=active&search=array

---

### Bulk Operations Workflow

1. Get questions:
GET /api/questions/questions/?status=draft

2. For each, publish:
POST /api/questions/questions/{id}/publish/

Or archive:
POST /api/questions/questions/{id}/archive/

============================================================================
4. PERMISSION RULES
============================================================================

Faculty can:
- Create questions
- Edit their own questions (except archived)
- Delete their own DRAFT questions
- Publish their questions
- Archive their questions
- Manage test cases for their questions
- View their own question statistics

Faculty cannot:
- Access other faculty's questions
- Delete ACTIVE or ARCHIVED questions
- Modify test cases of questions from other faculty

Students:
- Cannot access question creation/management endpoints
- Can view ACTIVE questions if included in assessments
- Cannot see HIDDEN test cases

============================================================================
5. ERROR RESPONSES
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

============================================================================
6. IMPORTANT RULES
============================================================================

✓ Hidden Test Cases
  - Never exposed to students through API
  - Only accessible to faculty who created the question
  - Used only during grading

✓ Sample Test Cases
  - Visible to students when question is in assessment
  - Help students understand the problem
  - Must have at least one

✓ Marks Validation
  - Total test case marks must equal question total marks
  - Enforced on question creation and updates
  - Prevents invalid scoring

✓ Question Reusability
  - Same question can be used in multiple assessments
  - Archiving doesn't break previous assessments
  - Questions can be reused across different courses/semesters

✓ Status Workflow
  - DRAFT: Initial status, not available for assessments
  - ACTIVE: Published and available for use in assessments
  - ARCHIVED: No longer used but still accessible in assessments

============================================================================
7. EXAMPLE API CALLS
============================================================================

### Create and Publish a Question

1. Create:
curl -X POST http://localhost:8000/api/questions/questions/ \\
  -H "Authorization: Bearer {token}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "title": "Fibonacci",
    "description": "Find the Nth Fibonacci number",
    "input_format": "Single integer N",
    "output_format": "Nth Fibonacci number",
    "constraints": "1 <= N <= 50",
    "sample_input": "5",
    "sample_output": "5",
    "difficulty": "medium",
    "topic": "Recursion",
    "total_marks": 15,
    "test_cases": [
      {
        "input": "5",
        "expected_output": "5",
        "is_sample": true,
        "marks": 5,
        "order": 1
      },
      {
        "input": "10",
        "expected_output": "55",
        "is_sample": false,
        "marks": 10,
        "order": 2
      }
    ]
  }'

2. Publish:
curl -X POST http://localhost:8000/api/questions/questions/{id}/publish/ \\
  -H "Authorization: Bearer {token}"

---

### Search Questions

curl -X GET "http://localhost:8000/api/questions/questions/?search=fibonacci&difficulty=medium" \\
  -H "Authorization: Bearer {token}"

---

### Add Test Case

curl -X POST http://localhost:8000/api/questions/test-cases/ \\
  -H "Authorization: Bearer {token}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "question_id": "uuid",
    "input": "20",
    "expected_output": "6765",
    "is_sample": false,
    "marks": 10,
    "order": 3
  }'

============================================================================
"""
