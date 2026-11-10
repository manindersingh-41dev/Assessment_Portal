"""
Service layer for Assessment Management.

Contains business logic for assessments, assignments, and results.
"""

from django.db import transaction
from django.utils import timezone
from django.db.models import Q, Sum, Count
from datetime import timedelta

from .models import (
    Assessment, AssessmentQuestion, StudentBatch,
    AssessmentAssignment, AssessmentResult
)
from users.models import User


class AssessmentService:
    """Service for assessment operations."""

    @staticmethod
    def validate_assessment_timing(start_datetime, end_datetime, duration_minutes):
        """Validate assessment timing."""
        errors = []

        if start_datetime >= end_datetime:
            errors.append('Start datetime must be before end datetime')

        duration = end_datetime - start_datetime
        duration_seconds = duration.total_seconds()
        duration_from_minutes = duration_minutes * 60

        if duration_seconds < duration_from_minutes:
            errors.append(
                f'Assessment window ({duration.total_seconds() / 60:.0f} minutes) '
                f'must be at least duration ({duration_minutes} minutes)'
            )

        return errors

    @staticmethod
    def validate_marks_configuration(total_marks, passing_marks, question_marks_sum):
        """Validate marks configuration."""
        errors = []

        if passing_marks > total_marks:
            errors.append('Passing marks cannot exceed total marks')

        if question_marks_sum != total_marks:
            errors.append(
                f'Total question marks ({question_marks_sum}) '
                f'must equal assessment marks ({total_marks})'
            )

        return errors

    @staticmethod
    def add_question_to_assessment(assessment, question, order, marks=None, is_mandatory=True, show_to_students=True):
        """Add question to assessment with versioning."""
        from questions.models import Question

        if not isinstance(question, Question):
            raise ValueError('question must be a Question instance')

        if question.status != Question.Status.ACTIVE:
            raise ValueError('Only active questions can be added to assessments')

        # Use provided marks or default to question marks
        marks = marks or question.total_marks

        # Create snapshot
        assessment_question = AssessmentQuestion.objects.create(
            assessment=assessment,
            question=question,
            question_title=question.title,
            question_description=question.description,
            question_input_format=question.input_format,
            question_output_format=question.output_format,
            question_constraints=question.constraints,
            question_difficulty=question.difficulty,
            question_language=question.language,
            question_order=order,
            marks=marks,
            is_mandatory=is_mandatory,
            show_to_students=show_to_students
        )

        return assessment_question

    @staticmethod
    def get_assessment_statistics(assessment):
        """Get comprehensive statistics for an assessment."""
        assignments = AssessmentAssignment.objects.filter(assessment=assessment)

        results = AssessmentResult.objects.filter(assessment=assessment)

        submitted_assignments = assignments.filter(
            status=AssessmentAssignment.Status.SUBMITTED
        )

        evaluated_assignments = assignments.filter(
            status=AssessmentAssignment.Status.GRADED
        )

        stats = {
            'total_assigned': assignments.count(),
            'started': assignments.filter(status__in=[
                AssessmentAssignment.Status.STARTED,
                AssessmentAssignment.Status.SUBMITTED,
                AssessmentAssignment.Status.GRADED
            ]).count(),
            'submitted': submitted_assignments.count(),
            'evaluated': evaluated_assignments.count(),
            'pending_evaluation': submitted_assignments.count(),
            'average_score': results.values('total_marks_obtained').aggregate(
                avg=models.Avg('total_marks_obtained')
            )['avg'] or 0,
            'pass_rate': (
                results.filter(passed=True).count() / results.count() * 100
                if results.exists() else 0
            ),
            'highest_score': results.aggregate(
                max=models.Max('total_marks_obtained')
            )['max'] or 0,
            'lowest_score': results.aggregate(
                min=models.Min('total_marks_obtained')
            )['min'] or 0,
        }

        return stats

    @staticmethod
    def can_publish(assessment):
        """Check if assessment can be published."""
        errors = []

        if assessment.status != Assessment.Status.DRAFT:
            errors.append('Only draft assessments can be published')

        if not assessment.questions.exists():
            errors.append('Assessment must have at least one question')

        # Check if total marks match
        total_question_marks = sum(q.marks for q in assessment.questions.all())
        if total_question_marks != assessment.total_marks:
            errors.append(
                f'Total question marks ({total_question_marks}) '
                f'must equal assessment marks ({assessment.total_marks})'
            )

        return errors


