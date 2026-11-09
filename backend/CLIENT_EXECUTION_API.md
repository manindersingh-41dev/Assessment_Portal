# Client-Side Execution API Contract

**Status:** Source implementation is in Portal_V2 for case retrieval, pending submission creation, and result reporting. Apply migrations `0006` and `0007` before using these endpoints; no database migration was applied during this work.

**Scope:** A common backend contract for browser WebAssembly and the future Tauri desktop runner. The API must not depend on WASM, Tauri, or a particular compiler implementation.

## 1. Current V2 baseline

- `POST /api/submissions/run/` compiles and runs visible cases through Docker in the Django web process.
- Final submissions are stored by the submission API and evaluated by a Celery task through Docker.
- `AssessmentQuestion.id` is the question identifier used by submissions. It is the assessment-to-question link UUID, not `questions.Question.id`.
- The active submission models are exported by `submissions/models/__init__.py` from the `submissions/models/` package. Several modules import from `.models`. The sibling `submissions/models.py` contains duplicate older model definitions; it must not be used for schema edits unless the app's model loading is deliberately changed.
- `SubmissionService.evaluate_assignment_submissions()` currently selects the highest-scoring completed submission. The agreed result rule for this transition is the latest accepted submission per assessment question, whether it passed or failed.
- `ComparisonService` trims leading/trailing whitespace, normalizes CRLF/CR to LF, and collapses whitespace within each line before comparing output. This remains the compatibility rule unless a separate decision changes it.

## 2. Responsibility boundary

The backend owns authentication, assignment eligibility, test-case membership, expected outputs, output comparison, verdicts, marks, persistence, and student/faculty result APIs.

Each client compiles and runs the source locally. The backend accepts the client's reported compile/run outcome and compares reported standard output with the stored expected output. It cannot prove that the client actually ran the submitted source or enforce the client's reported timeout, exit code, or runtime. These results are suitable for the project's practice/test-style trust model, not tamper-resistant grading.

The client must receive hidden test inputs to execute them. It receives no hidden expected output. A student can inspect the hidden inputs in browser developer tools or the desktop app; they are hidden from the normal interface, not secret from the client owner.

## 3. Runner-neutral metadata

Every client-evaluated submission records:

- `runner_type`: `web_wasm` or `desktop_gcc`.
- `runner_version`: application/runner version.
- `compiler_version`: compiler version text, when available.
- `client_submission_id`: a UUID generated once for a submit action and reused for network retries.

The client type is metadata only. It does not change authorization or scoring rules.

## 4. Retrieve execution cases

**Endpoint:** `GET /api/submissions/execution-cases/?assignment_id={uuid}&question_id={assessment-question-uuid}`

Requires an authenticated student. The student must own the assignment, the assignment must be started and eligible for submission, and the question must belong to that assessment.

Example response:

```json
{
  "assignment_id": "assignment-uuid",
  "question_id": "assessment-question-uuid",
  "time_limit_seconds": 10,
  "test_cases": [
    {
      "id": "test-case-uuid-1",
      "order": 1,
      "is_sample": true,
      "input": "3\n1 2 3\n",
      "expected_output": "6\n"
    },
    {
      "id": "test-case-uuid-2",
      "order": 2,
      "is_sample": false,
      "input": "5\n4 8 2 1 3\n"
    }
  ]
}
```

Rules:

- Return the input for each case so either client can execute it.
- Return `expected_output` only for visible/sample cases. Never return hidden expected output or marks.
- Return a stable test-case UUID; the client submits results against these IDs, not client-provided order values.
- Do not create a `CodeSubmission` for this read request or for a local sample run.
- Apply the existing assignment/deadline eligibility rules and a per-student request limit.
- A pending submission may instead request `?submission_id={submission-uuid}`. The backend returns its saved case snapshot only to the submission owner, so a client can resume after navigating away. The existing status response also exposes `is_stale` and `can_resume_client_evaluation`.

## 5. Create and complete a client evaluation

Client execution is a two-step submission flow. Creating the submission before compiling/running saves the code and establishes server-side order immediately. It also lets the client finish reporting results after the assessment deadline if the submission was created while the assignment was eligible.

### 5.1 Create the submission

**Endpoint:** `POST /api/submissions/client-evaluations/`

Requires an authenticated student. This creates a `pending` submission record and does not enqueue code execution.

Required request fields:

```json
{
  "client_submission_id": "client-generated-uuid",
  "assignment_id": "assignment-uuid",
  "question_id": "assessment-question-uuid",
  "source_code": "#include <stdio.h>\\nint main(void) { ... }",
  "runner_type": "web_wasm",
  "runner_version": "1.0.0",
  "compiler_version": "clang version text"
}
```

The response includes the `submission_id`, `status: "pending"`, and the authorized execution cases in the same format as the GET endpoint above. The server stores a snapshot of the case IDs, inputs, expected outputs, marks, visibility, order, and limits with the pending submission; only visible expected outputs and no marks are returned to the client. A retry with the same `client_submission_id` and identical request returns the existing submission and snapshot; reusing it with different data returns `409 Conflict`.

