import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowLeft,
  Check,
  CheckCircle2,
  Clock3,
  FileText,
  Maximize,
  Minimize,
  Play,
  Send,
  ShieldAlert,
} from 'lucide-react';
import { Button } from '../../components/Button';
import { Alert, Badge } from '../../components/Common';
import { Modal } from '../../components/Modal';
import CodeEditor from '../../components/CodeEditor';
import { useAuthStore } from '../../store/authStore';
import { useNotificationStore } from '../../store/notificationStore';
import api from '../../api/client';
import { config } from '../../constants/config';
import { createWasmRunner, RUNNER_TYPE, WASM_COMPILER_VERSION, WASM_RUNNER_VERSION } from '../../runner';

const endpoints = config.api.endpoints;
const DEFAULT_CODE = '#include <stdio.h>\n\nint main(void) {\n    // Write your solution here\n    return 0;\n}\n';
const FINAL_STATES = new Set(['completed', 'failed']);

const asList = (data) => {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  return [];
};

const unwrapAssessment = (data) => data?.assessment || data;

const formatTime = (seconds) => {
  const safeSeconds = Math.max(0, Number(seconds) || 0);
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  const remainder = safeSeconds % 60;
  return hours
    ? `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(remainder).padStart(2, '0')}`
    : `${String(minutes).padStart(2, '0')}:${String(remainder).padStart(2, '0')}`;
};

const getErrorMessage = (error, fallback) => {
  const data = error?.response?.data;
  if (typeof data?.detail === 'string') return data.detail;
  if (typeof data?.error === 'string') return data.error;
  if (data && typeof data === 'object') {
    const message = Object.values(data).flat(Infinity).find((value) => typeof value === 'string');
    if (message) return message;
  }
  return error?.message || fallback;
};

const getQuestionLinks = (assessment) => {
  const links = assessment?.questions || assessment?.assessment_questions || [];
  return links.map((link, index) => {
    const details = link.question_details || (typeof link.question === 'object' ? link.question : {});
    return {
      id: link.id,
      sourceQuestionId: typeof link.question === 'object' ? link.question.id : link.question,
      order: link.order || index + 1,
      marks: link.marks || 0,
      title: details.title || link.question_title || link.title || `Question ${index + 1}`,
      description: details.description || link.question_description || link.description || '',
      inputFormat: details.input_format || link.input_format || '',
      outputFormat: details.output_format || link.output_format || '',
      constraints: details.constraints || link.constraints || '',
      sampleInput: details.sample_input || link.sample_input || '',
      sampleOutput: details.sample_output || link.sample_output || '',
      difficulty: details.difficulty || link.question_difficulty || link.difficulty || 'medium',
      language: details.language || link.language || 'c',
    };
  }).filter((question) => question.id);
};

const effectiveDeadline = (assessment, assignment) => {
  const deadlines = [];
  if (assessment.is_timed !== false) {
    deadlines.push(new Date(assessment.end_time).getTime());
    deadlines.push(
      new Date(assignment.started_at).getTime() + Number(assessment.duration_minutes || 0) * 60_000,
    );
  }
  if (assignment.due_at) deadlines.push(new Date(assignment.due_at).getTime());
  return deadlines.length ? Math.min(...deadlines) : Infinity;
};

const localDraftStorageKey = (assignmentId) => `assessment-drafts:${assignmentId}`;
const pendingClientRequestsStorageKey = (assignmentId) => `assessment-client-requests:${assignmentId}`;

const createClientSubmissionId = () => {
  if (window.crypto?.randomUUID) return window.crypto.randomUUID();
  if (!window.crypto?.getRandomValues) {
    throw new Error('This browser cannot create a secure submission ID. Please use a current browser over HTTPS.');
  }

  const bytes = window.crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
};

const readPendingClientRequests = (assignmentId) => {
  try {
    const value = JSON.parse(window.localStorage.getItem(pendingClientRequestsStorageKey(assignmentId)) || '{}');
    return value && typeof value === 'object' ? value : {};
  } catch {
    return {};
  }
};

const savePendingClientRequest = (assignmentId, questionId, request) => {
  try {
    const requests = readPendingClientRequests(assignmentId);
    requests[questionId] = request;
    window.localStorage.setItem(pendingClientRequestsStorageKey(assignmentId), JSON.stringify(requests));
  } catch {
    // The server remains the source of truth once a pending evaluation is created.
  }
};

const clearPendingClientRequest = (assignmentId, questionId) => {
  try {
    const requests = readPendingClientRequests(assignmentId);
    delete requests[questionId];
    if (Object.keys(requests).length) {
      window.localStorage.setItem(pendingClientRequestsStorageKey(assignmentId), JSON.stringify(requests));
    } else {
      window.localStorage.removeItem(pendingClientRequestsStorageKey(assignmentId));
    }
  } catch {
    // A stale idempotency key is harmless after the server has returned a submission ID.
  }
};

const normalizeOutput = (value) => String(value ?? '')
  .trim()
  .replace(/\r\n/g, '\n')
  .replace(/\r/g, '\n')
  .split('\n')
  .map((line) => line.split(/\s+/).filter(Boolean).join(' '))
  .join('\n');

const outputsMatch = (actual, expected) => normalizeOutput(actual) === normalizeOutput(expected);

const supportsWasmRunner = () => typeof Worker !== 'undefined'
  && typeof WebAssembly !== 'undefined'
  && typeof WebAssembly.compile === 'function';

const readLocalDrafts = (assignmentId) => {
  try {
    const value = JSON.parse(window.localStorage.getItem(localDraftStorageKey(assignmentId)) || '{}');
    return value && typeof value === 'object' ? value : {};
  } catch {
    return {};
  }
};

const writeLocalDrafts = (assignmentId, value) => {
  try {
    window.localStorage.setItem(localDraftStorageKey(assignmentId), JSON.stringify(value));
  } catch {
    // Browser storage can be unavailable or full; the server draft is still saved.
  }
};

const formatVerdict = (status) => {
  if (!status) return 'Waiting';
  return status.replaceAll('_', ' ');
};