class AssignmentService:
    """Service for assignment operations."""

    @staticmethod
    @transaction.atomic
    def create_assignments_for_all_students(assessment):
        """Ensure every currently registered student has an assessment assignment."""
        student_ids = list(
            User.objects.filter(role='student', is_active=True).values_list(
                'id', flat=True
            )
        )
        if not student_ids:
            return []

        existing_student_ids = set(
            AssessmentAssignment.objects.filter(
                assessment=assessment,
                student_id__in=student_ids,
            ).values_list('student_id', flat=True)
        )
        missing_assignments = [
            AssessmentAssignment(
                assessment=assessment,
                student_id=student_id,
                created_by_id=assessment.created_by_id,
            )
            for student_id in student_ids
            if student_id not in existing_student_ids
        ]
        if missing_assignments:
            AssessmentAssignment.objects.bulk_create(
                missing_assignments,
                batch_size=1000,
                ignore_conflicts=True,
            )

        return list(
            AssessmentAssignment.objects.filter(
                assessment=assessment,
                student_id__in=student_ids,
            ).select_related('assessment', 'student')
        )

    @staticmethod
    @transaction.atomic
    def ensure_open_assessment_assignments(student):
        """Create a student's assignment rows for every published open assessment."""
        open_assessments = list(
            Assessment.objects.filter(
                is_published=True,
                is_open_to_all_students=True,
            ).values_list('id', 'created_by_id')
        )
        if not open_assessments:
            return

        existing_assessment_ids = set(
            AssessmentAssignment.objects.filter(
                student=student,
                assessment_id__in=[assessment_id for assessment_id, _ in open_assessments],
            ).values_list('assessment_id', flat=True)
        )
        missing_assignments = [
            AssessmentAssignment(
                assessment_id=assessment_id,
                student=student,
                created_by_id=created_by_id,
            )
            for assessment_id, created_by_id in open_assessments
            if assessment_id not in existing_assessment_ids
        ]
        if missing_assignments:
            AssessmentAssignment.objects.bulk_create(
                missing_assignments,
                ignore_conflicts=True,
            )

    @staticmethod
    @transaction.atomic
    def create_assignments(assessment, student_ids=None, batch_ids=None, deadline=None):
        """Create assignments for students or batches."""
        if not student_ids:
            student_ids = []
        if not batch_ids:
            batch_ids = []

        # Collect all unique students
        students_set = set()

        # Add individual students
        if student_ids:
            students_set.update(
                User.objects.filter(id__in=student_ids, role='student').values_list('id', flat=True)
            )

        # Add students from batches
        if batch_ids:
            batch_students = User.objects.filter(
                batches__id__in=batch_ids,
                role='student'
            ).values_list('id', flat=True).distinct()
            students_set.update(batch_students)

        # Create assignments
        assignments = []
        for student_id in students_set:
            assignment, created = AssessmentAssignment.objects.get_or_create(
                assessment=assessment,
                student_id=student_id,
                defaults={
                    'due_at': deadline,
                    'created_by': assessment.created_by,
                }
            )
            if created:
                assignments.append(assignment)

        return assignments

    @staticmethod
    def can_student_start(assignment):
        """Check if student can start assignment."""
        return assignment.can_start()

    @staticmethod
    @transaction.atomic
    def evaluate_assignment(assignment, marks_obtained, feedback=''):
        """Evaluate an assignment and create/update result."""
        if assignment.status != AssessmentAssignment.Status.SUBMITTED:
            raise ValueError('Assignment must be submitted before evaluation')

        # Update assignment
        total_marks = assignment.assessment.total_marks
        passed = total_marks > 0 and marks_obtained >= total_marks
        assignment.status = AssessmentAssignment.Status.GRADED
        assignment.save(update_fields=['status', 'updated_at'])

        # Calculate percentage
        percentage = (marks_obtained / total_marks * 100) if total_marks else 0

        # Create or update result
        result, created = AssessmentResult.objects.update_or_create(
            assessment=assignment.assessment,
            student=assignment.student,
            defaults={
                'total_marks_obtained': marks_obtained,
                'percentage': percentage,
                'passed': passed,
                'attempted_at': assignment.submitted_at,
                'feedback': feedback,
            }
        )

        return result

    @staticmethod
    def allow_resubmission(assignment):
        """Check if resubmission is allowed."""
        if assignment.assessment.resubmission_policy == Assessment.ResubmissionPolicy.NOT_ALLOWED:
            return False

        if assignment.assessment.resubmission_policy == Assessment.ResubmissionPolicy.ONCE:
            return assignment.attempt_number == 1

        if assignment.assessment.resubmission_policy == Assessment.ResubmissionPolicy.UNLIMITED:
            return True

        return False

    @staticmethod
    @transaction.atomic
    def create_resubmission(original_assignment):
        """Create a new attempt for resubmission."""
        if not AssignmentService.allow_resubmission(original_assignment):
            raise ValueError('Resubmission not allowed for this assessment')

        # Create new assignment with next attempt number
        new_attempt = original_assignment.attempt_number + 1

        new_assignment = AssessmentAssignment.objects.create(
            assessment=original_assignment.assessment,
            student=original_assignment.student,
            attempt_number=new_attempt,
            deadline=original_assignment.deadline,
            status=AssessmentAssignment.Status.ASSIGNED
        )

        return new_assignment

    @staticmethod
    def get_student_submissions(student, assessment=None):
        """Get all submissions for a student."""
        queryset = AssessmentAssignment.objects.filter(student=student)

        if assessment:
            queryset = queryset.filter(assessment=assessment)

        return queryset.order_by('-attempt_number', '-assigned_at')

    @staticmethod
    def get_assessment_submissions_summary(assessment):
        """Get summary of submissions for an assessment."""
        assignments = AssessmentAssignment.objects.filter(assessment=assessment)

        summary = {
            'total': assignments.count(),
            'assigned': assignments.filter(status=AssessmentAssignment.Status.ASSIGNED).count(),
            'started': assignments.filter(status=AssessmentAssignment.Status.STARTED).count(),
            'submitted': assignments.filter(status=AssessmentAssignment.Status.SUBMITTED).count(),
            'evaluated': assignments.filter(status=AssessmentAssignment.Status.GRADED).count(),
        }

        return summary


class QuestionSnapshotService:
    """Service for managing question snapshots in assessments."""

    @staticmethod
    def get_question_snapshot(assessment_question):
        """Get snapshot data for a question in an assessment."""
        return {
            'id': assessment_question.question.id,
            'title': assessment_question.question.title,
            'description': assessment_question.question_description,
            'input_format': assessment_question.question_input_format,
            'output_format': assessment_question.question_output_format,
            'constraints': assessment_question.question_constraints,
            'sample_input': assessment_question.question.sample_input,
            'sample_output': assessment_question.question.sample_output,
            'difficulty': assessment_question.question_difficulty,
            'language': assessment_question.question_language,
        }

    @staticmethod
    def compare_with_original(assessment_question):
        """Compare snapshot with current question state."""
        question = assessment_question.question

        changes = {
            'title_changed': assessment_question.question.title != question.title,
            'description_changed': assessment_question.question_description != question.description,
            'constraints_changed': assessment_question.question_constraints != question.constraints,
            'difficulty_changed': assessment_question.question_difficulty != question.difficulty,
        }

        return changes
