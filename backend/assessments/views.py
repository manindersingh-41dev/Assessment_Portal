"""
Views for Assessment Management.

Handles all assessment-related endpoints including creation, assignment, and student access.
"""

import math
import uuid
from datetime import timedelta

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import (
    Avg,
    Count,
    ExpressionWrapper,
    F,
    FloatField,
    Prefetch,
    Q,
    Value,
    prefetch_related_objects,
)
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import (
    Assessment, AssessmentAnswerDraft, AssessmentNotification, AssessmentQuestion,
    AssessmentAssignment, AssessmentIntegrityEvent,
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
    queue_assessment_publication_notifications,
    queue_notification_group,
)

MAX_INTEGRITY_WARNINGS = 3
CODE_INSERTION_WARNING_WORDS_PER_SECOND = 3
CODE_INSERTION_LOCK_WORDS_PER_SECOND = 6


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

        detail_prefetch = []
        if self.action == 'retrieve':
            detail_prefetch.append(
                Prefetch(
                    'assessment_questions',
                    queryset=AssessmentQuestion.objects.select_related('question'),
                )
            )

        if user.role == 'faculty' and user.is_faculty_approved:
            # Faculty sees their own assessments
            return Assessment.objects.filter(created_by=user).annotate(
                question_count=Count('assessment_questions', distinct=True),
                assignment_count=Count('assignments', distinct=True)
            ).prefetch_related(*detail_prefetch).order_by(
                F('published_at').desc(nulls_last=True), '-created_at'
            )
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
            ).prefetch_related(*detail_prefetch).order_by(
                F('published_at').desc(nulls_last=True), '-created_at'
            )

        return Assessment.objects.none()

    def get_permissions(self):
        """Set permissions based on action."""
        if self.action in ['create', 'publish', 'archive', 'reopen_window']:
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
        """Delete an assessment owned by the requesting faculty member."""
        instance = self.get_object()
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
            queue_assessment_publication_notifications(assessment.id)

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

    @action(detail=True, methods=['post'], url_path='reopen-window')
    @transaction.atomic
    def reopen_window(self, request, pk=None):
        """Reopen an expired assessment for all students for another 24 hours."""
        assessment = self.get_object()
        now = timezone.now()
        if assessment.end_time >= now:
            return Response(
                {'error': 'This assessment is still open.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_end = now + timedelta(hours=24)
        assessment.end_time = new_end
        assessment.status = Assessment.Status.ACTIVE
        assessment.is_published = True
        assessment.is_open_to_all_students = True
        if assessment.published_at is None:
            assessment.published_at = now
        assessment.save(update_fields=[
            'end_time',
            'status',
            'is_published',
            'is_open_to_all_students',
            'published_at',
            'updated_at',
        ])

        assignments = assessment.assignments.all()
        # A new global end time must override old personal deadlines too.
        assignments.update(due_at=new_end, updated_at=now)

        # Resume in-progress and completed attempts without deleting their
        # question submissions or drafts. Resetting started_at gives timed
        # attempts a fresh clock within the new 24-hour assessment window.
        resumable_statuses = [
            AssessmentAssignment.Status.STARTED,
            AssessmentAssignment.Status.SUBMITTED,
            AssessmentAssignment.Status.GRADED,
        ]
        assignments.filter(status__in=resumable_statuses).update(
            status=AssessmentAssignment.Status.STARTED,
            started_at=now,
            submitted_at=None,
            updated_at=now,
        )
        assignments.filter(
            status=AssessmentAssignment.Status.EXPIRED,
            started_at__isnull=False,
        ).update(
            status=AssessmentAssignment.Status.STARTED,
            started_at=now,
            submitted_at=None,
            updated_at=now,
        )
        # Expired assignments with no recorded start have no attempt to resume;
        # return them to the normal assigned state so the student can start.
        assignments.filter(
            status=AssessmentAssignment.Status.EXPIRED,
            started_at__isnull=True,
        ).update(
            status=AssessmentAssignment.Status.ASSIGNED,
            submitted_at=None,
            updated_at=now,
        )
        return Response({
            'message': 'Assessment reopened for all students for 24 hours.',
            'end_datetime': new_end,
            'is_published': True,
            'is_open_to_all_students': True,
        })

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
                'created_count': len(assignments),
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['get'])
    def assignments(self, request, pk=None):
        """Get all assignments for an assessment."""
        assessment = self.get_object()

        assignments = AssessmentAssignment.objects.filter(
            assessment=assessment
        ).select_related(
            'assessment', 'student', 'cheating_flag_cleared_by'
        ).prefetch_related(
            Prefetch(
                'notifications',
                queryset=AssessmentNotification.objects.filter(
                    kind=AssessmentNotification.Kind.ASSIGNED
                ),
            )
        ).order_by('-created_at')

        if request.query_params.get('student_ids_only') == '1':
            return Response({
                'student_ids': list(assignments.values_list('student_id', flat=True)),
            })

        paginator = AssessmentPagination()
        page = paginator.paginate_queryset(assignments, request, view=self)
        total_assignments = (
            paginator.page.paginator.count if page is not None else assignments.count()
        )
        serializer = AssessmentAssignmentSerializer(
            page if page is not None else assignments,
            many=True,
            context={'request': request}
        )
        paginated_data = (
            paginator.get_paginated_response(serializer.data).data
            if page is not None else {}
        )

        return Response(
            {
                'assessment_id': assessment.id,
                'assessment_title': assessment.title,
                'total_assignments': total_assignments,
                'next': paginated_data.get('next'),
                'previous': paginated_data.get('previous'),
                'assignments': paginated_data.get('results', serializer.data)
            }
        )

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get assessment statistics."""
        user = request.user
        now = timezone.now()
        assessments = Assessment.objects.filter(created_by=user)
        assessment_stats = assessments.aggregate(
            total=Count('id'),
            active=Count(
                'id',
                filter=Q(
                    is_published=True,
                    start_time__lte=now,
                    end_time__gte=now,
                ),
            ),
            upcoming=Count(
                'id',
                filter=Q(is_published=True, start_time__gt=now),
            ),
            completed=Count(
                'id',
                filter=Q(is_published=True, end_time__lt=now),
            ),
        )

        assignments = AssessmentAssignment.objects.filter(assessment__created_by=user)
        assignment_stats = assignments.aggregate(
            total=Count('id'),
            completed=Count(
                'id',
                filter=Q(
                    status__in=[
                        AssessmentAssignment.Status.SUBMITTED,
                        AssessmentAssignment.Status.GRADED,
                    ]
                ),
            ),
            pending=Count(
                'id',
                filter=Q(
                    status__in=[
                        AssessmentAssignment.Status.ASSIGNED,
                        AssessmentAssignment.Status.STARTED,
                    ]
                ),
            ),
            students=Count('student_id', distinct=True),
        )

        total_questions = AssessmentQuestion.objects.filter(
            assessment__created_by=user
        ).count()

        submissions = CodeSubmission.objects.filter(
            assignment__assessment__created_by=user
        )
        score_expression = ExpressionWrapper(
            F('marks_obtained') * Value(100.0) / F('question__marks'),
            output_field=FloatField(),
        )
        submission_stats = submissions.aggregate(
            total=Count('id'),
            completed=Count(
                'id', filter=Q(status=CodeSubmission.Status.COMPLETED)
            ),
            accepted=Count(
                'id',
                filter=Q(
                    status=CodeSubmission.Status.COMPLETED,
                    verdict=CodeSubmission.Verdict.ACCEPTED,
                ),
            ),
            average_score=Avg(
                score_expression,
                filter=Q(
                    status=CodeSubmission.Status.COMPLETED,
                    marks_obtained__isnull=False,
                    question__marks__gt=0,
                ),
            ),
        )
        completed_count = submission_stats['completed'] or 0
        acceptance_rate = (
            submission_stats['accepted'] * 100 / completed_count
            if completed_count else 0
        )

        data = {
            'total_assessments': assessment_stats['total'],
            'active_assessments': assessment_stats['active'],
            'completed_assessments': assessment_stats['completed'],
            'upcoming_assessments': assessment_stats['upcoming'],
            'total_assignments': assignment_stats['total'],
            'completed_assignments': assignment_stats['completed'],
            'pending_assignments': assignment_stats['pending'],
            'total_students': assignment_stats['students'],
            'total_questions': total_questions,
            'total_submissions': submission_stats['total'],
            'average_score': submission_stats['average_score'] or 0,
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
            if self.action in ('clear_cheating_flag', 'clear_integrity_warnings'):
                return AssessmentAssignment.objects.select_related(
                    'assessment', 'student', 'cheating_flag_cleared_by'
                )
            # Faculty sees assignments for their assessments
            return AssessmentAssignment.objects.filter(
                assessment__created_by=user
            ).select_related(
                'assessment', 'student', 'cheating_flag_cleared_by'
            ).prefetch_related(
                Prefetch(
                    'notifications',
                    queryset=AssessmentNotification.objects.filter(
                        kind=AssessmentNotification.Kind.ASSIGNED
                    ),
                )
            ).order_by('-created_at')

        elif user.role == 'student':
            # Materialize assignments for open assessments on demand so the
            # existing attempt and progress APIs work for current and future students.
            if self.action == 'list':
                AssignmentService.ensure_open_assessment_assignments(user)
            return AssessmentAssignment.objects.filter(
                student=user
            ).select_related('assessment').order_by('-created_at')

        return AssessmentAssignment.objects.none()

    @action(detail=False, methods=['get'], url_path='locked')
    def locked_assignments(self, request):
        """List active coding locks for approved faculty review."""
        if request.user.role != 'faculty' or not request.user.is_faculty_approved:
            return Response(
                {'error': 'Only approved faculty can view coding locks.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        assignments = AssessmentAssignment.objects.filter(
            is_flagged_cheating=True,
        ).select_related(
            'assessment', 'student', 'cheating_flag_cleared_by'
        ).prefetch_related(
            Prefetch(
                'notifications',
                queryset=AssessmentNotification.objects.filter(
                    kind=AssessmentNotification.Kind.ASSIGNED
                ),
            )
        ).order_by('-cheating_flagged_at', '-created_at')
        page = self.paginate_queryset(assignments)
        serializer = self.get_serializer(
            page if page is not None else assignments,
            many=True,
            context={'request': request},
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='flag-status')
    def flag_status(self, request, pk=None):
        """Return only the fields needed to synchronize a student coding lock."""
        assignment = self.get_object()
        if request.user.role != 'student' or assignment.student_id != request.user.id:
            return Response(
                {'error': 'Only the assigned student can view this attempt status.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response({
            'is_flagged_cheating': assignment.is_flagged_cheating,
            'cheating_flag_reason': assignment.cheating_flag_reason,
            'cheating_flag_cleared_at': assignment.cheating_flag_cleared_at,
            'integrity_warning_count': assignment.integrity_warning_count,
        })

    @action(detail=True, methods=['post'], url_path='integrity-event')
    def integrity_event(self, request, pk=None):
        """Record page-level or code-speed integrity events for a student."""
        return self._record_integrity_event(request)

    @action(detail=True, methods=['post'], url_path='flag-cheating')
    def flag_cheating(self, request, pk=None):
        """Compatibility route for older clients recording a speed breach."""
        return self._record_integrity_event(request)

    def _record_integrity_event(self, request):
        assignment = self.get_object()
        if request.user.role != 'student' or assignment.student_id != request.user.id:
            return Response(
                {'error': 'Only the assigned student can report this integrity event.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        event_type = request.data.get('reason')
        if event_type not in AssessmentIntegrityEvent.EventType.values:
            return Response(
                {'error': 'Unsupported integrity flag reason.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        speed_wpm = None
        words_per_second = None
        sustained_ms = None
        if event_type == AssessmentIntegrityEvent.EventType.SPEED:
            try:
                speed_wpm = float(request.data.get('speed_wpm'))
            except (TypeError, ValueError):
                speed_wpm = float('nan')
            try:
                sustained_ms = int(request.data.get('sustained_ms'))
            except (TypeError, ValueError):
                sustained_ms = 0
        if event_type in (
            AssessmentIntegrityEvent.EventType.RAPID_CODE_INSERTION,
            AssessmentIntegrityEvent.EventType.BULK_CODE_INSERTION,
        ):
            try:
                words_per_second = float(request.data.get('words_per_second'))
            except (TypeError, ValueError):
                words_per_second = float('nan')
            if not math.isfinite(words_per_second) or words_per_second <= CODE_INSERTION_WARNING_WORDS_PER_SECOND:
                return Response(
                    {'error': 'Code insertion must exceed 3 words per second.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if (
                event_type == AssessmentIntegrityEvent.EventType.BULK_CODE_INSERTION
                and words_per_second <= CODE_INSERTION_LOCK_WORDS_PER_SECOND
            ):
                return Response(
                    {'error': 'An immediate coding lock requires more than 6 words per second.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if (
                event_type == AssessmentIntegrityEvent.EventType.RAPID_CODE_INSERTION
                and words_per_second > CODE_INSERTION_LOCK_WORDS_PER_SECOND
            ):
                event_type = AssessmentIntegrityEvent.EventType.BULK_CODE_INSERTION
        submitted_event_id = request.data.get('event_id')
        if submitted_event_id:
            try:
                event_id = uuid.UUID(str(submitted_event_id))
            except (AttributeError, TypeError, ValueError):
                return Response(
                    {'error': 'A valid integrity-event ID is required.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            event_id = uuid.uuid4()
        if event_type == AssessmentIntegrityEvent.EventType.FULLSCREEN_EXIT:
            return Response({
                'event_id': str(event_id),
                'event_type': event_type,
                'outcome': None,
                'locked': assignment.is_flagged_cheating,
                'ignored': True,
                'integrity_warning_count': assignment.integrity_warning_count,
                'assignment': AssessmentAssignmentSerializer(
                    assignment,
                    context={'request': request},
                ).data,
            })
        if event_type == AssessmentIntegrityEvent.EventType.SPEED:
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

        with transaction.atomic():
            assignment = (
                AssessmentAssignment.objects.select_for_update()
                .select_related('assessment', 'student')
                .get(pk=assignment.pk)
            )
            student = assignment.student
            breach_event = AssessmentIntegrityEvent.objects.filter(
                student=student,
                event_id=event_id,
            ).first()

            if breach_event is None:
                if assignment.status != AssessmentAssignment.Status.STARTED:
                    return Response(
                        {'error': 'Only an in-progress assessment can report an integrity event.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                immediate_code_insertion_lock = (
                    event_type == AssessmentIntegrityEvent.EventType.BULK_CODE_INSERTION
                )
                if (
                    immediate_code_insertion_lock
                    or assignment.is_flagged_cheating
                    or assignment.integrity_warning_count >= MAX_INTEGRITY_WARNINGS
                ):
                    outcome = AssessmentIntegrityEvent.Outcome.LOCKED
                    if not assignment.is_flagged_cheating:
                        assignment.is_flagged_cheating = True
                        assignment.cheating_flag_reason = event_type
                        assignment.cheating_flag_speed_wpm = speed_wpm
                        assignment.cheating_flag_words_per_second = words_per_second
                        assignment.cheating_flag_sustained_ms = sustained_ms
                        assignment.cheating_flagged_at = timezone.now()
                        assignment.cheating_flag_cleared_at = None
                        assignment.cheating_flag_cleared_by = None
                        assignment.save(update_fields=[
                            'is_flagged_cheating',
                            'cheating_flag_reason',
                            'cheating_flag_speed_wpm',
                            'cheating_flag_words_per_second',
                            'cheating_flag_sustained_ms',
                            'cheating_flagged_at',
                            'cheating_flag_cleared_at',
                            'cheating_flag_cleared_by',
                            'updated_at',
                        ])
                else:
                    assignment.integrity_warning_count += 1
                    assignment.save(update_fields=['integrity_warning_count', 'updated_at'])
                    outcome = AssessmentIntegrityEvent.Outcome.WARNING

                breach_event = AssessmentIntegrityEvent.objects.create(
                    student=student,
                    assignment=assignment,
                    event_id=event_id,
                    event_type=event_type,
                    speed_wpm=speed_wpm,
                    words_per_second=words_per_second,
                    sustained_ms=sustained_ms,
                    outcome=outcome,
                )

            assignment.student = student
            warning_count = assignment.integrity_warning_count
            event_type = breach_event.event_type
            locked = breach_event.outcome == AssessmentIntegrityEvent.Outcome.LOCKED

        if locked:
            if event_type == AssessmentIntegrityEvent.EventType.BULK_CODE_INSERTION:
                message = (
                    'Code insertion exceeded 6 words per second. '
                    'This coding window is locked immediately.'
                )
            else:
                message = (
                    f'This coding window is locked after {MAX_INTEGRITY_WARNINGS} persistent '
                    'integrity warnings and another policy event.'
                )
        else:
            event_messages = {
                AssessmentIntegrityEvent.EventType.SPEED:
                    'Code-writing speed stayed above the 85 WPM limit for at least three seconds.',
                AssessmentIntegrityEvent.EventType.RAPID_CODE_INSERTION:
                    f'The code editor received more than {CODE_INSERTION_WARNING_WORDS_PER_SECOND} '
                    'words per second.',
                AssessmentIntegrityEvent.EventType.BULK_CODE_INSERTION:
                    'Code insertion exceeded 6 words per second.',
                AssessmentIntegrityEvent.EventType.TAB_HIDDEN:
                    'The assessment tab became hidden or you switched away from it.',
                AssessmentIntegrityEvent.EventType.WINDOW_BLUR:
                    'The assessment window lost focus.',
                AssessmentIntegrityEvent.EventType.FULLSCREEN_EXIT:
                    'You exited the assessment fullscreen window.',
            }
            warning_kind = (
                f'Final warning ({warning_count} of {MAX_INTEGRITY_WARNINGS}). '
                'The next assessment-integrity event will lock this coding window.'
                if warning_count >= MAX_INTEGRITY_WARNINGS
                else f'Integrity warning ({warning_count} of {MAX_INTEGRITY_WARNINGS}). '
                f'After {MAX_INTEGRITY_WARNINGS} warnings, the next event will lock this coding window.'
            )
            message = (
                f'{event_messages[event_type]} {warning_kind} '
                'Do not use AI or scripts to write code. '
                'Do not try to paste code using any alternative method. '
            )

        return Response({
            'event_id': str(event_id),
            'event_type': event_type,
            'outcome': breach_event.outcome,
            'locked': locked,
            'integrity_warning_count': warning_count,
            'message': message,
            'assignment': AssessmentAssignmentSerializer(
                assignment,
                context={'request': request},
            ).data,
        })

    @action(detail=True, methods=['post'], url_path='clear-cheating-flag')
    def clear_cheating_flag(self, request, pk=None):
        """Let any approved faculty member remove a coding lock."""
        if request.user.role != 'faculty' or not request.user.is_faculty_approved:
            return Response(
                {'error': 'Only approved faculty can remove a cheating lock.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        visible_assignment = self.get_object()
        lock_cleared = False
        with transaction.atomic():
            assignment = AssessmentAssignment.objects.select_for_update().select_related(
                'assessment', 'student', 'cheating_flag_cleared_by'
            ).get(pk=visible_assignment.pk)

            if assignment.is_flagged_cheating:
                lock_cleared = True
                assignment.is_flagged_cheating = False
                assignment.cheating_flag_cleared_at = timezone.now()
                assignment.cheating_flag_cleared_by = request.user
                assignment.save(update_fields=[
                    'is_flagged_cheating',
                    'cheating_flag_cleared_at',
                    'cheating_flag_cleared_by',
                    'updated_at',
                ])
                if assignment.integrity_warning_count:
                    assignment.integrity_warning_count = 0
                    assignment.save(update_fields=['integrity_warning_count', 'updated_at'])

        return Response({
            'message': (
                'The coding lock has been removed and this assessment warning count reset to zero.'
                if lock_cleared
                else 'No active coding lock was found.'
            ),
            'assignment': AssessmentAssignmentSerializer(
                assignment,
                context={'request': request},
            ).data,
        })

    @action(detail=True, methods=['post'], url_path='clear-integrity-warnings')
    def clear_integrity_warnings(self, request, pk=None):
        """Reset an assignment's warning count without changing its lock state."""
        if request.user.role != 'faculty' or not request.user.is_faculty_approved:
            return Response(
                {'error': 'Only approved faculty can clear integrity warnings.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        assignment = self.get_object()
        with transaction.atomic():
            assignment = AssessmentAssignment.objects.select_for_update().select_related(
                'assessment', 'student', 'cheating_flag_cleared_by'
            ).get(pk=assignment.pk)
            assignment.integrity_warning_count = 0
            assignment.save(update_fields=['integrity_warning_count', 'updated_at'])

        return Response({
            'message': 'Integrity warning count cleared for this assessment.',
            'assignment': AssessmentAssignmentSerializer(
                assignment,
                context={'request': request},
            ).data,
        })

    @action(detail=True, methods=['post'], url_path='reopen')
    def reopen(self, request, pk=None):
        """Reopen a submitted assignment so the student can continue it."""
        if request.user.role != 'faculty' or not request.user.is_faculty_approved:
            return Response(
                {'error': 'Only approved faculty can reopen an assessment.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        assignment = self.get_object()
        if assignment.assessment.created_by_id != request.user.id:
            return Response(
                {'error': 'You can only reopen assignments for your assessments.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        now = timezone.now()
        if assignment.assessment.end_time <= now:
            return Response(
                {'error': 'The assessment window is closed. Reopen the assessment window to make it available to all students.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if assignment.status not in [
            AssessmentAssignment.Status.SUBMITTED,
            AssessmentAssignment.Status.GRADED,
        ]:
            return Response(
                {'error': 'Only submitted assignments can be reopened.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assignment.status = AssessmentAssignment.Status.STARTED
        assignment.started_at = now
        assignment.submitted_at = None
        assignment.due_at = assignment.assessment.end_time
        assignment.save(update_fields=[
            'status',
            'started_at',
            'submitted_at',
            'due_at',
            'updated_at',
        ])
        return Response({
            'message': 'Assessment reopened for the student.',
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

        batch_notification_ids = list(AssessmentNotification.objects.filter(
            email_batch_id=notification.email_batch_id,
            kind=notification.kind,
            status__in=[
                AssessmentNotification.Status.FAILED,
                AssessmentNotification.Status.PENDING,
            ],
        ).values_list('id', flat=True))
        retry_time = timezone.now()
        with transaction.atomic():
            AssessmentNotification.objects.filter(
                id__in=batch_notification_ids
            ).update(
                status=AssessmentNotification.Status.PENDING,
                scheduled_for=retry_time,
                attempts=0,
                last_error='',
                updated_at=retry_time,
            )
            batch_notifications = list(
                AssessmentNotification.objects.filter(id__in=batch_notification_ids)
            )
            queue_notification_group(
                batch_notifications,
                notification.email_batch_id,
            )
        return Response(
            {'message': 'Email queued for delivery.', 'status': AssessmentNotification.Status.QUEUED},
            status=status.HTTP_202_ACCEPTED,
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
