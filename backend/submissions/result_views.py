"""
Views for Submission Management and Assessment Results.

Handles student submission history, faculty result viewing, and exports.
"""

import logging
import csv
from io import StringIO
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from submissions.models import CodeSubmission, TestCaseVerdict
from assessments.models import Assessment, AssessmentAssignment
from .result_serializers import (
    SubmissionSummarySerializer, StudentSubmissionHistorySerializer,
    AssessmentSubmissionOverviewSerializer, SubmissionSourceCodeSerializer
)
from .evaluation_service import SubmissionAggregationService
from .permissions import IsStudent, CanViewSubmissionResult
from assessments.permissions import IsApprovedFaculty

logger = logging.getLogger(__name__)


class ResultPagination(PageNumberPagination):
    """Pagination for results."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class StudentSubmissionViewSet(viewsets.ViewSet):
    """ViewSet for student submission history and results."""

    permission_classes = [permissions.IsAuthenticated, IsStudent]
    pagination_class = ResultPagination

    @action(detail=False, methods=['get'])
    def history(self, request):
        """
        Get submission history for current student.

        GET /api/results/submissions/history/
        """
        assignment_id = request.query_params.get('assignment_id')

        submissions = SubmissionAggregationService.get_student_submissions(
            student_id=str(request.user.id),
            assignment_id=assignment_id
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(submissions, request)

        if page is not None:
            serializer = StudentSubmissionHistorySerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = StudentSubmissionHistorySerializer(submissions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def results(self, request):
        """
        Get scorecards for submitted assessments owned by the current student.

        GET /api/results/submissions/results/
        """
        assignments = AssessmentAssignment.objects.filter(
            student=request.user,
            status__in=[
                AssessmentAssignment.Status.SUBMITTED,
                AssessmentAssignment.Status.GRADED,
            ],
        ).select_related('assessment', 'student').order_by('-submitted_at', '-created_at')
        results = [
            SubmissionAggregationService.get_assignment_scorecard(assignment)
            for assignment in assignments
        ]

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(results, request)
        return paginator.get_paginated_response(page if page is not None else results)

    @action(detail=False, methods=['get'])
    def assignment_result(self, request):
        """
        Get detailed result for a specific assignment.

        GET /api/results/submissions/assignment_result/?assignment_id=uuid
        """
        assignment_id = request.query_params.get('assignment_id')

        if not assignment_id:
            return Response(
                {'error': 'assignment_id query parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            assignment = AssessmentAssignment.objects.get(
                id=assignment_id,
                student=request.user
            )
        except AssessmentAssignment.DoesNotExist:
            return Response(
                {'error': 'Assignment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if assignment.status not in {
            AssessmentAssignment.Status.SUBMITTED,
            AssessmentAssignment.Status.GRADED,
        }:
            return Response(
                {'error': 'Submit the assessment before viewing its scorecard.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(SubmissionAggregationService.get_assignment_scorecard(assignment))

    @action(detail=False, methods=['get'])
    def question_submissions(self, request):
        """
        Get submissions for a specific question.

        GET /api/results/submissions/question_submissions/?assignment_id=uuid&question_id=uuid
        """
        assignment_id = request.query_params.get('assignment_id')
        question_id = request.query_params.get('question_id')

        if not assignment_id or not question_id:
            return Response(
                {'error': 'assignment_id and question_id parameters required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            assignment = AssessmentAssignment.objects.get(
                id=assignment_id,
                student=request.user
            )
        except AssessmentAssignment.DoesNotExist:
            return Response(
                {'error': 'Assignment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get submissions for this question
        submissions = CodeSubmission.objects.filter(
            assignment=assignment,
            question_id=question_id
        ).order_by('-created_at')

        serializer = SubmissionSummarySerializer(submissions, many=True)
        return Response(serializer.data)


class FacultyResultViewSet(viewsets.ViewSet):
    """ViewSet for faculty result viewing and export."""

    permission_classes = [permissions.IsAuthenticated, IsApprovedFaculty]
    pagination_class = ResultPagination

    @action(detail=False, methods=['get'])
    def assessment_overview(self, request):
        """
        Get this faculty member's submissions, optionally filtered by assessment.

        GET /api/results/faculty/assessment_overview/?assessment_id=uuid
        """
        assessment_id = request.query_params.get('assessment_id')

        if assessment_id:
            try:
                Assessment.objects.get(id=assessment_id, created_by=request.user)
            except Assessment.DoesNotExist:
                return Response(
                    {'error': 'Assessment not found or not authorized'},
                    status=status.HTTP_404_NOT_FOUND
                )

        submissions = SubmissionAggregationService.get_assessment_submissions(
            assessment_id=assessment_id,
            faculty_id=str(request.user.id),
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(submissions, request)

        if page is not None:
            serializer = AssessmentSubmissionOverviewSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = AssessmentSubmissionOverviewSerializer(submissions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def student_submissions(self, request):
        """
        Get all submissions for a specific student in an assessment.

        GET /api/results/faculty/student_submissions/?assessment_id=uuid&student_id=uuid
        """
        assessment_id = request.query_params.get('assessment_id')
        student_id = request.query_params.get('student_id')

        if not assessment_id or not student_id:
            return Response(
                {'error': 'assessment_id and student_id parameters required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            assessment = Assessment.objects.get(id=assessment_id, created_by=request.user)
        except Assessment.DoesNotExist:
            return Response(
                {'error': 'Assessment not found or not authorized'},
                status=status.HTTP_404_NOT_FOUND
            )

        submissions = CodeSubmission.objects.filter(
            assignment__assessment=assessment,
            student_id=student_id
        ).order_by('-created_at')

        serializer = SubmissionSummarySerializer(submissions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def submission_details(self, request):
        """
        Get detailed view of a submission including source code and test results.

        GET /api/results/faculty/submission_details/?submission_id=uuid
        """
        submission_id = request.query_params.get('submission_id')

        if not submission_id:
            return Response(
                {'error': 'submission_id query parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            submission = CodeSubmission.objects.get(id=submission_id)

            # Check authorization
            if submission.assignment.assessment.created_by != request.user:
                return Response(
                    {'error': 'Not authorized to view this submission'},
                    status=status.HTTP_403_FORBIDDEN
                )

        except CodeSubmission.DoesNotExist:
            return Response(
                {'error': 'Submission not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get test case verdicts
        verdicts = TestCaseVerdict.objects.filter(submission=submission).order_by('test_case_order')

        verdict_data = []
        for verdict in verdicts:
            verdict_data.append({
                'test_case_order': verdict.test_case_order,
                'is_sample': verdict.is_sample,
                'status': verdict.status,
                'marks_obtained': verdict.marks_obtained,
                'execution_time_ms': verdict.execution_time_ms,
                'memory_used_mb': verdict.memory_used_mb,
                'actual_output': verdict.actual_output,
                'error_message': verdict.error_message
            })

        response_data = {
            'submission': SubmissionSourceCodeSerializer(submission).data,
            'test_case_verdicts': verdict_data
        }

        return Response(response_data)

    @action(detail=False, methods=['get'])
    def assessment_statistics(self, request):
        """
        Get statistics for an assessment.

        GET /api/results/faculty/assessment_statistics/?assessment_id=uuid
        """
        assessment_id = request.query_params.get('assessment_id')

        if not assessment_id:
            return Response(
                {'error': 'assessment_id query parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            assessment = Assessment.objects.get(id=assessment_id, created_by=request.user)
        except Assessment.DoesNotExist:
            return Response(
                {'error': 'Assessment not found or not authorized'},
                status=status.HTTP_404_NOT_FOUND
            )

        assignments = AssessmentAssignment.objects.filter(assessment=assessment).select_related(
            'assessment', 'student'
        )
        scorecards = [
            SubmissionAggregationService.get_assignment_scorecard(assignment)
            for assignment in assignments
        ]
        submissions = CodeSubmission.objects.filter(assignment__assessment=assessment)
        evaluated = [row for row in scorecards if row['status'] == 'evaluated']
        completed_submissions = submissions.filter(status=CodeSubmission.Status.COMPLETED)
        accepted_submissions = completed_submissions.filter(verdict=CodeSubmission.Verdict.ACCEPTED).count()
        average_percentage = (
            sum(row['percentage'] for row in evaluated) / len(evaluated)
            if evaluated else 0
        )
        average_marks = (
            sum(row['marks_obtained'] for row in evaluated) / len(evaluated)
            if evaluated else 0
        )

        return Response({
            'assessment_id': str(assessment.id),
            'assessment_title': assessment.title,
            'total_students': assignments.count(),
            'evaluated': len(evaluated),
            'pending': max(assignments.count() - len(evaluated), 0),
            'total_submissions': submissions.count(),
            'accepted_submissions': accepted_submissions,
            'acceptance_rate': round(accepted_submissions * 100 / completed_submissions.count(), 2)
            if completed_submissions.exists() else 0,
            'average_percentage': round(average_percentage, 2),
            'average_marks': round(average_marks, 2),
        })

    @action(detail=False, methods=['post'])
    def evaluate_assessment(self, request):
        """
        Evaluate all pending submissions for an assessment.

        POST /api/results/faculty/evaluate_assessment/?assessment_id=uuid
        """
        assessment_id = request.query_params.get('assessment_id')

        if not assessment_id:
            return Response(
                {'error': 'assessment_id query parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            assessment = Assessment.objects.get(id=assessment_id, created_by=request.user)
        except Assessment.DoesNotExist:
            return Response(
                {'error': 'Assessment not found or not authorized'},
                status=status.HTTP_404_NOT_FOUND
            )

        assignments = AssessmentAssignment.objects.filter(
            assessment=assessment,
            status=AssessmentAssignment.Status.SUBMITTED,
        ).select_related('assessment', 'student')
        evaluated = 0
        pending = 0
        for assignment in assignments:
            scorecard = SubmissionAggregationService.get_assignment_scorecard(assignment)
            if scorecard['status'] == 'evaluated':
                assignment.status = AssessmentAssignment.Status.GRADED
                assignment.save(update_fields=['status', 'updated_at'])
                evaluated += 1
            else:
                pending += 1

        logger.info("Faculty %s refreshed results for assessment %s", request.user.id, assessment_id)

        return Response({
            'message': 'Assessment result statuses updated.',
            'summary': {
                'assessment_id': str(assessment.id),
                'evaluated_assignments': evaluated,
                'pending_assignments': pending,
            },
        })

    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        """
        Export assessment results as CSV.

        GET /api/results/faculty/export_csv/?assessment_id=uuid
        """
        assessment_id = request.query_params.get('assessment_id')

        if not assessment_id:
            return Response(
                {'error': 'assessment_id query parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            assessment = Assessment.objects.get(id=assessment_id, created_by=request.user)
        except Assessment.DoesNotExist:
            return Response(
                {'error': 'Assessment not found or not authorized'},
                status=status.HTTP_404_NOT_FOUND
            )

        assignments = AssessmentAssignment.objects.filter(
            assessment=assessment
        ).select_related('assessment', 'student').order_by('student__last_name', 'student__first_name')
        question_links = assessment.assessment_questions.select_related('question').order_by('order')
        question_columns = {
            str(question.id): f"Q{question.order}: {question.question.title} ({question.marks})"
            for question in question_links
        }
        headers = [
            'Student Name',
            'Student Email',
            'Marks Obtained',
            'Total Marks',
            'Percentage',
            'Status',
        ] + list(question_columns.values())

        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        for assignment in assignments:
            row = SubmissionAggregationService.get_assignment_scorecard(assignment)
            csv_row = {
                'Student Name': assignment.student.get_full_name(),
                'Student Email': assignment.student.email,
                'Marks Obtained': row['marks_obtained'],
                'Total Marks': row['total_marks'],
                'Percentage': f"{row['percentage']:.2f}",
                'Status': row['status'].replace('_', ' ').title(),
            }
            for question_result in row['question_results']:
                column = question_columns.get(question_result['question_id'])
                if column:
                    csv_row[column] = question_result['marks_obtained']
            writer.writerow(csv_row)

        # Return as file
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="assessment_{assessment.id}_results.csv"'
        return response

    @action(detail=False, methods=['get'])
    def student_wise_results(self, request):
        """
        Get scorecards for the faculty member's assessments, optionally filtered by assessment.

        GET /api/results/faculty/student_wise_results/?assessment_id=uuid (optional)
        """
        assessment_id = request.query_params.get('assessment_id')

        assignments = AssessmentAssignment.objects.filter(
            assessment__created_by=request.user
        ).select_related('assessment', 'student')
        if assessment_id:
            try:
                Assessment.objects.get(id=assessment_id, created_by=request.user)
            except Assessment.DoesNotExist:
                return Response(
                    {'error': 'Assessment not found or not authorized'},
                    status=status.HTTP_404_NOT_FOUND
                )
            assignments = assignments.filter(assessment_id=assessment_id)
        assignments = assignments.order_by(
            'student__first_name',
            'student__last_name',
            'student__email',
            'id',
        )

        paginator = self.pagination_class()
        page_assignments = paginator.paginate_queryset(assignments, request)
        results = [
            SubmissionAggregationService.get_assignment_scorecard(assignment)
            for assignment in page_assignments
        ]
        return paginator.get_paginated_response(results)
