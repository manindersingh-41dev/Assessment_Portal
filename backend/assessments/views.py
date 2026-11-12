"""
Views for Assessment Management.

Handles all assessment-related endpoints including creation, assignment, and student access.
"""

import math

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Count, F, Q, prefetch_related_objects
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404

from .models import (
    Assessment, AssessmentAnswerDraft, AssessmentNotification, AssessmentQuestion,
    AssessmentAssignment
)
from submissions.models import CodeSubmission
from submissions.services import SubmissionService
from .serializers import (
    AssessmentSerializer,
    AssessmentCreateSerializer,
    AssessmentUpdateSerializer,
    AssessmentDetailSerializer,
    AssessmentAssignmentSerializer,
    AssessmentAssignmentCreateSerializer,
    AssessmentAnswerDraftSerializer,
    AssessmentAnswerDraftWriteSerializer,
    AssessmentQuestionSerializer,
)
from .permissions import (
    IsApprovedFaculty, IsAssessmentCreator, CanAssignAssessment,
    IsStudent
)
from .services import AssessmentService, AssignmentService
from .notifications import (
    send_assignment_notifications,
    send_assessment_publication_notifications,
    send_notification_group,
)


class AssessmentPagination(PageNumberPagination):
    """Pagination for assessments."""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class AssessmentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing assessments."""

    queryset = Assessment.objects.all()
    pagination_class = AssessmentPagination
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return AssessmentCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AssessmentUpdateSerializer
        elif self.action == 'retrieve':
            return AssessmentDetailSerializer
        elif self.action == 'list':
            return AssessmentSerializer
        return AssessmentDetailSerializer

    def get_queryset(self):
        """Filter assessments based on user role."""
        user = self.request.user

        if user.role == 'faculty' and user.is_faculty_approved:
            # Faculty sees their own assessments
            return Assessment.objects.filter(created_by=user).annotate(
                question_count=Count('assessment_questions', distinct=True),
                assignment_count=Count('assignments', distinct=True)
            ).order_by(F('published_at').desc(nulls_last=True), '-created_at')
        elif user.role == 'student':
            # Published open assessments are available to all students; targeted
            # assessments remain visible only to students with an assignment.
            return Assessment.objects.filter(
                is_published=True
            ).filter(
                Q(assignments__student=user) | Q(is_open_to_all_students=True)
            ).distinct().annotate(
                question_count=Count('assessment_questions', distinct=True),
                assignment_count=Count('assignments', distinct=True)
            ).order_by(F('published_at').desc(nulls_last=True), '-created_at')

        return Assessment.objects.none()

    def get_permissions(self):
        """Set permissions based on action."""
        if self.action in ['create', 'publish', 'archive']:
            permission_classes = [IsApprovedFaculty]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAssessmentCreator]
        elif self.action in ['assign', 'assignments', 'statistics']:
            permission_classes = [IsApprovedFaculty]
        else:
            permission_classes = [permissions.IsAuthenticated]

        return [permission() for permission in permission_classes]

    def create(self, request, *args, **kwargs):
        """Create new assessment."""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(
            {
                'message': 'Assessment created successfully',
                'assessment': AssessmentDetailSerializer(
                    serializer.instance,
                    context={'request': request}
                ).data
            },
            status=status.HTTP_201_CREATED
        )

    def perform_create(self, serializer):
        """Save assessment with created_by."""
        serializer.save(created_by=self.request.user)

    def update(self, request, *args, **kwargs):
        """Update assessment."""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(
            {
                'message': 'Assessment updated successfully',
                'assessment': AssessmentDetailSerializer(
                    serializer.instance,
                    context={'request': request}
                ).data
            }
        )

    def destroy(self, request, *args, **kwargs):
        """Delete assessment (only draft)."""
        instance = self.get_object()

        if instance.status != Assessment.Status.DRAFT:
            return Response(
                {'error': 'Only draft assessments can be deleted'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if instance.assignments.exists():
            return Response(
                {'error': 'Cannot delete assessment with active assignments'},
                status=status.HTTP_400_BAD_REQUEST
            )

        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish assessment."""
        assessment = self.get_object()
        was_published = assessment.is_published

        assessment.is_published = True
        assessment.status = Assessment.Status.ACTIVE
        if assessment.published_at is None:
            assessment.published_at = timezone.now()
        assessment.save(update_fields=[
            'is_published',
            'status',
            'published_at',
            'updated_at',
        ])
        if not was_published:
            send_assessment_publication_notifications(assessment)

        return Response(
            {
                'message': 'Assessment published successfully',
                'assessment': AssessmentDetailSerializer(
                    assessment,
                    context={'request': request}
                ).data
            }
        )

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive assessment."""
        assessment = self.get_object()

        assessment.status = Assessment.Status.ARCHIVED
        assessment.save()

        return Response(
            {
                'message': 'Assessment archived successfully',
                'assessment': AssessmentDetailSerializer(
                    assessment,
                    context={'request': request}
                ).data
            }
        )

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Assign assessment to students."""
        assessment = self.get_object()

        if not assessment.is_published:
            return Response(
                {'error': 'Assessment must be published before assignment'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = AssessmentAssignmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = AssignmentService()
        assignments = service.create_assignments(
            assessment=assessment,
            student_ids=serializer.validated_data.get('student_ids', []),
            batch_ids=serializer.validated_data.get('batch_ids', []),
            deadline=serializer.validated_data.get('deadline')
        )
        send_assignment_notifications(assignments)
        prefetch_related_objects(assignments, 'notifications')

        return Response(
            {
                'message': f'{len(assignments)} assignment(s) created successfully',
                'assignments': AssessmentAssignmentSerializer(
                    assignments,
                    many=True,
                    context={'request': request}
                ).data
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['get'])
    def assignments(self, request, pk=None):
        """Get all assignments for an assessment."""
        assessment = self.get_object()

        assignments = AssessmentAssignment.objects.filter(
            assessment=assessment
        ).prefetch_related('notifications').order_by('-created_at')

        serializer = AssessmentAssignmentSerializer(
            assignments,
            many=True,
            context={'request': request}
        )

        return Response(
            {
                'assessment_id': assessment.id,
                'assessment_title': assessment.title,
                'total_assignments': assignments.count(),
                'assignments': serializer.data
            }
        )

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get assessment statistics."""
        user = request.user
        assessments = self.get_queryset()

        now = timezone.now()
        published_assessments = assessments.filter(is_published=True)
        active = published_assessments.filter(start_time__lte=now, end_time__gte=now).count()
        upcoming = published_assessments.filter(start_time__gt=now).count()
        completed = published_assessments.filter(end_time__lt=now).count()

        # Assignment statistics
        assignments = AssessmentAssignment.objects.filter(assessment__created_by=user)
        completed_assignments = assignments.filter(
            status__in=[AssessmentAssignment.Status.SUBMITTED, AssessmentAssignment.Status.GRADED]
        ).count()
        pending_assignments = assignments.filter(
            status__in=[AssessmentAssignment.Status.ASSIGNED, AssessmentAssignment.Status.STARTED]
        ).count()
        submissions = CodeSubmission.objects.filter(assignment__assessment__created_by=user)
        evaluated_submissions = submissions.filter(status=CodeSubmission.Status.COMPLETED)
        completed_rows = evaluated_submissions.values_list(
            'marks_obtained', 'question__marks'
        )
        percentages = [
            marks * 100 / question_marks
            for marks, question_marks in completed_rows
            if marks is not None and question_marks
        ]
        avg_score = sum(percentages) / len(percentages) if percentages else 0
        accepted_count = evaluated_submissions.filter(
            verdict=CodeSubmission.Verdict.ACCEPTED
        ).count()
        acceptance_rate = accepted_count / evaluated_submissions.count() * 100 if evaluated_submissions.exists() else 0

        data = {
            'total_assessments': assessments.count(),
            'active_assessments': active,
            'completed_assessments': completed,
            'upcoming_assessments': upcoming,
            'total_assignments': assignments.count(),
            'completed_assignments': completed_assignments,
            'pending_assignments': pending_assignments,
            'total_students': assignments.values('student_id').distinct().count(),
            'total_questions': sum(assessment.assessment_questions.count() for assessment in assessments),
            'total_submissions': submissions.count(),
            'average_score': avg_score,
            'acceptance_rate': acceptance_rate,
        }

        return Response(data)

    @action(detail=False, methods=['get'])
    def my_assessments(self, request):
        """Get student's assessments."""
        if request.user.role != 'student':
            return Response(
                {'error': 'Only students can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )

        assessments = self.get_queryset()
        page = self.paginate_queryset(assessments)

        if page is not None:
            serializer = AssessmentSerializer(
                page,
                many=True,
                context={'request': request, 'student': request.user}
            )
            return self.get_paginated_response(serializer.data)

        serializer = AssessmentSerializer(
            assessments,
            many=True,
            context={'request': request, 'student': request.user}
        )
        return Response(serializer.data)


class AssessmentAssignmentViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing assessment assignments."""

    serializer_class = AssessmentAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = AssessmentPagination

    def get_queryset(self):
        """Filter assignments based on user role."""
        user = self.request.user

        if user.role == 'faculty' and user.is_faculty_approved:
            # Faculty sees assignments for their assessments
            return AssessmentAssignment.objects.filter(
                assessment__created_by=user
            ).prefetch_related('notifications').order_by('-created_at')

        elif user.role == 'student':
            # Materialize assignments for open assessments on demand so the
            # existing attempt and progress APIs work for current and future students.
            AssignmentService.ensure_open_assessment_assignments(user)
            return AssessmentAssignment.objects.filter(
                student=user
            ).select_related('assessment').order_by('-created_at')

        return AssessmentAssignment.objects.none()

    @action(detail=True, methods=['post'], url_path='flag-cheating')
    def flag_cheating(self, request, pk=None):
        """Persist a high code-writing-speed integrity flag for the student."""
        assignment = self.get_object()
        if request.user.role != 'student' or assignment.student_id != request.user.id:
            return Response(
                {'error': 'Only the assigned student can flag this attempt.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if assignment.status != AssessmentAssignment.Status.STARTED:
            return Response(
                {'error': 'Only an in-progress assessment can be flagged.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if request.data.get('reason') != 'high_code_writing_speed':
            return Response(
                {'error': 'Unsupported integrity flag reason.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            speed_wpm = float(request.data.get('speed_wpm'))
        except (TypeError, ValueError):
            speed_wpm = float('nan')
        try:
            sustained_ms = int(request.data.get('sustained_ms'))
        except (TypeError, ValueError):
            sustained_ms = 0
        if not math.isfinite(speed_wpm) or speed_wpm <= 85:
            return Response(
                {'error': 'A code-writing speed above 85 WPM is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if sustained_ms < 3_000:
            return Response(
                {'error': 'The speed must remain above the limit for at least three seconds.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            not assignment.is_flagged_cheating
            or speed_wpm > (assignment.cheating_flag_speed_wpm or 0)
        ):
            newly_flagged = not assignment.is_flagged_cheating
            assignment.is_flagged_cheating = True
            assignment.cheating_flag_reason = 'high_code_writing_speed'
            assignment.cheating_flag_speed_wpm = speed_wpm
            assignment.cheating_flag_sustained_ms = sustained_ms
            if newly_flagged:
                assignment.cheating_flagged_at = timezone.now()
                assignment.cheating_flag_cleared_at = None
                assignment.cheating_flag_cleared_by = None
            assignment.save(update_fields=[
                'is_flagged_cheating',
                'cheating_flag_reason',
                'cheating_flag_speed_wpm',
                'cheating_flag_sustained_ms',
                'cheating_flagged_at',
                'cheating_flag_cleared_at',
                'cheating_flag_cleared_by',
                'updated_at',
            ])

        return Response({
            'message': 'This attempt has been flagged for review.',
            'assignment': AssessmentAssignmentSerializer(
                assignment,
                context={'request': request},
            ).data,
        })

    @action(detail=True, methods=['post'], url_path='clear-cheating-flag')
    def clear_cheating_flag(self, request, pk=None):
        """Let the owning faculty member remove an accidental coding lock."""
        if request.user.role != 'faculty' or not request.user.is_faculty_approved:
            return Response(
                {'error': 'Only approved faculty can remove a cheating lock.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        assignment = self.get_object()
        if assignment.assessment.created_by_id != request.user.id:
            return Response(
                {'error': 'You can only remove locks on your assessments.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if assignment.is_flagged_cheating:
            assignment.is_flagged_cheating = False
            assignment.cheating_flag_cleared_at = timezone.now()
            assignment.cheating_flag_cleared_by = request.user
            assignment.save(update_fields=[
                'is_flagged_cheating',
                'cheating_flag_cleared_at',
                'cheating_flag_cleared_by',
                'updated_at',
            ])

        return Response({
            'message': 'The coding lock has been removed.',
            'assignment': AssessmentAssignmentSerializer(
                assignment,
                context={'request': request},
            ).data,
        })

    @action(
        detail=True,
        methods=['post'],
        url_path=r'notifications/(?P<notification_id>[0-9a-f-]+)/retry',
    )
    def retry_notification(self, request, pk=None, notification_id=None):
        """Retry a failed assignment email for its owning faculty member."""
        if request.user.role != 'faculty' or not request.user.is_faculty_approved:
            return Response(
                {'error': 'Only approved faculty can retry assessment emails.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        assignment = self.get_object()
        if assignment.assessment.created_by_id != request.user.id:
            return Response(
                {'error': 'You can only retry emails for your assessments.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        notification = get_object_or_404(
            AssessmentNotification,
            id=notification_id,
            assignment=assignment,
        )
        if notification.kind != AssessmentNotification.Kind.ASSIGNED:
            return Response(
                {'error': 'Scheduled reminders are disabled.'},
                status=status.HTTP_410_GONE,
            )
        if notification.status != AssessmentNotification.Status.FAILED:
            return Response(
                {'error': 'Only failed emails can be retried.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        batch_notifications = AssessmentNotification.objects.filter(
            email_batch_id=notification.email_batch_id,
            kind=notification.kind,
            status__in=[
                AssessmentNotification.Status.FAILED,
                AssessmentNotification.Status.PENDING,
            ],
        )
        batch_notifications.update(
            status=AssessmentNotification.Status.PENDING,
            scheduled_for=timezone.now(),
            attempts=0,
            last_error='',
            updated_at=timezone.now(),
        )
        batch_notifications = list(batch_notifications)
        send_notification_group(batch_notifications, notification.email_batch_id)
        notification.refresh_from_db(fields=['status', 'last_error'])
        if notification.status == AssessmentNotification.Status.FAILED:
            return Response(
                {'error': notification.last_error or 'The email could not be sent.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(
            {'message': 'Email sent.', 'status': notification.status},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['get', 'put'], url_path='drafts')
    def drafts(self, request, pk=None):
        """Read or autosave a student's in-progress question drafts."""
        assignment = self.get_object()
        if assignment.student_id != request.user.id:
            return Response(
                {'error': 'Only the assigned student can access these drafts.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if request.method == 'GET':
            drafts = AssessmentAnswerDraft.objects.filter(
                assignment=assignment,
            ).select_related('assessment_question')
            return Response({
                'drafts': AssessmentAnswerDraftSerializer(drafts, many=True).data,
            })

        if assignment.status != AssessmentAssignment.Status.STARTED:
            return Response(
                {'error': 'Drafts can only be saved while the assessment is in progress.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AssessmentAnswerDraftWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        question = get_object_or_404(
            AssessmentQuestion,
            id=serializer.validated_data['question_id'],
            assessment_id=assignment.assessment_id,
        )
        draft, _ = AssessmentAnswerDraft.objects.update_or_create(
            assignment=assignment,
            assessment_question=question,
            defaults={'source_code': serializer.validated_data['source_code']},
        )
        return Response(AssessmentAnswerDraftSerializer(draft).data)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Mark assignment as started."""
        assignment = self.get_object()

        if assignment.student != request.user:
            return Response(
                {'error': 'Cannot start another student\'s assignment'},
                status=status.HTTP_403_FORBIDDEN
            )

        if not assignment.can_start():
            return Response(
                {'error': 'Cannot start this assignment at this time'},
                status=status.HTTP_400_BAD_REQUEST
            )

        assignment.mark_started()
        return Response(
            {
                'message': 'Assignment started successfully',
                'assignment': AssessmentAssignmentSerializer(
                    assignment,
                    context={'request': request}
                ).data
            }
        )

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Mark assignment as submitted."""
        visible_assignment = self.get_object()
        with transaction.atomic():
            assignment = AssessmentAssignment.objects.select_for_update().select_related(
                'assessment'
            ).get(id=visible_assignment.id)

            if assignment.student != request.user:
                return Response(
                    {'error': 'Cannot submit another student\'s assignment'},
                    status=status.HTTP_403_FORBIDDEN
                )

            if assignment.status != AssessmentAssignment.Status.STARTED:
                return Response(
                    {'error': 'Assignment must be in STARTED status to submit'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            assignment.mark_submitted()
            SubmissionService.evaluate_assignment_submissions(assignment)

        return Response(
            {
                'message': 'Assignment submitted successfully',
                'assignment': AssessmentAssignmentSerializer(
                    assignment,
                    context={'request': request}
                ).data
            }
        )

    @action(detail=True, methods=['post'])
    def evaluate(self, request, pk=None):
        """Evaluate assignment (faculty only)."""
        assignment = self.get_object()

        if assignment.assessment.created_by != request.user:
            return Response(
                {'error': 'Only assessment creator can evaluate'},
                status=status.HTTP_403_FORBIDDEN
            )

        marks_obtained = request.data.get('marks_obtained')
        feedback = request.data.get('feedback', '')

        if marks_obtained is None:
            return Response(
                {'error': 'marks_obtained is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            marks_obtained = int(marks_obtained)
            if marks_obtained < 0 or marks_obtained > assignment.assessment.total_marks:
                raise ValueError('Marks out of range')
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid marks value'},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = AssignmentService()
        service.evaluate_assignment(
            assignment=assignment,
            marks_obtained=marks_obtained,
            feedback=feedback
        )

        return Response(
            {
                'message': 'Assignment evaluated successfully',
                'assignment': AssessmentAssignmentSerializer(
                    assignment,
                    context={'request': request}
                ).data
            }
        )

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending assignments for faculty."""
        user = request.user

        if user.role != 'faculty':
            return Response(
                {'error': 'Only faculty can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )

        assignments = AssessmentAssignment.objects.filter(
            assessment__created_by=user,
            status=AssessmentAssignment.Status.SUBMITTED
        ).order_by('-submitted_at')

        page = self.paginate_queryset(assignments)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(assignments, many=True, context={'request': request})
        return Response(serializer.data)
