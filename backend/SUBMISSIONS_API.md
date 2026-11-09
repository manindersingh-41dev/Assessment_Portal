"""
Code Submission and Execution API Documentation.

Complete reference for all code submission, execution, and result endpoints
for the Geeta University Coding Assessment Portal.

For the shared browser-WASM and desktop-GCC client execution API, see
`CLIENT_EXECUTION_API.md`.
"""

# ============================================================================
# CODE SUBMISSION & EXECUTION API DOCUMENTATION
# ============================================================================

"""
BASE URL: http://localhost:8000/api/submissions/

All endpoints require authentication.
Authentication: JWT token in Authorization header
    Authorization: Bearer <access_token>

============================================================================
1. CODE SUBMISSION
============================================================================

### Submit Code for a Question
POST /api/submissions/submit/{assignment_id}/

Submit C source code for evaluation.

Path Parameters:
- assignment_id: UUID of AssessmentAssignment

Request Body:
{
    "question_id": "uuid-of-assessment-question",
    "source_code": "#include <stdio.h>\nint main() { ... }"
}

Response (201 Created):
{
    "message": "Submission received and queued for execution",
    "submission_id": "uuid",
    "status": "pending"
}

Validation:
- Question must exist in assessment
- Student must have assignment (status STARTED or SUBMITTED)
- Deadline must not have passed
- Source code required (non-empty)
- Source code must not contain dangerous patterns
- Source code must include necessary headers
- Max 100KB size

Status Codes:
- 201: Submission created successfully
- 400: Validation error (invalid code, deadline passed, etc.)
- 403: Not authorized (student doesn't own assignment)
- 500: Internal server error

Dangerous Patterns Blocked:
- system()
- fork()
- exec()
- popen()
- asm()
- dlopen()
- __builtin_

Example:
curl -X POST http://localhost:8000/api/submissions/submit/assignment-uuid/ \\
  -H "Authorization: Bearer {token}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "question_id": "question-uuid",
    "source_code": "#include <stdio.h>\\nint main() {\\n  printf(\\\"Hello World\\\");\\n  return 0;\\n}"
  }'

---

============================================================================
2. SUBMISSION STATUS & RESULTS
============================================================================

### Get Submission Status
GET /api/submissions/status/{submission_id}/

Get current status of a submission during execution.

Path Parameters:
- submission_id: UUID of CodeSubmission

Response (200 OK):
{
    "id": "uuid",
    "status": "executing",  # pending, compiling, compiled, executing, completed, failed
    "verdict": "not_evaluated",
    "marks_obtained": null,
    "total_test_cases": 5,
    "passed_test_cases": 0,
    "failed_test_cases": 0,
    "compilation_time_ms": null,
    "execution_time_ms": null,
    "max_memory_used_mb": null,
    "execution_started_at": "2024-11-06T10:15:00Z",
    "execution_completed_at": null
}

Status Progression:
1. PENDING - Initial state, waiting to be processed
2. COMPILING - Code is being compiled
3. COMPILED - Compilation successful, about to run tests
4. EXECUTING - Running test cases
5. COMPLETED - All test cases executed
6. FAILED - Execution encountered error

Verdict Values:
- not_evaluated - Not yet evaluated
- accepted - All test cases passed
- wrong_answer - Output doesn't match expected
- compilation_error - Failed to compile
- runtime_error - Program crashed
- time_limit_exceeded - Program took too long
- memory_limit_exceeded - Program used too much memory
- internal_error - System error during execution

---

### Get Submission Result
GET /api/submissions/result/{submission_id}/

Get detailed result with test case verdicts.

Path Parameters:
- submission_id: UUID of CodeSubmission

Response (200 OK):
{
    "id": "uuid",
    "verdict": "accepted",
    "verdict_display": "Accepted (All test cases passed)",
    "marks_obtained": 10,
    "total_test_cases": 5,
    "passed_test_cases": 5,
    "success_rate": 100.0,
    "compilation_error": null,
    "test_case_verdicts": [
        {
            "test_case_order": 1,
            "is_sample": true,
            "status": "accepted",
            "status_display": "Accepted",
            "marks_obtained": 2,
            "execution_time_ms": 5,
            "memory_used_mb": 1.2,
            "actual_output": "6",
            "error_message": null
        },
        {
            "test_case_order": 2,
            "is_sample": false,  # Hidden test cases show limited info
            "status": "accepted",
            "status_display": "Accepted",
            "marks_obtained": 2,
            "execution_time_ms": 8
        },
        ...
    ]
}

Note:
- Hidden test case details (actual_output, error_message) are NOT shown
- Only sample test case full details are shown
- Students can only view their own submissions

Status Codes:
- 200: Result available
- 400: Submission not yet completed
- 403: Cannot view other students' submissions
- 404: Submission not found

Example:
curl -X GET http://localhost:8000/api/submissions/result/submission-uuid/ \\
  -H "Authorization: Bearer {token}"

---

### Get Execution Log
GET /api/submissions/submissions/{submission_id}/execution_log/

Get detailed execution logs for debugging.

Response (200 OK):
{
    "id": "uuid",
    "compilation_output": "... compiler stdout ...",
    "compilation_stderr": "... compiler errors ...",
    "execution_output": "... execution logs ...",
    "system_info": {
        "test_cases": 5,
        "passed": 5,
        "failed": 0,
        "total_time_ms": 45,
        "max_memory_mb": 2.5
    },
    "created_at": "2024-11-06T10:15:30Z"
}

---

============================================================================
3. SUBMISSION LISTING
============================================================================

### List My Submissions
GET /api/submissions/list/

List all submissions for current student.

Query Parameters:
- page: Page number (default: 1)
- page_size: Results per page (default: 10)

Response (200 OK):
{
    "count": 25,
    "next": "http://localhost:8000/api/submissions/list/?page=2",
    "previous": null,
    "results": [
        {
            "id": "uuid",
            "question_title": "Sum of Numbers",
            "status": "completed",
            "status_display": "Completed",
            "verdict": "accepted",
            "verdict_display": "Accepted (All test cases passed)",
            "marks_obtained": 10,
            "passed_test_cases": 5,
            "total_test_cases": 5,
            "attempt_number": 1,
            "created_at": "2024-11-06T10:15:00Z"
        }
    ]
}

---

### List Submissions by Assignment
GET /api/submissions/by_assignment/{assignment_id}/

List all submissions for a specific assignment.

Faculty can view all student submissions for their assessments.
Students can only view their own submissions.

Query Parameters:
- page: Page number (default: 1)
- page_size: Results per page (default: 10)

Response: Same as list endpoint

---

### Get Submission Statistics
GET /api/submissions/stats/

Get statistics about student's submissions.

Response (200 OK):
{
    "total_submissions": 25,
    "pending_submissions": 2,
    "completed_submissions": 23,
    "accepted_submissions": 18,
    "average_marks": 8.2,
    "success_rate": 72.0,
    "compilation_errors": 3,
    "runtime_errors": 2
}

---

============================================================================
4. SUBMISSION STRUCTURE & EXECUTION FLOW
============================================================================

### Complete Submission Workflow

1. **Student Submits Code**
POST /api/submissions/submit/{assignment_id}/
→ Response: submission_id, status=pending

2. **Poll Status** (while status != completed)
GET /api/submissions/status/{submission_id}/
→ Shows: pending → compiling → compiled → executing → completed

3. **Get Results** (when status == completed)
GET /api/submissions/result/{submission_id}/
→ Shows: verdict, marks, test case results

---

### Source Code Validation

Before submission, code is validated for:
- Not empty (required)
- Not too large (max 100KB)
- Contains #include statements
- No dangerous patterns (system, fork, exec, etc.)

Example Valid Code:
```c
#include <stdio.h>

int sum(int a, int b) {
    return a + b;
}

int main() {
    int x, y;
    scanf("%d %d", &x, &y);
    printf("%d\n", sum(x, y));
    return 0;
}
```

---

### Execution Environment

Each submission runs in isolated Docker container:
- No network access
- CPU limit: 1 core
- Memory limit: 256MB
- Execution timeout: 10 seconds per test case
- Non-root user execution
- Compiled with GCC (C11 standard)

---

### Test Case Evaluation

For each test case:
1. Compile source code (once)
2. Provide input via stdin
3. Capture output on stdout
4. Compare with expected output
5. Record: status, marks, time, memory

Comparison:
- Whitespace normalized (multiple spaces become one)
- Newlines normalized (CRLF → LF)
- Leading/trailing whitespace stripped

Results Stored:
- Test order number
- Sample/hidden flag
- Pass/fail status
- Marks obtained
- Execution time (ms)
- Memory used (MB)
- Actual output (sample only)
- Error message (if any)

---

### Verdict Determination

| Condition | Verdict |
|-----------|---------|
| Compilation fails | Compilation Error |
| All test cases pass | Accepted |
| At least one wrong answer | Wrong Answer |
| Runtime error on test | Runtime Error |
| Exceeds time limit | Time Limit Exceeded |
| Exceeds memory limit | Memory Limit Exceeded |
| System error | Internal Error |

---

============================================================================
5. SUPPORTED C FEATURES
============================================================================

Supported:
- Standard I/O: scanf(), printf()
- Control: if/else, while, for, do-while, switch
- Functions: recursion, multiple functions
- Data types: int, float, char, arrays
- Pointers: basic pointer operations
- Structures: struct definitions and usage
- String operations: basic string handling
- Math: basic arithmetic and math functions

Standard Libraries Available:
- stdio.h (I/O)
- stdlib.h (utilities)
- string.h (string functions)
- math.h (math functions)
- ctype.h (character functions)

Not Supported / Blocked:
- File I/O (open, read, write)
- System calls (system(), exec(), fork())
- Network operations
- Dynamic code execution
- Assembly code (asm)
- Memory manipulation (dlopen)

---

============================================================================
6. SECURITY FEATURES
============================================================================

✓ Docker Isolation
  - Each submission runs in isolated container
  - No access to host system
  - No network access
  - Resource limits enforced

✓ Code Validation
  - Dangerous patterns detected before execution
  - Size limits enforced
  - Syntax requirements checked

✓ Hidden Test Cases
  - Never exposed to students
  - Only sample test case details shown
  - Faculty can view full results

✓ Resource Limits
  - CPU: 1 core
  - Memory: 256MB
  - Time: 10 seconds per test case
  - File size: 1MB
  - Processes: 256 max

✓ Non-root Execution
  - Code runs as user 1000:1000
  - No privileged operations possible

✓ Automatic Cleanup
  - Temporary files deleted after execution
  - Old containers cleaned up
  - No data persistence

---

============================================================================
7. ERROR HANDLING
============================================================================

All errors follow standard format:

{
    "error": "Error title",
    "details": "Detailed error message"
}

Or field-specific:

{
    "field_name": ["Error message"]
}

Common Errors:

### 400 Bad Request
- Empty source code
- Source code too large
- Missing includes
- Dangerous patterns detected
- Invalid question_id
- Deadline passed
- Assignment not started

### 403 Forbidden
- Cannot view other students' submissions
- Faculty cannot view non-owned assessments
- Student role required

### 404 Not Found
- Submission not found
- Assignment not found
- Question not found

### 500 Internal Server Error
- Docker execution error
- Unexpected system error

---

============================================================================
8. EXAMPLE WORKFLOWS
============================================================================

### Complete Example: C Sum Program

1. **Assessment Setup**
   - Faculty creates assessment with Question: "Sum of Two Numbers"
   - Sample test: input "3 5", expected output "8"
   - Hidden test: input "100 200", expected output "300"

2. **Student Submits**
```bash
curl -X POST http://localhost:8000/api/submissions/submit/assignment-uuid/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "question_id": "question-uuid",
    "source_code": "#include <stdio.h>\nint main() {\n  int a, b;\n  scanf(\"%d %d\", &a, &b);\n  printf(\"%d\\n\", a + b);\n  return 0;\n}"
  }'
```

Response:
```json
{
  "message": "Submission received and queued for execution",
  "submission_id": "sub-uuid-123",
  "status": "pending"
}
```

3. **Check Status**
```bash
curl http://localhost:8000/api/submissions/status/sub-uuid-123/ \
  -H "Authorization: Bearer {token}"
```

Poll until status = "completed"

4. **Get Results**
```bash
curl http://localhost:8000/api/submissions/result/sub-uuid-123/ \
  -H "Authorization: Bearer {token}"
```

Response:
```json
{
  "id": "sub-uuid-123",
  "verdict": "accepted",
  "marks_obtained": 10,
  "passed_test_cases": 2,
  "total_test_cases": 2,
  "success_rate": 100.0,
  "test_case_verdicts": [
    {
      "test_case_order": 1,
      "is_sample": true,
      "status": "accepted",
      "marks_obtained": 5,
      "execution_time_ms": 3,
      "actual_output": "8"
    },
    {
      "test_case_order": 2,
      "is_sample": false,
      "status": "accepted",
      "marks_obtained": 5,
      "execution_time_ms": 2
    }
  ]
}
```

---

### Example: Wrong Answer

Student submits incorrect implementation:
```c
#include <stdio.h>
int main() {
  int a, b;
  scanf("%d %d", &a, &b);
  printf("%d\n", a - b);  // Wrong: subtraction instead of addition
  return 0;
}
```

Result:
```json
{
  "verdict": "wrong_answer",
  "marks_obtained": 5,
  "passed_test_cases": 1,
  "total_test_cases": 2,
  "success_rate": 50.0,
  "test_case_verdicts": [
    {
      "test_case_order": 1,
      "is_sample": true,
      "status": "wrong_answer",
      "marks_obtained": 0,
      "actual_output": "-2",
      "error_message": null
    },
    {
      "test_case_order": 2,
      "is_sample": false,
      "status": "wrong_answer",
      "marks_obtained": 0
    }
  ]
}
```

---

### Example: Compilation Error

Student submits code with syntax error:
```c
#include <stdio.h>
int main() {
  printf("Hello)  // Missing closing quote
  return 0
}
```

Result:
```json
{
  "verdict": "compilation_error",
  "marks_obtained": 0,
  "total_test_cases": 0,
  "compilation_error": "error: missing terminating \" character [-Werror,-Wformat]\n printf(\"Hello)  ^"
}
```

---

============================================================================
9. IMPORTANT RULES
============================================================================

✓ Asynchronous Execution
  - Submissions queued for background processing
  - Use status endpoint to poll progress
  - Results available after completion

✓ Unique Submissions
  - Each submission gets unique ID
  - Cannot reprocess same submission
  - Multiple submissions create separate records

✓ Student Code Safety
  - Code never touches host system
  - Dangerous patterns blocked at validation
  - Docker provides additional isolation

✓ Result Visibility
  - Students see own submissions only
  - Hidden test details never exposed
  - Faculty can view student submissions

✓ Resubmission
  - Students can resubmit based on assessment policy
  - Each submission tracked separately
  - Best submission used for grading (configurable)

---

============================================================================
10. BACKEND SETUP
============================================================================

### Requirements
- Docker (for code execution)
- Celery (for background tasks)
- Redis (for job queue)
- GCC compiler

### Docker Setup
1. Pull base image: gcc:11-bullseye
2. Verify: docker pull gcc:11-bullseye
3. Test: docker run --rm gcc:11-bullseye gcc --version

### Celery Setup
1. Install: pip install celery redis
2. Configure Redis connection in settings
3. Start Celery: celery -A submissions worker -l info

### Production Setup
- Use separate Docker host for execution
- Configure resource limits
- Enable container cleanup cron job
- Monitor execution queue
- Set up alerting for failures

---

============================================================================
"""
