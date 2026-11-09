---

## 🤖 Claude Code Configuration

This project utilizes the  hook to initialize project context automatically when opening the session in Claude Code.

### codebaseSessionStart Hook

This hook ensures the agent is aware of the project structure, current goals, and active work state. To configure this, ensure your  includes the following:



---
"""
Submission Management and Assessment Evaluation API Documentation.

Complete reference for all result viewing, submission tracking, and export endpoints
for the Geeta University Coding Assessment Portal.
"""

# ============================================================================
# SUBMISSION MANAGEMENT & ASSESSMENT EVALUATION API DOCUMENTATION
# ============================================================================

"""
BASE URL: http://localhost:8000/api/results/

All endpoints require authentication.
Authentication: JWT token in Authorization header
    Authorization: Bearer <access_token>

============================================================================
1. STUDENT SUBMISSION HISTORY & RESULTS
============================================================================

### View Submission History
GET /api/results/submissions/history/

Get all code submissions for current student.

Query Parameters:
- page: Page number (default: 1)
- page_size: Results per page (default: 20)
- assignment_id: Optional filter by assignment

Response (200 OK):
{
    "count": 15,
    "next": "http://...",
    "previous": null,
    "results": [
        {
            "submission_id": "uuid",
            "question_title": "Sum of Numbers",
            "question_order": 1,
            "status": "completed",
            "verdict": "accepted",
            "marks_obtained": 10,
            "total_test_cases": 4,
            "passed_test_cases": 4,
            "attempt_number": 1,
            "created_at": "2024-11-06T10:15:00Z"
        },
        ...
    ]
}

Only shows submissions for student's own assignments.

---

### View Assessment Results
GET /api/results/submissions/results/

Get all assessment results for current student.

Query Parameters:
- page: Page number (default: 1)
- page_size: Results per page (default: 20)

Response (200 OK):
{
    "count": 8,
    "results": [
        {
            "id": "uuid",
            "student_name": "John Doe",
            "student_email": "student@geetauniversity.edu.in",
            "assessment_title": "Python Basics",
            "total_marks_obtained": 85,
            "passing_marks": 60,
            "percentage": 85.0,
            "passed": true,
            "attempted_at": "2024-11-06T11:45:00Z",
            "evaluated_at": "2024-11-06T12:00:00Z",
            "feedback": "Passed 4/5 questions. Score: 85/100"
        }
    ]
}

Only shows results if assessment allows (show_results_to_students=true).

---

### Get Assignment Result Details
GET /api/results/submissions/assignment_result/

Get detailed result breakdown for a specific assignment.

Query Parameters:
- assignment_id: UUID of AssessmentAssignment (required)

Response (200 OK):
{
    "assignment_id": "uuid",
    "student_id": "uuid",
    "student_name": "John Doe",
    "student_email": "student@geetauniversity.edu.in",
    "assessment_id": "uuid",
    "assessment_title": "Python Basics",
    "total_marks_obtained": 85,
    "total_marks": 100,
    "percentage": 85.0,
    "passed": true,
    "attempted_questions": 4,
    "total_questions": 5,
    "question_results": [
        {
            "question_id": "uuid",
            "question_title": "Sum of Numbers",
            "question_order": 1,
            "marks_obtained": 10,
            "total_marks": 10,
            "verdict": "accepted",
            "percentage": 100.0
        },
        {
            "question_id": "uuid",
            "question_title": "Array Processing",
            "question_order": 2,
            "marks_obtained": 7,
            "total_marks": 10,
            "verdict": "wrong_answer",
            "percentage": 70.0
        }
    ],
    "evaluated_at": "2024-11-06T12:00:00Z"
}

Shows:
- Overall marks and percentage
- Pass/fail status
- Question-wise breakdown
- Verdict for each question

Only accessible if:
- Student owns the assignment
- Results are released by faculty

---

### View Question Submissions
GET /api/results/submissions/question_submissions/

Get all submissions for a specific question in an assignment.

Query Parameters:
- assignment_id: UUID (required)
- question_id: UUID (required)

Response (200 OK):
{
    "results": [
        {
            "id": "uuid",
            "question_title": "Sum of Numbers",
            "question_order": 1,
            "status": "completed",
            "status_display": "Completed",
            "verdict": "accepted",
            "verdict_display": "Accepted (All test cases passed)",
            "marks_obtained": 10,
            "total_test_cases": 4,
            "passed_test_cases": 4,
            "attempt_number": 1,
            "created_at": "2024-11-06T10:15:00Z"
        }
    ]
}

Shows all attempts for a specific question in order.

---

============================================================================
2. FACULTY SUBMISSION VIEWING
============================================================================

### Assessment Submission Overview
GET /api/results/faculty/assessment_overview/

Get overview of all submissions for an assessment.

Query Parameters:
- assessment_id: UUID (required)
- page: Page number (default: 1)
- page_size: Results per page (default: 20)

Response (200 OK):
{
    "count": 50,
    "results": [
        {
            "submission_id": "uuid",
            "student_name": "John Doe",
            "student_email": "student@geetauniversity.edu.in",
            "question_title": "Sum of Numbers",
            "status": "completed",
            "verdict": "accepted",
            "marks_obtained": 10,
            "total_test_cases": 4,
            "passed_test_cases": 4,
            "attempt_number": 1,
            "created_at": "2024-11-06T10:15:00Z"
        }
    ]
}

Shows all submissions across all students.

Permission: Faculty who created the assessment only.

---

### Get Student's Submissions for Assessment
GET /api/results/faculty/student_submissions/

Get all submissions from a specific student for an assessment.

Query Parameters:
- assessment_id: UUID (required)
- student_id: UUID (required)

Response (200 OK):
Returns list of submissions ordered by creation time.

Permission: Faculty who created the assessment only.

---

### View Submission Details
GET /api/results/faculty/submission_details/

Get complete submission details including source code and test case results.

Query Parameters:
- submission_id: UUID (required)

Response (200 OK):
{
    "submission": {
        "id": "uuid",
        "question_title": "Sum of Numbers",
        "student_name": "John Doe",
        "source_code": "#include <stdio.h>\nint main() { ... }",
        "status": "completed",
        "status_display": "Completed",
        "verdict": "accepted",
        "verdict_display": "Accepted (All test cases passed)",
        "marks_obtained": 10,
        "compilation_error": null,
        "created_at": "2024-11-06T10:15:00Z"
    },
    "test_case_verdicts": [
        {
            "test_case_order": 1,
            "is_sample": true,
            "status": "accepted",
            "marks_obtained": 2,
            "execution_time_ms": 5,
            "memory_used_mb": 1.2,
            "actual_output": "3",
            "error_message": null
        },
        {
            "test_case_order": 2,
            "is_sample": true,
            "status": "accepted",
            "marks_obtained": 2,
            "execution_time_ms": 8,
            "memory_used_mb": 1.5,
            "actual_output": "10",
            "error_message": null
        }
    ]
}

Shows:
- Complete source code
- Compilation errors (if any)
- All test case verdicts (including hidden)
- Marks per test case
- Execution metrics

Permission: Faculty who created the assessment only.

---

### Assessment Statistics
GET /api/results/faculty/assessment_statistics/

Get statistics for an assessment.

Query Parameters:
- assessment_id: UUID (required)

Response (200 OK):
{
    "assessment_id": "uuid",
    "assessment_title": "Python Basics",
    "total_students": 50,
    "evaluated": 48,
    "pending": 2,
    "passed": 35,
    "failed": 13,
    "pass_rate": 70.0,
    "average_percentage": 72.5,
    "average_marks": 72.5,
    "question_statistics": {
        "uuid-q1": {
            "title": "Sum of Numbers",
            "order": 1,
            "marks": 10,
            "statistics": {
                "total_submissions": 48,
                "accepted": 42,
                "wrong_answer": 6,
                "compilation_error": 0,
                "runtime_error": 0,
                "average_marks": 8.5,
                "acceptance_rate": 87.5
            }
        }
    ]
}

Shows:
- Overall pass rate
- Average scores
- Question-wise statistics
- Verdict distribution

Permission: Faculty who created the assessment only.

---

### Evaluate Assessment
POST /api/results/faculty/evaluate_assessment/

Evaluate all pending submissions and calculate final results.

Query Parameters:
- assessment_id: UUID (required)

Response (200 OK):
{
    "message": "Assessment evaluated successfully",
    "summary": {
        "assessment_id": "uuid",
        "assessment_title": "Python Basics",
        "total_students": 50,
        "passed": 35,
        "failed": 15,
        "pass_rate": 70.0,
        "results": [...]
    }
}

This endpoint:
1. Gets all submitted assignments
2. Calculates best submission per student
3. Computes marks per question
4. Determines pass/fail
5. Creates AssessmentResult records
6. Updates AssessmentAssignment status

Permission: Faculty who created the assessment only.

---

### Export Results as CSV
GET /api/results/faculty/export_csv/

Export assessment results as CSV file.

Query Parameters:
- assessment_id: UUID (required)

Response (200 OK):
Content-Type: text/csv
Content-Disposition: attachment

CSV Headers:
Student Name, Student Email, Total Marks, Passing Marks, Percentage, Status, Q1 (10), Q2 (10), ...

Example:
```
Student Name,Student Email,Total Marks,Passing Marks,Percentage,Status,Q1 (10),Q2 (10),Q3 (10)
John Doe,john@example.com,85,60,85.0,Passed,10,10,7
Jane Smith,jane@example.com,60,60,60.0,Passed,10,8,5
```

Permission: Faculty who created the assessment only.

---

### Get Student-wise Results
GET /api/results/faculty/student_wise_results/

Get all students' results for an assessment.

Query Parameters:
- assessment_id: UUID (required)
- page: Page number (default: 1)
- page_size: Results per page (default: 20)

Response (200 OK):
Sorted by percentage (highest first).

Shows:
- Student name and email
- Assessment title
- Total marks obtained
- Passing marks
- Percentage
- Pass/fail status
- Attempt and evaluated timestamps
- Feedback

Permission: Faculty who created the assessment only.

---

============================================================================
3. MARKS CALCULATION EXAMPLES
============================================================================

### Example: Test Case Weightage Calculation

Question: Sum of Numbers (10 marks)

Test Cases:
- Test 1: 2 marks
- Test 2: 2 marks
- Test 3: 3 marks
- Test 4: 3 marks

Student passes tests 1, 2, 3:
Marks = 2 + 2 + 3 = 7 marks

Result: 7/10 (70%)

---

### Example: Multi-Question Assessment

Assessment: Python Basics (100 marks)

Question 1: Sum (10 marks)
- Student: 7 marks

Question 2: Arrays (20 marks)
- Student: 20 marks

Question 3: Strings (20 marks)
- Student: 15 marks

Question 4: Sorting (25 marks)
- Student: 0 marks (compilation error)

Question 5: Recursion (25 marks)
- Student: 23 marks

Total: 7 + 20 + 15 + 0 + 23 = 65 marks
Percentage: 65/100 = 65%
Status: PASSED (65 >= 60 passing marks)

---

### Example: Best Submission Selection

Student submits same question 3 times:

Attempt 1: 5 marks (date: 10:00)
Attempt 2: 8 marks (date: 10:15)
Attempt 3: 5 marks (date: 10:30)

Best submission: Attempt 2 (8 marks)
Final marks: 8

---

============================================================================
4. RESULT VISIBILITY & ACCESS CONTROL
============================================================================

Student Visibility:
- Can only view own submissions
- Can only view own assessment results
- Results visible only if faculty allows (show_results_to_students=true)
- Hidden test case details never shown
- Only own assignments/questions visible

Faculty Visibility:
- Can view all submissions for their assessments
- Can view source code
- Can view full test case results (including hidden)
- Can view compilation errors
- Can download CSV exports
- Cannot access other faculty's assessments

Hidden Information Protection:
- Hidden test case input NEVER shown
- Hidden test case expected output NEVER shown
- Hidden test case verdicts shown only to faculty
- Student sees only marks and verdict status

---

============================================================================
5. API WORKFLOW EXAMPLES
============================================================================

### Student: View Assessment Results

1. Get results list:
GET /api/results/submissions/results/
→ Returns all assessments with results

2. Click on specific result:
GET /api/results/submissions/assignment_result/?assignment_id=xyz
→ Returns detailed breakdown per question

3. View submission for question:
GET /api/results/submissions/question_submissions/?assignment_id=xyz&question_id=abc
→ Returns all attempts for this question

---

### Faculty: Review Assessment

1. Get submission overview:
GET /api/results/faculty/assessment_overview/?assessment_id=uuid
→ Lists all submissions from all students

2. View specific submission:
GET /api/results/faculty/submission_details/?submission_id=uuid
→ Shows source code and all test results

3. View student's all submissions:
GET /api/results/faculty/student_submissions/?assessment_id=uuid&student_id=uuid
→ Shows all attempts

4. Get statistics:
GET /api/results/faculty/assessment_statistics/?assessment_id=uuid
→ Shows pass rate, averages, question statistics

5. Export results:
GET /api/results/faculty/export_csv/?assessment_id=uuid
→ Downloads CSV with all results

---

### Faculty: Grade Assessment

1. Evaluate all submissions:
POST /api/results/faculty/evaluate_assessment/?assessment_id=uuid
→ Calculates results for all students
→ Creates AssessmentResult records
→ Updates assignment status

2. View results:
GET /api/results/faculty/student_wise_results/?assessment_id=uuid
→ Shows all students' final results

3. Export for records:
GET /api/results/faculty/export_csv/?assessment_id=uuid
→ Download CSV for documentation

---

============================================================================
6. DATA AGGREGATION & CALCULATIONS
============================================================================

### Submission Aggregation

get_student_submissions(student_id)
- Returns: All submissions for student
- Ordered: By creation time
- Includes: Status, verdict, marks, attempt number

get_assessment_submissions(assessment_id)
- Returns: All submissions for assessment
- Includes: Student name, question, status, marks
- Ordered: By creation time

get_question_submissions(question_id, assessment_id)
- Returns: Submissions for specific question
- Ordered: By marks (highest first)
- Includes: Student, verdict, marks

---

### Marks Calculation

calculate_marks_for_submission(submission)
- Input: CodeSubmission
- Process: Sum marks from passed test cases
- Output: (total_marks, verdict)

get_best_submission(assignment, question)
- Input: Assignment + Question
- Process: Find highest marks, earliest if tied
- Output: Best CodeSubmission or None

calculate_question_marks(assignment, question)
- Input: Assignment + Question
- Process: Get best submission, calculate marks
- Output: (marks_obtained, total_marks, verdict)

calculate_assignment_results(assignment)
- Input: AssessmentAssignment
- Process: Calculate all questions, aggregate
- Output: Complete results dict

---

### Assessment Evaluation

evaluate_assessment(assessment)
- Finds: All submitted assignments
- For each: Calculate results
- Updates: Assignment marks, status
- Creates: AssessmentResult records
- Returns: Evaluation summary

get_assessment_statistics(assessment)
- Aggregates: All results
- Calculates: Pass rate, averages
- Question-wise: Acceptance rate, average marks
- Returns: Comprehensive statistics

---

============================================================================
7. CSV EXPORT FORMAT
============================================================================

Columns:
1. Student Name
2. Student Email
3. Total Marks
4. Passing Marks
5. Percentage
6. Status (Passed/Failed)
7. Q1 (marks) - for each question
8. Q2 (marks)
... and so on

Example with 3 questions:
```
Student Name,Student Email,Total Marks,Passing Marks,Percentage,Status,Q1 (10),Q2 (20),Q3 (15)
John Doe,john@geetauniversity.edu.in,35,45,58.33,Failed,10,15,10
Jane Smith,jane@geetauniversity.edu.in,45,45,75.0,Passed,10,20,15
Bob Johnson,bob@geetauniversity.edu.in,20,45,33.33,Failed,0,15,5
```

Usage:
- Import to Excel/Sheets for further analysis
- Store in records for documentation
- Generate grade reports
- Identify weak areas by question

---

============================================================================
8. ERROR SCENARIOS
============================================================================

### 400 Bad Request
- Missing required query parameters
- Invalid UUID format
- Invalid assignment_id or assessment_id

### 403 Forbidden
- Student viewing other student's results
- Faculty viewing other faculty's assessment
- Results not released (show_results_to_students=false)
- Faculty evaluation not authorized

### 404 Not Found
- Submission not found
- Assignment not found
- Assessment not found
- Student not found

### 500 Internal Server Error
- Calculation errors
- Database errors
- File export errors

---

============================================================================
9. IMPORTANT RULES
============================================================================

✓ Best Submission Selection
  - Used for final grading
  - Selected by: highest marks, then earliest
  - Applied once per question per student

✓ Marks Calculation
  - Sum of passed test case marks
  - Never exceeds question marks
  - Rounded to nearest integer

✓ Result Visibility
  - Controlled by faculty (show_results_to_students flag)
  - Students can only view own results
  - Hidden test details never exposed

✓ Export Data
  - All data in CSV format
  - Question marks in headers
  - Student name and email included
  - Pass/fail status clearly indicated

✓ Access Control
  - Students: Own submissions/results only
  - Faculty: Own assessment submissions only
  - Strict permission checks enforced
  - No cross-faculty access

---

============================================================================
"""
