import React, { useEffect, useMemo, useState } from 'react';
import { Download, FileJson, Plus, Upload } from 'lucide-react';
import { Alert, CardDescription } from '../../components/Common';
import { Button } from '../../components/Button';
import { Modal } from '../../components/Modal';
import api from '../../api/client';
import { config } from '../../constants/config';

const questionTemplate = {
  questions: [
    {
      title: 'Sum two integers',
      description: 'Read two integers and print their sum.',
      input_format: 'Two space-separated integers.',
      output_format: 'Print their sum.',
      constraints: '-1000000 <= a, b <= 1000000',
      sample_input: '2 3',
      sample_output: '5',
      sample_explanation: '2 + 3 = 5',
      difficulty: 'easy',
      topic: 'arithmetic',
      language: 'c',
      total_marks: 10,
      time_limit_seconds: 30,
      memory_limit_mb: 128,
      test_cases: [
        { input: '2 3', expected_output: '5', marks: 5, is_sample: true },
        { input: '-4 7', expected_output: '3', marks: 5, is_sample: false },
      ],
    },
    {
      title: 'Multiply two integers',
      description: 'Read two integers and print their product.',
      input_format: 'Two space-separated integers.',
      output_format: 'Print their product.',
      constraints: '-10000 <= a, b <= 10000',
      sample_input: '4 6',
      sample_output: '24',
      sample_explanation: '4 * 6 = 24',
      difficulty: 'easy',
      topic: 'arithmetic',
      language: 'c',
      total_marks: 6,
      time_limit_seconds: 30,
      memory_limit_mb: 128,
      test_cases: [
        { input: '4 6', expected_output: '24', marks: 2, is_sample: true },
        { input: '-3 5', expected_output: '-15', marks: 2, is_sample: false },
        { input: '0 9', expected_output: '0', marks: 2, is_sample: false },
      ],
    },
  ],
};

const flattenErrors = (value, path = '') => {
  if (typeof value === 'string') return [path ? `${path}: ${value}` : value];
  if (Array.isArray(value)) {
    return value.flatMap((item, index) => flattenErrors(item, `${path}[${index + 1}]`));
  }
  if (value && typeof value === 'object') {
    return Object.entries(value).flatMap(([key, item]) => (
      flattenErrors(item, path ? `${path}.${key}` : key)
    ));
  }
  return [];
};

const fingerprintFields = ['title', 'description', 'input_format', 'output_format', 'constraints'];
const normalizeQuestionText = (value) => String(value || '').split(/\s+/).filter(Boolean).join(' ').toLowerCase();
const questionFingerprint = (question) => JSON.stringify(
  fingerprintFields.map((field) => normalizeQuestionText(question[field])),
);