const AssessmentAttemptPage = () => {
  const [assessment, setAssessment] = useState(null);
  const [assignment, setAssignment] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [codes, setCodes] = useState({});
  const [deadlineAt, setDeadlineAt] = useState(null);
  const [remainingSeconds, setRemainingSeconds] = useState(0);
  const [runResults, setRunResults] = useState({});
  const [runProgressByQuestion, setRunProgressByQuestion] = useState({});
  const [submissionIds, setSubmissionIds] = useState({});
  const [submissionStatuses, setSubmissionStatuses] = useState({});
  const [submissionErrors, setSubmissionErrors] = useState({});
  const [submissionStatusErrors, setSubmissionStatusErrors] = useState({});
  const [draftSaveStatus, setDraftSaveStatus] = useState('saved');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [running, setRunning] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submittingQuestionIds, setSubmittingQuestionIds] = useState(() => new Set());
  const [finalized, setFinalized] = useState(false);
  const [polling, setPolling] = useState(false);
  const [integrityWarnings, setIntegrityWarnings] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [resultsHeightPercent, setResultsHeightPercent] = useState(36);
  const [resultsHeightPx, setResultsHeightPx] = useState(260);
  const [resizingResults, setResizingResults] = useState(false);
  const [showSubmitConfirm, setShowSubmitConfirm] = useState(false);
  const [showExitConfirm, setShowExitConfirm] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  const { id } = useParams();
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const addNotification = useNotificationStore((state) => state.addNotification);
  const codeRef = useRef({});
  const submissionIdsRef = useRef({});
  const submissionStatusesRef = useRef({});
  const submissionStatusErrorsRef = useRef({});
  const draftSaveTimersRef = useRef(new Map());
  const draftSaveQueuesRef = useRef(new Map());
  const questionSubmitLocksRef = useRef(new Set());
  const pollingInFlightRef = useRef(false);
  const submitLockRef = useRef(false);
  const autoSubmitTriggeredRef = useRef(false);
  const runnerRef = useRef(null);
  const runnerQueueRef = useRef(Promise.resolve());
  const runnerGenerationRef = useRef(0);
  const attemptRootRef = useRef(null);
  const workspacePanelsRef = useRef(null);

  useEffect(() => {
    runnerGenerationRef.current += 1;
    return () => {
      runnerGenerationRef.current += 1;
      runnerRef.current?.dispose();
      runnerRef.current = null;
    };
  }, [id]);

  useEffect(() => {
    if (!resizingResults) return undefined;

    const resizeResults = (event) => {
      const bounds = workspacePanelsRef.current?.getBoundingClientRect();
      if (!bounds || bounds.height <= 0) return;
      const nextHeight = bounds.bottom - event.clientY;
      const clampedHeight = Math.min(bounds.height * 0.75, Math.max(bounds.height * 0.18, nextHeight));
      setResultsHeightPx(clampedHeight);
      setResultsHeightPercent((clampedHeight / bounds.height) * 100);
    };
    const stopResizing = () => setResizingResults(false);

    window.addEventListener('pointermove', resizeResults);
    window.addEventListener('pointerup', stopResizing);
    window.addEventListener('pointercancel', stopResizing);
    return () => {
      window.removeEventListener('pointermove', resizeResults);
      window.removeEventListener('pointerup', stopResizing);
      window.removeEventListener('pointercancel', stopResizing);
    };
  }, [resizingResults]);

  const currentQuestion = questions[currentQuestionIndex] || null;
  const currentCode = currentQuestion ? (codes[currentQuestion.id] ?? DEFAULT_CODE) : DEFAULT_CODE;
  const currentSubmission = currentQuestion ? submissionStatuses[currentQuestion.id] : null;
  const currentSubmissionPending = Boolean(currentSubmission && !FINAL_STATES.has(currentSubmission.status));
  const currentQuestionSubmitting = Boolean(currentQuestion && submittingQuestionIds.has(currentQuestion.id));
  const canEdit = !finalized && (assessment?.is_timed === false || remainingSeconds > 0);
  const questionStatuses = useMemo(() => questions.map((question) => submissionStatuses[question.id]), [questions, submissionStatuses]);
  const completedSubmissions = questionStatuses.filter((status) => FINAL_STATES.has(status?.status)).length;
  const questionsNeedingWork = questions.filter((question) => {
    const result = submissionStatuses[question.id];
    return FINAL_STATES.has(result?.status) && result?.verdict !== 'accepted';
  }).length;
  const allQuestionsSubmitted = questions.length > 0 && questions.every((question) => Boolean(submissionIds[question.id]));
  const allQuestionSubmissionsSettled = allQuestionsSubmitted && questions.every((question) => FINAL_STATES.has(submissionStatuses[question.id]?.status));

  const updateQuestionSubmissionStatus = useCallback((questionId, nextStatus) => {
    const updated = { ...submissionStatusesRef.current, [questionId]: nextStatus };
    submissionStatusesRef.current = updated;
    setSubmissionStatuses(updated);
  }, []);

  const updateSubmissionStatusError = useCallback((questionId, message) => {
    const currentMessage = submissionStatusErrorsRef.current[questionId];
    if (message ? currentMessage === message : !currentMessage) return;

    const updated = { ...submissionStatusErrorsRef.current };
    if (message) updated[questionId] = message;
    else delete updated[questionId];
    submissionStatusErrorsRef.current = updated;
    setSubmissionStatusErrors(updated);
  }, []);

  const runRunnerTask = useCallback((task) => {
    const generation = runnerGenerationRef.current;
    const execution = runnerQueueRef.current.catch(() => {}).then(() => {
      if (generation !== runnerGenerationRef.current) {
        throw new Error('The browser code run was cancelled because the assessment page changed.');
      }
      return task();
    });
    runnerQueueRef.current = execution.catch(() => {});
    return execution;
  }, []);

  const runClientEvaluation = useCallback(async ({
    questionId,
    submissionId,
    sourceCode,
    executionCases,
  }) => {
    const current = submissionStatusesRef.current[questionId] || {};
    setSubmissionErrors((items) => ({ ...items, [questionId]: '' }));
    updateSubmissionStatusError(questionId, null);
    updateQuestionSubmissionStatus(questionId, {
      ...current,
      id: submissionId,
      status: 'pending',
      client_processing: true,
      client_error: false,
      client_phase: 'Preparing the browser C compiler',
    });

    try {
      if (!supportsWasmRunner()) {
        throw new Error('This browser does not support WebAssembly workers. Please use a current version of Chrome, Edge, Firefox, or Safari.');
      }
      if (!Array.isArray(executionCases?.test_cases) || executionCases.test_cases.length === 0) {
        throw new Error('The server did not provide test cases for this submission. Try resuming the evaluation.');
      }
      if (!runnerRef.current) runnerRef.current = createWasmRunner();

      const execution = await runRunnerTask(() => runnerRef.current.runSubmission({
        sourceCode,
        testCases: executionCases.test_cases,
        timeLimitSeconds: executionCases.time_limit_seconds,
        onStatus: (progress) => {
          const existing = submissionStatusesRef.current[questionId] || {};
          updateQuestionSubmissionStatus(questionId, {
            ...existing,
            id: submissionId,
            status: 'pending',
            client_processing: true,
            client_error: false,
            client_phase: progress.phase,
            client_progress: progress.progress,
          });
        },
      }));

      const response = await api.post(
        endpoints.submissions.clientEvaluationResults(submissionId),
        {
          compilation: execution.compilation,
          test_results: execution.test_results,
        },
        { timeout: 120000 },
      );
      updateQuestionSubmissionStatus(questionId, response.data);
      updateSubmissionStatusError(questionId, null);
      return response.data;
    } catch (evaluationError) {
      const message = getErrorMessage(
        evaluationError,
        'The browser could not finish this evaluation. Your saved submission can be resumed.',
      );
      const existing = submissionStatusesRef.current[questionId] || {};
      updateQuestionSubmissionStatus(questionId, {
        ...existing,
        id: submissionId,
        status: 'pending',
        client_processing: false,
        client_error: true,
        client_phase: '',
      });
      setSubmissionErrors((items) => ({ ...items, [questionId]: message }));
      throw evaluationError;
    }
  }, [runRunnerTask, updateQuestionSubmissionStatus, updateSubmissionStatusError]);

  const resumeClientEvaluation = useCallback(async (questionId, submission) => {
    if (!submission?.id || typeof submission.source_code !== 'string') {
      throw new Error('The saved code for this pending evaluation could not be found. Submit this question again.');
    }

    try {
      const response = await api.get(endpoints.submissions.executionCases, {
        params: { submission_id: submission.id },
      });
      return await runClientEvaluation({
        questionId,
        submissionId: submission.id,
        sourceCode: submission.source_code,
        executionCases: response.data,
      });
    } catch (resumeError) {
      const message = getErrorMessage(resumeError, 'The pending browser evaluation could not be resumed.');
      const existing = submissionStatusesRef.current[questionId] || submission;
      updateQuestionSubmissionStatus(questionId, {
        ...existing,
        id: submission.id,
        status: 'pending',
        client_processing: false,
        client_error: true,
        client_phase: '',
      });
      setSubmissionErrors((items) => ({ ...items, [questionId]: message }));
      throw resumeError;
    }
  }, [runClientEvaluation, updateQuestionSubmissionStatus]);

  const resumePendingClientEvaluations = useCallback(async (statusesByQuestion) => {
    for (const [questionId, submission] of Object.entries(statusesByQuestion)) {
      if (submission.status !== 'pending'
        || !submission.can_resume_client_evaluation
        || typeof submission.source_code !== 'string') continue;
      try {
        await resumeClientEvaluation(questionId, submission);
      } catch {
        // The pending status remains visible with a manual resume action.
      }
    }
  }, [resumeClientEvaluation]);

  const createAndEvaluateClientSubmission = useCallback(async (question, sourceCode) => {
    if (!assignment?.id) throw new Error('The assignment is not ready for submission.');
    if (!supportsWasmRunner()) {
      throw new Error('This browser does not support WebAssembly workers. Please use a current version of Chrome, Edge, Firefox, or Safari.');
    }

    const pendingRequests = readPendingClientRequests(assignment.id);
    const pendingRequest = pendingRequests[question.id];
    const sourceSnapshot = pendingRequest?.source_code ?? sourceCode;
    const clientSubmissionId = pendingRequest?.client_submission_id || createClientSubmissionId();
    savePendingClientRequest(assignment.id, question.id, {
      client_submission_id: clientSubmissionId,
      source_code: sourceSnapshot,
    });

    let response;
    try {
      response = await api.post(endpoints.submissions.clientEvaluations, {
        client_submission_id: clientSubmissionId,
        assignment_id: assignment.id,
        question_id: question.id,
        source_code: sourceSnapshot,
        runner_type: RUNNER_TYPE.WEB_WASM,
        runner_version: WASM_RUNNER_VERSION,
        compiler_version: WASM_COMPILER_VERSION,
      });
    } catch (createError) {
      if (createError.response?.status && createError.response.status < 500 && createError.response.status !== 429) {
        clearPendingClientRequest(assignment.id, question.id);
      }
      throw createError;
    }

    const submissionId = response.data?.submission_id || response.data?.id;
    if (!submissionId) throw new Error(`The server did not return a submission ID for ${question.title}.`);
    clearPendingClientRequest(assignment.id, question.id);
    const ids = { ...submissionIdsRef.current, [question.id]: submissionId };
    submissionIdsRef.current = ids;
    setSubmissionIds(ids);
    updateSubmissionStatusError(question.id, null);
    updateQuestionSubmissionStatus(question.id, {
      id: submissionId,
      question_id: question.id,
      source_code: sourceSnapshot,
      status: response.data.status || 'pending',
      client_processing: false,
      client_error: false,
    });

    if (response.data.status === 'completed' && response.data.result) {
      updateQuestionSubmissionStatus(question.id, response.data.result);
      return response.data.result;
    }

    return runClientEvaluation({
      questionId: question.id,
      submissionId,
      sourceCode: sourceSnapshot,
      executionCases: response.data,
    });
  }, [assignment, runClientEvaluation, updateQuestionSubmissionStatus, updateSubmissionStatusError]);

  const saveDraftNow = useCallback((questionId, sourceCode) => {
    if (!assignment?.id || finalized) return Promise.resolve();

    const priorSave = draftSaveQueuesRef.current.get(questionId) || Promise.resolve();
    const save = priorSave.catch(() => {}).then(async () => {
      await api.put(endpoints.assessments.assignmentDrafts(assignment.id), {
        question_id: questionId,
        source_code: sourceCode,
      });
      if (codeRef.current[questionId] === sourceCode) setDraftSaveStatus('saved');
    }).catch(() => {
      setDraftSaveStatus('error');
    });
    draftSaveQueuesRef.current.set(questionId, save);
    return save.finally(() => {
      if (draftSaveQueuesRef.current.get(questionId) === save) {
        draftSaveQueuesRef.current.delete(questionId);
      }
    });
  }, [assignment, finalized]);

  const scheduleDraftSave = useCallback((questionId, sourceCode) => {
    if (!assignment?.id || finalized) return;
    const priorTimer = draftSaveTimersRef.current.get(questionId);
    if (priorTimer) window.clearTimeout(priorTimer);
    setDraftSaveStatus('saving');
    const timer = window.setTimeout(() => {
      draftSaveTimersRef.current.delete(questionId);
      saveDraftNow(questionId, codeRef.current[questionId] ?? sourceCode);
    }, 700);
    draftSaveTimersRef.current.set(questionId, timer);
  }, [assignment?.id, finalized, saveDraftNow]);

  const flushDrafts = useCallback(async () => {
    draftSaveTimersRef.current.forEach((timer) => window.clearTimeout(timer));
    draftSaveTimersRef.current.clear();
    await Promise.all(Object.entries(codeRef.current).map(([questionId, sourceCode]) => (
      saveDraftNow(questionId, sourceCode)
    )));
  }, [saveDraftNow]);

  useEffect(() => {
    const controller = new AbortController();
    const { signal } = controller;

    const loadAttempt = async () => {
      setLoading(true);
      setError('');
      setDeadlineAt(null);
      setRemainingSeconds(0);
      setDraftSaveStatus('saved');
      setFinalized(false);
      setCurrentQuestionIndex(0);
      autoSubmitTriggeredRef.current = false;
      submissionIdsRef.current = {};
      submissionStatusesRef.current = {};
      submissionStatusErrorsRef.current = {};
      setSubmissionIds({});
      setSubmissionStatuses({});
      setSubmissionErrors({});
      setSubmissionStatusErrors({});
      try {
        const [assessmentResponse, assignmentResponse] = await Promise.all([
          api.get(endpoints.assessments.detail(id), { signal }),
          api.get(endpoints.assessments.myAssignments, { params: { page_size: 100 }, signal }),
        ]);
        if (signal.aborted) return;

        const currentAssessment = unwrapAssessment(assessmentResponse.data);
        const myAssignment = asList(assignmentResponse.data).find(
          (item) => String(item.assessment?.id || item.assessment) === String(currentAssessment.id || id),
        );
        if (!myAssignment) throw new Error('This assessment is not assigned to your account.');

        const questionRows = getQuestionLinks(currentAssessment);
        if (!questionRows.length) throw new Error('This assessment does not have any available questions.');

        let activeAssignment = myAssignment;
        if (activeAssignment.status === 'assigned') {
          const startResponse = await api.post(endpoints.assessments.startAssignment(activeAssignment.id), {}, { signal });
          activeAssignment = startResponse.data?.assignment || startResponse.data;
        }
        if (activeAssignment.status === 'expired') {
          throw new Error('This assessment assignment has expired.');
        }
        if (!['started', 'submitted', 'graded'].includes(activeAssignment.status)) {
          throw new Error('This assessment could not be started. Return to the details page and try again during its scheduled window.');
        }
        if (activeAssignment.status === 'started' && !activeAssignment.started_at) {
          throw new Error('The server did not record the assessment start time. Please reopen the assessment.');
        }

        const codeMap = Object.fromEntries(questionRows.map((question) => [question.id, DEFAULT_CODE]));
        const startDeadline = activeAssignment.started_at
          ? effectiveDeadline(currentAssessment, activeAssignment)
          : NaN;
        if (Number.isFinite(startDeadline)) {
          setDeadlineAt(startDeadline);
          setRemainingSeconds(Math.max(0, Math.ceil((startDeadline - Date.now()) / 1000)));
        }
        setAssessment(currentAssessment);
        setAssignment(activeAssignment);
        setQuestions(questionRows);
        setCodes(codeMap);
        codeRef.current = codeMap;
        if (['submitted', 'graded'].includes(activeAssignment.status)) setFinalized(true);

        const localDrafts = readLocalDrafts(activeAssignment.id);
        const [submissionsResult, draftsResult] = await Promise.allSettled([
          api.get(endpoints.submissions.byAssignment(activeAssignment.id), {
            params: { page_size: 100 },
            signal,
          }),
          api.get(endpoints.assessments.assignmentDrafts(activeAssignment.id), { signal }),
        ]);
        if (signal.aborted) return;

        const submissionRows = submissionsResult.status === 'fulfilled'
          ? asList(submissionsResult.value.data)
          : [];
        const latestByQuestion = {};
        for (const submission of submissionRows) {
          if (submission.question_id && !latestByQuestion[submission.question_id]) {
            latestByQuestion[submission.question_id] = submission;
          }
        }
        const stagedRequests = readPendingClientRequests(activeAssignment.id);
        Object.entries(latestByQuestion).forEach(([questionId, submission]) => {
          if (stagedRequests[questionId]?.source_code === submission.source_code) {
            clearPendingClientRequest(activeAssignment.id, questionId);
          }
        });
        const savedDrafts = draftsResult.status === 'fulfilled'
          ? asList(draftsResult.value.data?.drafts)
          : [];
        const draftByQuestion = Object.fromEntries(savedDrafts.map((draft) => [draft.question_id, draft]));
        const restoredCodeMap = { ...codeMap };
        const localSavedAt = Number(localDrafts.saved_at || 0);
        const localDraftsToSync = [];
        for (const question of questionRows) {
          const candidates = [];
          const submission = latestByQuestion[question.id];
          const savedDraft = draftByQuestion[question.id];
          const localCode = localDrafts.codes?.[question.id];
          if (submission && typeof submission.source_code === 'string') {
            candidates.push({ code: submission.source_code, savedAt: Date.parse(submission.created_at) || 0 });
          }
          if (savedDraft && typeof savedDraft.source_code === 'string') {
            candidates.push({ code: savedDraft.source_code, savedAt: Date.parse(savedDraft.updated_at) || 0 });
          }
          if (typeof localCode === 'string') {
            const localCodeSavedAt = Number(
              localDrafts.saved_at_by_question?.[question.id] || localSavedAt,
            );
            candidates.push({
              code: localCode,
              savedAt: localCodeSavedAt,
            });
            const newestServerCodeAt = Math.max(
              savedDraft ? Date.parse(savedDraft.updated_at) || 0 : 0,
              submission ? Date.parse(submission.created_at) || 0 : 0,
            );
            if (activeAssignment.status === 'started' && localCodeSavedAt > newestServerCodeAt) {
              localDraftsToSync.push({ question_id: question.id, source_code: localCode });
            }
          }
          candidates.sort((left, right) => left.savedAt - right.savedAt);
          if (candidates.length) restoredCodeMap[question.id] = candidates[candidates.length - 1].code;
        }
        codeRef.current = restoredCodeMap;
        setCodes(restoredCodeMap);
        localDraftsToSync.forEach((draft) => {
          api.put(endpoints.assessments.assignmentDrafts(activeAssignment.id), draft).catch(() => {});
        });
        const savedQuestionId = localDrafts.current_question_id;
        const savedQuestionIndex = questionRows.findIndex((question) => question.id === savedQuestionId);
        const resumeQuestionIndex = savedQuestionIndex >= 0 ? savedQuestionIndex : 0;
        setCurrentQuestionIndex(resumeQuestionIndex);
        writeLocalDrafts(activeAssignment.id, {
          ...localDrafts,
          current_question_id: questionRows[resumeQuestionIndex].id,
        });

        const idsByQuestion = Object.fromEntries(
          Object.entries(latestByQuestion).map(([questionId, submission]) => [questionId, submission.id]),
        );
        const statusEntries = await Promise.all(
          Object.entries(latestByQuestion).map(async ([questionId, submission]) => {
            try {
              const statusResponse = await api.get(
                endpoints.submissions.status(submission.id),
                { signal },
              );
              return [questionId, { ...submission, ...statusResponse.data }];
            } catch (statusError) {
              if (!signal.aborted) {
                updateSubmissionStatusError(
                  questionId,
                  getErrorMessage(statusError, 'Could not refresh this question’s evaluation status.'),
                );
              }
              return [questionId, submission];
            }
          }),
        );
        if (signal.aborted) return;
        const statusesByQuestion = Object.fromEntries(statusEntries);
        submissionIdsRef.current = idsByQuestion;
        setSubmissionIds(idsByQuestion);
        submissionStatusesRef.current = statusesByQuestion;
        setSubmissionStatuses(statusesByQuestion);
        void resumePendingClientEvaluations(statusesByQuestion);
      } catch (loadError) {
        if (signal.aborted) return;
        const message = getErrorMessage(loadError, 'Could not load this assessment attempt.');
        setError(message);
        addNotification(message, 'error');
      } finally {
        if (!signal.aborted) setLoading(false);
      }
    };

    loadAttempt();
    return () => controller.abort();
  }, [addNotification, id, reloadKey, resumePendingClientEvaluations, updateSubmissionStatusError]);

  const performFinalSubmit = useCallback(async (automatic = false) => {
    if (!assignment || !questions.length || finalized || submitLockRef.current || questionSubmitLocksRef.current.size) return;
    if (!automatic && (!allQuestionsSubmitted || !allQuestionSubmissionsSettled)) return;
    submitLockRef.current = true;
    setSubmitting(true);
    setShowSubmitConfirm(false);

    try {
      await flushDrafts();
      if (automatic) {
        const ids = { ...submissionIdsRef.current };
        for (const question of questions) {
          if (ids[question.id]) continue;
          try {
            await createAndEvaluateClientSubmission(
              question,
              codeRef.current[question.id] ?? DEFAULT_CODE,
            );
            ids[question.id] = submissionIdsRef.current[question.id];
          } catch (questionError) {
            const message = getErrorMessage(
              questionError,
              `Question ${question.order} could not be evaluated before automatic submission.`,
            );
            addNotification(`${question.title}: ${message}`, 'error', 7000);
          }
        }
      }

      await api.post(endpoints.assessments.submitAssignment(assignment.id), automatic ? { automatic: true } : {});
      setAssignment((current) => ({ ...current, status: 'submitted' }));
      setFinalized(true);
      addNotification(
        automatic
          ? 'Time is up. Your assessment has been submitted; any saved pending evaluations will continue.'
          : 'Assessment submitted. Your results have been saved.',
        'success',
      );
      navigate('/student/dashboard', { replace: true });
    } catch (submitError) {
      if (automatic) autoSubmitTriggeredRef.current = false;
      const message = getErrorMessage(submitError, 'Could not submit the assessment. Your code is still on this page; try again.');
      addNotification(message, 'error', 7000);
    } finally {
      submitLockRef.current = false;
      setSubmitting(false);
    }
  }, [addNotification, allQuestionSubmissionsSettled, allQuestionsSubmitted, assignment, createAndEvaluateClientSubmission, finalized, flushDrafts, navigate, questions]);

  const handleSubmitQuestion = useCallback(async () => {
    const canResumePending = currentSubmissionPending && currentSubmission?.client_error;
    const questionId = currentQuestion?.id;
    if (!assignment || !currentQuestion || !canEdit || (currentSubmissionPending && !canResumePending) || questionSubmitLocksRef.current.has(questionId) || submitLockRef.current) return;
    questionSubmitLocksRef.current.add(questionId);
    setSubmittingQuestionIds((current) => new Set(current).add(questionId));
    setSubmissionErrors((current) => ({ ...current, [currentQuestion.id]: '' }));
    const sourceCode = codeRef.current[currentQuestion.id] ?? DEFAULT_CODE;

    try {
      await saveDraftNow(currentQuestion.id, sourceCode);
      if (canResumePending) {
        await resumeClientEvaluation(currentQuestion.id, currentSubmission);
        addNotification(`Question ${currentQuestion.order} evaluation resumed.`, 'success');
      } else {
        await createAndEvaluateClientSubmission(currentQuestion, sourceCode);
        addNotification(`Question ${currentQuestion.order} submitted and evaluated.`, 'success');
      }
    } catch (submitError) {
      const message = getErrorMessage(submitError, 'Could not submit this question. Your code is still available to edit.');
      setSubmissionErrors((items) => ({ ...items, [currentQuestion.id]: message }));
      addNotification(message, 'error', 7000);
    } finally {
      questionSubmitLocksRef.current.delete(questionId);
      setSubmittingQuestionIds((current) => {
        const updated = new Set(current);
        updated.delete(questionId);
        return updated;
      });
      if (assessment?.is_timed !== false && remainingSeconds <= 0 && questionSubmitLocksRef.current.size === 0) performFinalSubmit(true);
    }
  }, [addNotification, assessment?.is_timed, assignment, canEdit, createAndEvaluateClientSubmission, currentQuestion, currentSubmission, currentSubmissionPending, performFinalSubmit, remainingSeconds, resumeClientEvaluation, saveDraftNow]);

  useEffect(() => {
    if (!deadlineAt || finalized) return undefined;
    const interval = window.setInterval(() => {
      const next = Math.max(0, Math.ceil((deadlineAt - Date.now()) / 1000));
      setRemainingSeconds(next);
      if (next === 0 && !autoSubmitTriggeredRef.current && !questionSubmitLocksRef.current.size && !submitLockRef.current) {
        autoSubmitTriggeredRef.current = true;
        performFinalSubmit(true);
      }
    }, 1000);
    return () => window.clearInterval(interval);
  }, [deadlineAt, finalized, performFinalSubmit]);

  useEffect(() => {
    const ids = Object.entries(submissionIds);
    if (!ids.length) return undefined;
    const controller = new AbortController();
    let intervalId;

    const poll = async () => {
      if (pollingInFlightRef.current || controller.signal.aborted) return;
      const pending = Object.entries(submissionIds).filter(([questionId]) =>
        !FINAL_STATES.has(submissionStatusesRef.current[questionId]?.status)
          || Boolean(submissionStatusErrorsRef.current[questionId]),
      );
      if (!pending.length) {
        setPolling(false);
        window.clearInterval(intervalId);
        return;
      }

      pollingInFlightRef.current = true;
      setPolling(true);
      await Promise.all(pending.map(async ([questionId, submissionId]) => {
          try {
            const response = await api.get(endpoints.submissions.status(submissionId), { signal: controller.signal });
            const result = response.data;
            if (controller.signal.aborted) return;
            const existing = submissionStatusesRef.current[questionId] || {};
            const nextStatus = {
              ...result,
              source_code: existing.source_code,
              ...(result.status === 'pending' && existing.client_error ? { client_error: true } : {}),
              ...(result.status === 'pending' && existing.client_processing ? {
                client_processing: true,
                client_phase: existing.client_phase,
                client_progress: existing.client_progress,
              } : {}),
            };
            updateQuestionSubmissionStatus(questionId, nextStatus);
            if (FINAL_STATES.has(result.status)) {
              setSubmissionErrors((items) => {
                const updated = { ...items };
                delete updated[questionId];
                return updated;
              });
            }
            updateSubmissionStatusError(questionId, null);
          } catch (pollError) {
            if (controller.signal.aborted) return;
            updateSubmissionStatusError(
              questionId,
              getErrorMessage(pollError, 'Could not refresh this question’s evaluation status.'),
            );
          }
        }));
      pollingInFlightRef.current = false;
      if (!controller.signal.aborted) {
        const stillPending = Object.entries(submissionIds).some(([questionId]) =>
          !FINAL_STATES.has(submissionStatusesRef.current[questionId]?.status)
            || Boolean(submissionStatusErrorsRef.current[questionId]),
        );
        if (!stillPending) {
          setPolling(false);
          window.clearInterval(intervalId);
        }
      }
    };

    intervalId = window.setInterval(poll, 5000);
    poll();
    return () => {
      controller.abort();
      window.clearInterval(intervalId);
    };
  }, [submissionIds, updateQuestionSubmissionStatus, updateSubmissionStatusError]);

  useEffect(() => {
    const onVisibilityChange = () => {
      if (document.visibilityState !== 'hidden' || finalized) return;
      Object.entries(codeRef.current).forEach(([questionId, sourceCode]) => {
        saveDraftNow(questionId, sourceCode);
      });
      if (assessment?.is_timed === false) return;
      setIntegrityWarnings((count) => count + 1);
      addNotification('Leaving the assessment tab has been detected.', 'warning');
    };
    const onFullscreenChange = () => setIsFullscreen(Boolean(document.fullscreenElement));
    const onClipboard = (event) => {
      event.preventDefault();
      event.stopImmediatePropagation();
    };
    const onKeyDown = (event) => {
      const key = event.key.toLowerCase();
      const clipboardShortcut = ((event.ctrlKey || event.metaKey) && ['c', 'v', 'x'].includes(key))
        || (event.ctrlKey && key === 'insert')
        || (event.shiftKey && ['insert', 'delete'].includes(key));
      if (clipboardShortcut) {
        event.preventDefault();
        event.stopImmediatePropagation();
      }
    };

    document.addEventListener('visibilitychange', onVisibilityChange);
    document.addEventListener('copy', onClipboard, true);
    document.addEventListener('cut', onClipboard, true);
    document.addEventListener('paste', onClipboard, true);
    document.addEventListener('keydown', onKeyDown, true);
    document.addEventListener('fullscreenchange', onFullscreenChange);
    return () => {
      document.removeEventListener('visibilitychange', onVisibilityChange);
      document.removeEventListener('copy', onClipboard, true);
      document.removeEventListener('cut', onClipboard, true);
      document.removeEventListener('paste', onClipboard, true);
      document.removeEventListener('keydown', onKeyDown, true);
      document.removeEventListener('fullscreenchange', onFullscreenChange);
    };
  }, [addNotification, assessment?.is_timed, finalized, saveDraftNow]);

  const updateCode = (questionId, nextCode) => {
    const updated = { ...codeRef.current, [questionId]: nextCode };
    codeRef.current = updated;
    setCodes(updated);
    if (assignment?.id) {
      const localDrafts = readLocalDrafts(assignment.id);
      writeLocalDrafts(assignment.id, {
        ...localDrafts,
        codes: { ...(localDrafts.codes || {}), [questionId]: nextCode },
        saved_at_by_question: {
          ...(localDrafts.saved_at_by_question || {}),
          [questionId]: Date.now(),
        },
        saved_at: Date.now(),
      });
      scheduleDraftSave(questionId, nextCode);
    }
  };

  const selectQuestion = (index) => {
    setCurrentQuestionIndex(index);
    if (assignment?.id && questions[index]) {
      const localDrafts = readLocalDrafts(assignment.id);
      writeLocalDrafts(assignment.id, {
        ...localDrafts,
        current_question_id: questions[index].id,
      });
    }
  };

  const handleRunCode = async () => {
    if (!assignment || !currentQuestion || !canEdit || running || currentQuestionSubmitting) return;
    if (!supportsWasmRunner()) {
      const message = 'This browser does not support WebAssembly workers. Please use a current version of Chrome, Edge, Firefox, or Safari.';
      setRunResults((current) => ({ ...current, [currentQuestion.id]: { error: message } }));
      return;
    }

    const questionId = currentQuestion.id;
    const sourceCode = codeRef.current[questionId] ?? DEFAULT_CODE;
    setRunning(true);
    setRunProgressByQuestion((current) => ({
      ...current,
      [questionId]: { phase: 'Loading visible test cases' },
    }));
    try {
      const casesResponse = await api.get(endpoints.submissions.executionCases, {
        params: { assignment_id: assignment.id, question_id: questionId },
      });
      const visibleCases = (casesResponse.data?.test_cases || []).filter((testCase) => testCase.is_sample);
      if (!visibleCases.length) {
        setRunResults((current) => ({
          ...current,
          [questionId]: { error: 'No visible test cases are available for this question.' },
        }));
        return;
      }

      if (!runnerRef.current) runnerRef.current = createWasmRunner();
      const execution = await runRunnerTask(() => runnerRef.current.runSubmission({
        sourceCode,
        testCases: visibleCases,
        timeLimitSeconds: casesResponse.data.time_limit_seconds,
        onStatus: (progress) => setRunProgressByQuestion((current) => ({
          ...current,
          [questionId]: progress,
        })),
      }));

      if (execution.compilation.status === 'error') {
        setRunResults((current) => ({
          ...current,
          [questionId]: {
            status: 'compilation_error',
            verdict: 'compilation_error',
            compilation_error: execution.compilation.diagnostics || 'The C compiler could not compile this code.',
            test_results: [],
          },
        }));
        return;
      }

      const executionById = new Map(execution.test_results.map((result) => [result.test_case_id, result]));
      const testResults = visibleCases.map((testCase) => {
        const result = executionById.get(String(testCase.id));
        let status = result?.status || 'runtime_error';
        if (status === 'completed') {
          status = result.exit_code === 0 && outputsMatch(result.stdout, testCase.expected_output)
            ? 'accepted'
            : result.exit_code === 0 ? 'wrong_answer' : 'runtime_error';
        }
        return {
          order: testCase.order,
          status,
          expected_output: testCase.expected_output,
          actual_output: result?.stdout || '',
          error: result?.stderr || '',
        };
      });
      const allPassed = testResults.every((result) => result.status === 'accepted');
      setRunResults((current) => ({
        ...current,
        [questionId]: {
          status: allPassed ? 'accepted' : 'failed',
          verdict: allPassed ? 'accepted' : 'failed',
          test_results: testResults,
        },
      }));
    } catch (runError) {
      const message = getErrorMessage(runError, 'The browser could not run this C program. Check the connection and try again.');
      setRunResults((current) => ({ ...current, [questionId]: { error: message } }));
      addNotification(message, 'error');
    } finally {
      setRunProgressByQuestion((current) => {
        const updated = { ...current };
        delete updated[questionId];
        return updated;
      });
      setRunning(false);
    }
  };

  const resetCurrentCode = () => {
    if (!currentQuestion) return;
    updateCode(currentQuestion.id, DEFAULT_CODE);
  };

  const enterFullscreen = async () => {
    try {
      if (!document.fullscreenElement) await attemptRootRef.current?.requestFullscreen?.();
      else await document.exitFullscreen?.();
    } catch {
      addNotification('Fullscreen is unavailable in this browser.', 'warning');
    }
  };

  const exitAttempt = async () => {
    setShowExitConfirm(false);
    await flushDrafts();
    if (assessment) navigate(`/student/assessments/${assessment.id}`);
    else navigate('/student/assessments');
  };

  const showLoadError = !loading && error;
  if (loading) {
    return <div className="flex min-h-dvh items-center justify-center bg-slate-950 text-sm text-slate-200">Loading your assessment…</div>;
  }
  if (showLoadError || !assessment || !assignment || !currentQuestion) {
    return (
      <div className="mx-auto max-w-2xl space-y-4 p-6">
        <Button variant="ghost" onClick={() => navigate('/student/assessments')}><ArrowLeft size={16} />My assessments</Button>
        <Alert type="error" title="Assessment could not be opened">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span>{error || 'This assessment is unavailable.'}</span>
            <Button variant="secondary" size="sm" onClick={() => { setLoading(true); setReloadKey((value) => value + 1); }}>Try again</Button>
          </div>
        </Alert>
      </div>
    );
  }

  const remainingLabel = formatTime(remainingSeconds);
  const timerUrgent = Boolean(deadlineAt && remainingSeconds <= 300);
  const currentRunResult = runResults[currentQuestion.id];
  const currentVerdict = currentSubmission?.verdict_display || currentSubmission?.verdict || currentSubmission?.status_display || currentSubmission?.status;
  const currentSubmissionError = submissionErrors[currentQuestion.id]
    || currentSubmission?.compilation_error
    || currentSubmission?.error_message;
  const hasResultsPanel = Boolean(
    submissionErrors[currentQuestion.id] || currentSubmission || currentRunResult
  );

  return (
    <div
      ref={attemptRootRef}
      className="flex min-h-dvh min-w-0 flex-col bg-slate-950 text-slate-100 lg:h-dvh lg:min-h-0 lg:overflow-hidden"
      onContextMenu={(event) => event.preventDefault()}
    >
      <header className="z-10 flex min-h-16 shrink-0 flex-wrap items-center justify-between gap-3 border-b border-slate-800 bg-slate-900 px-3 py-2 sm:px-5">
        <div className="flex min-w-0 items-center gap-3">
          <Button size="sm" variant="ghost" aria-label="Leave assessment" onClick={() => setShowExitConfirm(true)}>
            <ArrowLeft size={17} />
          </Button>
          <div className="min-w-0">
            <h1 className="truncate text-sm font-bold sm:text-base">{assessment.title}</h1>
            <p className="truncate text-xs text-slate-400">{user?.first_name || user?.email || 'Student'} · {questions.length} question{questions.length === 1 ? '' : 's'}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 sm:gap-4">
          {integrityWarnings > 0 && (
            <span className="hidden items-center gap-1 text-xs text-amber-300 sm:inline-flex" title="Tab changes detected">
              <ShieldAlert size={15} />{integrityWarnings} focus change{integrityWarnings === 1 ? '' : 's'}
            </span>
          )}
          <div className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 font-mono text-sm font-bold tabular-nums ${timerUrgent ? 'border-rose-500/50 bg-rose-950/60 text-rose-200' : 'border-slate-700 bg-slate-800 text-slate-100'}`} aria-live="polite" aria-label={deadlineAt ? `Time remaining ${remainingLabel}` : 'No time limit'}>
            <Clock3 size={16} />{deadlineAt ? remainingLabel : 'No time limit'}
          </div>
          <Button size="sm" variant="ghost" onClick={enterFullscreen} aria-label={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'} title={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}>
            {isFullscreen ? <Minimize size={16} /> : <Maximize size={16} />}
          </Button>
        </div>
      </header>

      <nav className="flex shrink-0 items-center gap-2 overflow-x-auto border-b border-slate-800 bg-slate-900/70 px-3 py-2 sm:px-5" aria-label="Assessment questions">
        {questions.map((question, index) => {
          const result = submissionStatuses[question.id];
          const done = FINAL_STATES.has(result?.status);
          const needsWork = done && result?.verdict !== 'accepted';
          return (
            <button key={question.id} type="button" onClick={() => selectQuestion(index)}
              aria-current={index === currentQuestionIndex ? 'step' : undefined}
              className={`inline-flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold transition ${index === currentQuestionIndex ? 'bg-primary-600 text-white' : needsWork ? 'bg-rose-950 text-rose-200 hover:bg-rose-900' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'}`}>
              {needsWork ? <AlertTriangle size={14} /> : done ? <Check size={14} /> : <span>Q{index + 1}</span>}
              <span className="hidden sm:inline">{question.title}</span>
            </button>
          );
        })}
        <span className="ml-auto hidden shrink-0 text-xs text-slate-500 sm:block">{currentQuestion.marks} marks</span>
      </nav>

      {integrityWarnings > 0 && (
        <div className="shrink-0 border-b border-amber-900/70 bg-amber-950/60 px-4 py-2 text-xs text-amber-100 sm:hidden">
          <AlertTriangle size={14} className="mr-1 inline" />{integrityWarnings} focus change{integrityWarnings === 1 ? '' : 's'} detected.
        </div>
      )}

      <div className="shrink-0 border-b border-sky-900/60 bg-sky-950/30 px-4 py-2 text-xs text-sky-100" role="note">
        C code runs in your browser. The server decides your final score, and results can rarely differ from local GCC.
      </div>

      {questionsNeedingWork > 0 && !finalized && (
        <div className="shrink-0 border-b border-rose-900/70 bg-rose-950/50 px-4 py-2 text-sm text-rose-100" role="status">
          {questionsNeedingWork} question{questionsNeedingWork === 1 ? ' needs' : 's need'} attention. Select a marked question to review the error, edit the code, and submit it again.
        </div>
      )}

      {Object.keys(submissionIds).length > 0 && (finalized || polling) && (
        <div className={`flex shrink-0 flex-wrap items-center justify-between gap-2 border-b px-4 py-2 text-sm ${finalized ? 'border-emerald-900/70 bg-emerald-950/60 text-emerald-100' : 'border-sky-900/70 bg-sky-950/50 text-sky-100'}`}>
          <span><CheckCircle2 size={16} className="mr-2 inline" />
            {finalized ? 'Assessment submitted.' : `Checking question results (${completedSubmissions}/${questions.length})…`}
            {Object.keys(submissionStatusErrors).length > 0 ? ' A status check failed; the page will keep retrying.' : finalized ? ' Code evaluation status is shown with each question.' : ''}
          </span>
        </div>
      )}

      <main className="grid min-w-0 flex-1 grid-cols-1 lg:min-h-0 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] lg:grid-rows-1">
        <section className="min-h-0 max-h-[42dvh] overflow-y-auto border-b border-slate-800 bg-slate-900 px-4 py-5 sm:px-6 lg:max-h-none lg:border-b-0 lg:border-r">
          <div className="mb-5 flex items-start justify-between gap-3">
            <div>
              <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-wide text-slate-400">
                <FileText size={14} />Question {currentQuestionIndex + 1} of {questions.length}
              </div>
              <h2 className="break-words text-xl font-bold text-white sm:text-2xl">{currentQuestion.title}</h2>
            </div>
            <Badge variant="info">{currentQuestion.marks} marks</Badge>
          </div>

          {currentQuestion.description && <p className="whitespace-pre-wrap text-sm leading-7 text-slate-300">{currentQuestion.description}</p>}
          {currentQuestion.inputFormat && <QuestionSection title="Input format">{currentQuestion.inputFormat}</QuestionSection>}
          {currentQuestion.outputFormat && <QuestionSection title="Output format">{currentQuestion.outputFormat}</QuestionSection>}
          {currentQuestion.constraints && <QuestionSection title="Constraints">{currentQuestion.constraints}</QuestionSection>}
          {currentQuestion.sampleInput && <QuestionSection title="Sample input" code>{currentQuestion.sampleInput}</QuestionSection>}
          {currentQuestion.sampleOutput && <QuestionSection title="Sample output" code>{currentQuestion.sampleOutput}</QuestionSection>}

          <div className="mt-6 flex flex-wrap items-center gap-2 border-t border-slate-800 pt-4 text-xs text-slate-400">
            <span className="capitalize">Difficulty: {currentQuestion.difficulty}</span>
            <span aria-hidden="true">·</span>
            <span>Language: C</span>
            {currentSubmission && <Badge variant={currentSubmission.status === 'completed' && currentSubmission.verdict === 'accepted' ? 'success' : 'neutral'}>{formatVerdict(currentVerdict)}</Badge>}
          </div>
        </section>

        <section className="flex min-h-[55dvh] min-w-0 flex-col bg-slate-950 lg:min-h-0">
          <div ref={workspacePanelsRef} className="flex min-h-0 flex-1 flex-col">
            <div className="flex min-h-0 flex-1 flex-col p-3 sm:p-4">
            <div className="mb-2 flex shrink-0 items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
                <span className="h-2 w-2 rounded-full bg-emerald-400" />solution.c
              </div>
              <span className="text-xs text-slate-500">
                {draftSaveStatus === 'saving' ? 'Saving…' : draftSaveStatus === 'error' ? 'Saved in this browser · sync failed' : 'Saved'} · C11
              </span>
            </div>
            <div className="min-h-48 min-w-0 flex-1 overflow-hidden rounded-xl border border-slate-800 lg:min-h-0">
              <CodeEditor code={currentCode} onChange={(value) => updateCode(currentQuestion.id, value)}
                language="c" readOnly={!canEdit} fontSize={14} />
            </div>
          </div>

          {hasResultsPanel && (
            <>
              <div
                role="separator"
                aria-label="Resize code editor and results"
                aria-orientation="horizontal"
                aria-valuemin={18}
                aria-valuemax={75}
                aria-valuenow={Math.round(resultsHeightPercent)}
                tabIndex={0}
                onPointerDown={(event) => {
                  event.preventDefault();
                  setResizingResults(true);
                }}
                onKeyDown={(event) => {
                  if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
                    event.preventDefault();
                    const delta = event.key === 'ArrowDown' ? 4 : -4;
                    const nextPercent = Math.min(75, Math.max(18, resultsHeightPercent + delta));
                    const bounds = workspacePanelsRef.current?.getBoundingClientRect();
                    setResultsHeightPercent(nextPercent);
                    if (bounds?.height) setResultsHeightPx(bounds.height * nextPercent / 100);
                  }
                }}
                className={`flex h-3 shrink-0 cursor-row-resize touch-none items-center justify-center border-y border-slate-800 bg-slate-900 hover:bg-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 ${resizingResults ? 'bg-slate-700' : ''}`}
                title="Drag to resize the code editor and results"
              >
                <span className="h-1 w-12 rounded-full bg-slate-500" />
              </div>
              <div
                className="min-h-32 min-w-0 shrink-0 overflow-y-auto overscroll-contain lg:min-h-0"
                style={{ height: `${resultsHeightPx}px` }}
              >
          {(submissionErrors[currentQuestion.id] || currentSubmission) && (
            <div className={`border-t px-4 py-3 ${currentSubmissionError || submissionStatusErrors[currentQuestion.id] || (FINAL_STATES.has(currentSubmission?.status) && currentSubmission?.verdict !== 'accepted') ? 'border-rose-900/70 bg-rose-950/40' : 'border-slate-800 bg-slate-900'}`} aria-live="polite">
              {submissionErrors[currentQuestion.id] ? (
                <>
                  <p className="mb-1 text-sm font-semibold text-rose-200">Question submission failed</p>
                  <pre className="whitespace-pre-wrap text-xs text-rose-100">{submissionErrors[currentQuestion.id]}</pre>
                  <p className="mt-2 text-xs text-slate-300">Your code is still available. Fix it and submit this question again.</p>
                </>
              ) : !FINAL_STATES.has(currentSubmission?.status) ? (
                <>
                  <p className="text-sm text-sky-200">Question evaluation is {formatVerdict(currentSubmission?.status)}…</p>
                  {currentSubmission?.client_phase && (
                    <p className="mt-1 text-xs text-slate-300">
                      {currentSubmission.client_phase}
                      {Number.isFinite(currentSubmission.client_progress)
                        ? ` · ${Math.round(currentSubmission.client_progress * 100)}%`
                        : ''}
                    </p>
                  )}
                  {submissionStatusErrors[currentQuestion.id] && (
                    <p className="mt-2 text-xs text-amber-200">
                      Could not refresh this result: {submissionStatusErrors[currentQuestion.id]}. The page will retry automatically.
                    </p>
                  )}
                </>
              ) : (
                <>
                  <p className={`mb-1 text-sm font-semibold ${currentSubmission.verdict === 'accepted' ? 'text-emerald-200' : 'text-rose-200'}`}>
                    {formatVerdict(currentVerdict)} · {currentSubmission.passed_test_cases ?? 0} / {currentSubmission.total_test_cases ?? 0} tests passed
                  </p>
                  {currentSubmissionError && <pre className="whitespace-pre-wrap text-xs text-rose-100">{currentSubmissionError}</pre>}
                  {submissionStatusErrors[currentQuestion.id] && (
                    <p className="mt-2 text-xs text-amber-200">
                      Could not load the full result: {submissionStatusErrors[currentQuestion.id]}. The page will retry automatically.
                    </p>
                  )}
                  {currentSubmission.test_case_verdicts?.length > 0 && (
                    <div className="mt-3 space-y-2">
                      {currentSubmission.test_case_verdicts.map((testCase) => (
                        <div key={testCase.test_case_order} className="rounded-lg border border-slate-800 p-3 text-xs">
                          {testCase.is_sample ? (
                            <>
                              <div className="mb-2 flex items-center justify-between gap-3">
                                <p className="font-semibold text-slate-300">Visible test case {testCase.test_case_order}</p>
                                <Badge variant={testCase.status === 'accepted' ? 'success' : 'danger'}>
                                  {formatVerdict(testCase.status)}
                                </Badge>
                              </div>
                              <div className="grid gap-2 sm:grid-cols-2">
                                <div>
                                  <p className="mb-1 text-slate-500">Expected output</p>
                                  <pre className="overflow-x-auto whitespace-pre-wrap text-slate-400">{testCase.expected_output ?? '(not available)'}</pre>
                                </div>
                                <div>
                                  <p className="mb-1 text-slate-500">Your output</p>
                                  <pre className="overflow-x-auto whitespace-pre-wrap text-slate-200">{testCase.actual_output || '(no output)'}</pre>
                                </div>
                              </div>
                              {testCase.error_message && <pre className="mt-2 whitespace-pre-wrap text-rose-300">{testCase.error_message}</pre>}
                            </>
                          ) : (
                            <div className="flex items-center justify-between gap-3">
                              <p className="font-semibold text-slate-300">Secret test case {testCase.test_case_order}</p>
                              <Badge variant={testCase.status === 'accepted' ? 'success' : 'danger'}>
                                {testCase.status_display || (testCase.status === 'accepted' ? 'Passed' : 'Failed')}
                              </Badge>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                  {currentSubmission.verdict !== 'accepted' && <p className="mt-2 text-xs text-slate-300">Your editor is still available. Make a correction and submit this question again.</p>}
                </>
              )}
            </div>
          )}

          {currentRunResult && (
            <div className="border-t border-slate-800 bg-slate-900 px-4 py-3">
              <div className="mb-2 flex items-center justify-between gap-3">
                <h3 className="text-xs font-bold uppercase tracking-wide text-slate-300">Sample run</h3>
                <Badge variant={currentRunResult.verdict === 'accepted' ? 'success' : currentRunResult.error || currentRunResult.compilation_error || currentRunResult.verdict === 'failed' ? 'danger' : 'warning'}>
                  {formatVerdict(currentRunResult.verdict || (currentRunResult.error ? 'unavailable' : currentRunResult.status))}
                </Badge>
              </div>
              {currentRunResult.error && <p className="text-sm text-rose-300">{currentRunResult.error}</p>}
              {currentRunResult.compilation_error && <pre className="whitespace-pre-wrap text-sm text-rose-300">{currentRunResult.compilation_error}</pre>}
              <div className="space-y-2">
                {(currentRunResult.test_results || []).map((result) => (
                  <div key={result.order} className="rounded-lg border border-slate-800 p-3 text-xs">
                    <p className="mb-2 font-semibold text-slate-300">Sample case {result.order}: <span className="capitalize">{formatVerdict(result.status)}</span></p>
                    <div className="grid gap-2 sm:grid-cols-2">
                      <pre className="overflow-x-auto whitespace-pre-wrap text-slate-400">Expected: {result.expected_output}</pre>
                      <pre className="overflow-x-auto whitespace-pre-wrap text-slate-200">Your output: {result.actual_output || result.error || '(no output)'}</pre>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {runProgressByQuestion[currentQuestion.id] && (
            <div className="border-t border-slate-800 bg-slate-900 px-4 py-2 text-xs text-sky-200" role="status" aria-live="polite">
              Sample run: {runProgressByQuestion[currentQuestion.id].phase}
              {Number.isFinite(runProgressByQuestion[currentQuestion.id].progress)
                ? ` · ${Math.round(runProgressByQuestion[currentQuestion.id].progress * 100)}%`
                : ''}
            </div>
          )}
              </div>
            </>
          )}
          </div>

          <footer className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-t border-slate-800 bg-slate-900 px-3 py-3 sm:px-4">
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" disabled={!canEdit} onClick={resetCurrentCode}>Reset code</Button>
              <Button variant="secondary" size="sm" loading={running} disabled={!canEdit || running || currentQuestionSubmitting} onClick={handleRunCode}>
                <Play size={14} />Run sample
              </Button>
            </div>
            <div className="flex flex-wrap justify-end gap-2">
              <Button size="sm" variant="secondary" loading={currentQuestionSubmitting}
                disabled={!canEdit || running || currentQuestionSubmitting || submitting || (currentSubmissionPending && !currentSubmission?.client_error)}
                onClick={handleSubmitQuestion}>
                <Send size={14} />{currentSubmissionPending
                  ? currentSubmission?.client_error ? 'Resume evaluation' : 'Evaluating question'
                  : submissionIds[currentQuestion.id] ? 'Submit question again' : 'Submit question'}
              </Button>
              {allQuestionsSubmitted && (
                <Button size="sm" loading={submitting} disabled={finalized || submitting || submittingQuestionIds.size > 0 || !allQuestionSubmissionsSettled}
                  onClick={() => setShowSubmitConfirm(true)}>
                  <CheckCircle2 size={14} />Submit assessment
                </Button>
              )}
            </div>
          </footer>
        </section>
      </main>

      <Modal
        isOpen={showSubmitConfirm}
        onClose={() => setShowSubmitConfirm(false)}
        title="Finish this assessment?"
        footer={(
          <>
            <Button variant="secondary" onClick={() => setShowSubmitConfirm(false)}>Keep working</Button>
            <Button variant="danger" loading={submitting} disabled={!allQuestionSubmissionsSettled} onClick={() => performFinalSubmit(false)}>Submit assessment</Button>
          </>
        )}
      >
        <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">
          Your submitted answers will be finalized and the assessment will close. You can still edit and re-submit any question until you finish the assessment.
        </p>
        {deadlineAt && remainingSeconds <= 300 && <p className="mt-3 text-sm font-medium text-amber-700 dark:text-amber-300">Time remaining: {remainingLabel}</p>}
      </Modal>

      <Modal
        isOpen={showExitConfirm}
        onClose={() => setShowExitConfirm(false)}
        title="Leave the coding workspace?"
        footer={(
          <>
            <Button variant="secondary" onClick={() => setShowExitConfirm(false)}>Stay here</Button>
            <Button variant="danger" onClick={exitAttempt}>Leave attempt</Button>
          </>
        )}
      >
        <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">
          {assessment.is_timed === false
            ? 'Your work is autosaved. You can leave and return later; the assessment has no completion timer.'
            : 'The timer continues while you are away. Your work is autosaved, so you can return to finish before time expires.'}
        </p>
      </Modal>
    </div>
  );
};

const QuestionSection = ({ title, code = false, children }) => (
  <div className="mt-6">
    <h3 className="mb-2 text-sm font-semibold text-slate-200">{title}</h3>
    {code ? (
      <pre className="max-w-full overflow-x-auto whitespace-pre-wrap rounded-lg border border-slate-800 bg-slate-950 p-3 font-mono text-sm text-slate-300">{children}</pre>
    ) : (
      <p className="whitespace-pre-wrap text-sm leading-6 text-slate-300">{children}</p>
    )}
  </div>
);

export default AssessmentAttemptPage;