### 5.2 Report compile and run results

**Endpoint:** `POST /api/submissions/client-evaluations/{submission_id}/results/`

The client submits the results for the saved source snapshot:

```json
{
  "compilation": {
    "status": "success",
    "duration_ms": 42,
    "diagnostics": ""
  },
  "test_results": [
    {
      "test_case_id": "test-case-uuid-1",
      "status": "completed",
      "exit_code": 0,
      "duration_ms": 3,
      "stdout": "6\\n",
      "stderr": ""
    }
  ]
}
```

`compilation.status` is `success` or `error`. A compile error may have an empty `test_results` array; the server records a completed compilation-error submission with zero marks. On successful compilation, results must include each test-case ID exactly once, including hidden cases. Each test result status is `completed`, `runtime_error`, `time_limit_exceeded`, or `memory_limit_exceeded`. Results are accepted only for the owning student's pending client-evaluation submission.

Validation and persistence rules:

- Re-check case membership and submission ownership on the server. The assignment eligibility/deadline is checked when the pending submission is created; result reporting can complete that already-authorized submission after the deadline.
- Enforce the same limits for both clients: source code 100 KB; no more than 250 test cases; combined case input and expected-output snapshot no more than 2 MB; compiler diagnostics no more than 20 KB; each stdout/stderr value no more than 64 KB; combined reported stdout/stderr no more than 1 MB. Validate runner type, status values, unique case IDs, and that every case belongs to the saved submission snapshot.
- Use the existing output comparison service for normal exits. A reported timeout maps to a time-limit verdict; a reported nonzero exit maps to a runtime-error verdict; a reported memory-limit status maps to a memory-limit verdict; otherwise compare stdout with the expected output. Client-reported status and time remain unverified diagnostics.
- Store visible expected/actual output for student feedback. Do not copy hidden expected output into verdict rows or student responses, and never return hidden actual output or detailed hidden errors to students.
- Preserve one result row per case. The current `TestCaseVerdict` stores order and visibility rather than a test-case foreign key; implementation validates UUIDs against the saved server-side snapshot, then persists the corresponding order and visibility.
- Use a database transaction so all verdict rows are either stored or none are.
- Result reporting is idempotent. Repeating the same result payload for a completed submission returns its existing result; sending different results for an already-completed submission returns `409 Conflict`.
- The status API returns the same result shape after completion. If the assignment was automatically submitted while an evaluation was pending, completion recalculates the assignment when all latest submissions have results.
- A newer submission is ordered when its creation request is accepted, not when local execution finishes. A retry of an older `client_submission_id` must not become the latest submission.

## 6. Response and result privacy

Successful response returns the completed submission ID, aggregate verdict, marks, case counts, compilation details, and case results.

- Visible cases may include expected output, actual output, status, and student-safe error details.
- Hidden cases include only case order and `passed`/`failed` status. Do not include hidden inputs, expected/actual outputs, stderr, detailed errors, runtime, memory, or per-case marks in student-facing responses.
- Faculty result access continues through the existing faculty permission rules.
- Existing student result and scorecard APIs should keep their response shapes where possible.

## 7. Idempotency and latest-submission semantics

`client_submission_id` identifies one submit action, not one question or assessment. The server-generated submission creation time determines ordering. For a given `(assignment, AssessmentQuestion)`, the newest submission is authoritative even if it has fewer marks than an earlier submission. Retries with the same client ID do not change ordering. Assessment finalization waits only for the newest submission per question; an older pending evaluation cannot block a newer completed submission. If the newest client submission has no result report, it remains pending and is exposed as incomplete/stale; the server cannot execute it as a fallback without returning to server-side execution.

## 8. Legacy transition

Keep the current Docker-backed `run/` and queued submission flow working while the new endpoints are introduced. The client-result API is additive. Faculty retry cannot send a client-run submission back through Docker; the student must resume or resubmit from a supported client. The setting `SERVER_DOCKER_EXECUTION_ENABLED` defaults to `true` during migration. After the client flow has been integrated and piloted, set it to `false` to reject new Docker runs/retries and fail any queued Docker task that has not started. Do this between assessment windows, after the Docker queue is empty; existing submitted assignments with unfinished server evaluations cannot switch to client execution automatically. The same client-result API remains available to the Tauri client. Celery remains for email/reminder work.

## 9. Backend completion criteria

- Both a simulated `web_wasm` client and a simulated `desktop_gcc` client can use the same endpoints and request schema.
- Unauthorized assignments/questions cannot retrieve test cases or submit results.
- Hidden expected outputs and detailed hidden results are absent from student-facing responses.
- Results, scorecards, faculty pages, and exports use the latest submission per question, not the highest-scoring historical submission.
- Retried requests do not create duplicate submissions or change which submission is latest.
- Existing Docker execution can remain available during migration and can later be disabled without removing email/reminder workers.