const BulkQuestionImportModal = ({
  isOpen,
  onClose,
  onImported,
  onAddExisting,
  questionBank = [],
  selectedQuestionIds = [],
}) => {
  const [questions, setQuestions] = useState([]);
  const [fileName, setFileName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const testCaseCount = useMemo(
    () => questions.reduce((total, question) => total + (Array.isArray(question.test_cases) ? question.test_cases.length : 0), 0),
    [questions],
  );
  const bankQuestionsByFingerprint = useMemo(() => new Map(
    questionBank.map((question) => [questionFingerprint(question), question]),
  ), [questionBank]);
  const matchedImportRows = useMemo(() => questions.map((question, index) => ({
    question,
    index,
    existing: bankQuestionsByFingerprint.get(questionFingerprint(question)),
  })).filter((item) => item.existing), [bankQuestionsByFingerprint, questions]);
  const selectedIds = useMemo(
    () => new Set(selectedQuestionIds.map(String)),
    [selectedQuestionIds],
  );
  const existingQuestionsToAdd = useMemo(() => {
    const uniqueMatches = new Map();
    matchedImportRows.forEach(({ existing }) => {
      if (!selectedIds.has(String(existing.id))) uniqueMatches.set(String(existing.id), existing);
    });
    return [...uniqueMatches.values()];
  }, [matchedImportRows, selectedIds]);
  const questionsToImport = useMemo(() => questions.filter(
    (question) => !bankQuestionsByFingerprint.has(questionFingerprint(question)),
  ), [bankQuestionsByFingerprint, questions]);

  useEffect(() => {
    if (!isOpen) return;
    setQuestions([]);
    setFileName('');
    setError('');
  }, [isOpen]);

  const handleFileChange = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;

    setError('');
    setQuestions([]);
    setFileName(file.name);
    try {
      const parsed = JSON.parse(await file.text());
      if (!parsed || !Array.isArray(parsed.questions)) {
        throw new Error('The JSON file must contain a top-level "questions" array.');
      }
      if (parsed.questions.some((question) => !question || typeof question !== 'object' || Array.isArray(question))) {
        throw new Error('Every item in "questions" must be a question object.');
      }
      if (parsed.questions.length === 0) {
        throw new Error('Add at least one question to the file.');
      }
      if (parsed.questions.length > 100) {
        throw new Error('A file can contain at most 100 questions.');
      }
      setQuestions(parsed.questions);
    } catch (parseError) {
      setFileName('');
      setError(parseError instanceof SyntaxError
        ? 'The selected file is not valid JSON.'
        : parseError.message || 'Could not read this file.');
    }
  };

  const downloadTemplate = () => {
    const blob = new Blob([`${JSON.stringify(questionTemplate, null, 2)}\n`], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'bulk-question-template.json';
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const importQuestions = async () => {
    if (!questionsToImport.length || loading) return;
    setLoading(true);
    setError('');
    try {
      const response = await api.post(config.api.endpoints.questions.bulkCreate, { questions: questionsToImport });
      const createdQuestions = response.data?.questions;
      if (!Array.isArray(createdQuestions) || createdQuestions.length !== questionsToImport.length) {
        throw new Error('The server did not confirm that every question was created.');
      }
      onImported(createdQuestions);
      if (!existingQuestionsToAdd.length) onClose();
    } catch (importError) {
      const details = flattenErrors(importError?.response?.data);
      setError(details.length
        ? details.slice(0, 20).join('\n')
        : importError.message || 'Could not import these questions. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => !loading && onClose()}
      title="Bulk import questions"
      size="2xl"
      footer={(
        <>
          <Button variant="secondary" disabled={loading} onClick={onClose}>Cancel</Button>
          {existingQuestionsToAdd.length > 0 && (
            <Button icon={Plus} variant="success" disabled={loading} onClick={() => {
              onAddExisting(existingQuestionsToAdd);
              if (!questionsToImport.length) onClose();
            }}>
              Add {existingQuestionsToAdd.length} existing to assessment
            </Button>
          )}
          {questionsToImport.length > 0 && (
            <Button icon={Upload} loading={loading} disabled={loading} onClick={importQuestions}>
              Import {questionsToImport.length} new question{questionsToImport.length === 1 ? '' : 's'}
            </Button>
          )}
        </>
      )}
    >
      <div className="space-y-5">
        <div>
          <CardDescription>
            Upload one JSON file. Each question contains its own <code>test_cases</code> array, so questions can have different numbers of cases. Every question needs at least one sample case, and its test-case marks must add up to <code>total_marks</code>. The entire file is validated before any questions are saved.
          </CardDescription>
        </div>

        {error && <Alert type="error" title="Import not completed"><pre className="max-h-40 overflow-auto whitespace-pre-wrap text-sm">{error}</pre></Alert>}

        {matchedImportRows.length > 0 && (
          <Alert type="info" title="Questions already in your bank">
            {matchedImportRows.length} uploaded question{matchedImportRows.length === 1 ? ' matches' : 's match'} existing bank content. Add those to the assessment without creating duplicate bank entries.
            {existingQuestionsToAdd.length === 0 && ' All matching questions are already selected in this assessment.'}
          </Alert>
        )}

        <div className="flex flex-wrap items-center gap-3">
          <label className="inline-flex min-h-10 cursor-pointer items-center gap-2 rounded-lg border border-slate-300 px-4 text-sm font-semibold text-slate-800 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-100 dark:hover:bg-slate-800">
            <FileJson size={16} aria-hidden="true" />Choose JSON file
            <input className="sr-only" type="file" accept=".json,application/json" onChange={handleFileChange} disabled={loading} />
          </label>
          <Button variant="ghost" icon={Download} onClick={downloadTemplate}>Download example template</Button>
          {fileName && <span className="text-sm text-slate-500">{fileName}</span>}
        </div>

        {questions.length > 0 ? (
          <section className="rounded-xl border border-slate-200 dark:border-slate-700" aria-live="polite">
            <div className="flex flex-wrap justify-between gap-2 border-b border-slate-200 px-4 py-3 text-sm dark:border-slate-700">
              <strong>{questions.length} questions ready</strong>
              <span className="text-slate-500">{testCaseCount} test cases total</span>
            </div>
            <ol className="max-h-60 divide-y divide-slate-100 overflow-y-auto dark:divide-slate-800">
              {questions.map((question, index) => (
                <li key={`${question.title || 'question'}-${index}`} className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
                  <span className="min-w-0 truncate font-medium text-slate-800 dark:text-slate-200">{question.title || `Question ${index + 1}`}</span>
                  <span className="flex shrink-0 items-center gap-2 text-xs text-slate-500">
                    {bankQuestionsByFingerprint.has(questionFingerprint(question)) && (
                      <span className="rounded-full bg-emerald-100 px-2 py-0.5 font-medium text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200">Already in bank</span>
                    )}
                    {Array.isArray(question.test_cases) ? question.test_cases.length : 0} test cases
                  </span>
                </li>
              ))}
            </ol>
          </section>
        ) : (
          <p className="rounded-lg bg-slate-50 p-4 text-sm text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            The template includes two example questions with different test-case counts. Replace the examples with your question data and keep at least one sample case per question.
          </p>
        )}
      </div>
    </Modal>
  );
};

export default BulkQuestionImportModal;
