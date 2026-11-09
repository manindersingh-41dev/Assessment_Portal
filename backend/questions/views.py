"""
Views for Question Bank Management.

Provides endpoints for faculty to create, update, delete, and manage questions.
Implements proper permission checks and business logic validation.
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q, Avg
from django.db import transaction

from .models import Question, TestCase
from .serializers import (
    QuestionCreateSerializer,
    QuestionUpdateSerializer,
    QuestionDetailSerializer,
    QuestionListSerializer,
    QuestionPreviewSerializer,
    QuestionStatusChangeSerializer,
    TestCaseSerializer,
    TestCaseDetailSerializer,
    TestCaseCreateSerializer,
    TestCaseUpdateSerializer,
    QuestionStatsSerializer,
)
from .services import QuestionService, TestCaseService
from users.permissions import IsFaculty, IsApprovedFaculty


class QuestionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing programming questions.

    Faculty can create, update, delete, and manage questions.
    Students can only view active questions if included in assessments.
    """

    queryset = Question.objects.all()
    permission_classes = [IsAuthenticated, IsApprovedFaculty]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['difficulty', 'status', 'topic']
    search_fields = ['title', 'description', 'topic']
    ordering_fields = ['created_at', 'title', 'difficulty', 'total_marks']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return QuestionCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return QuestionUpdateSerializer
        elif self.action == 'preview':
            return QuestionPreviewSerializer
        elif self.action == 'retrieve':
            return QuestionDetailSerializer
        elif self.action == 'list':
            return QuestionListSerializer
        return QuestionDetailSerializer

    def get_queryset(self):
        """Filter questions by faculty."""
        user = self.request.user

        # Faculty can only see their own questions
        if user.is_faculty():
            return Question.objects.filter(created_by=user).prefetch_related(
                'test_cases'
            )

        # Students cannot access this endpoint
        return Question.objects.none()

    def create(self, request, *args, **kwargs):
        """
        Create a new question with test cases.

        POST /api/questions/
        {
            "title": "Sum of Numbers",
            "description": "Given N numbers, find their sum",
            "input_format": "First line: N (number of numbers)",
            "output_format": "Single line: sum of all numbers",
            "constraints": "1 <= N <= 1000, 1 <= each number <= 10000",
            "sample_input": "3\n1 2 3",
            "sample_output": "6",
            "sample_explanation": "1 + 2 + 3 = 6",
            "difficulty": "easy",
            "topic": "Basic Math",
            "total_marks": 10,
            "time_limit_seconds": 30,
            "memory_limit_mb": 128,
            "test_cases": [
                {
                    "input": "3\n1 2 3",
                    "expected_output": "6",
                    "is_sample": true,
                    "marks": 5,
                    "order": 1
                },
                {
                    "input": "5\n1 2 3 4 5",
                    "expected_output": "15",
                    "is_sample": false,
                    "marks": 5,
                    "order": 2
                }
            ]
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(
            {
                'message': 'Question created successfully (DRAFT status)',
                'question': QuestionDetailSerializer(
                    serializer.instance, context=self.get_serializer_context()
                ).data
            },
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        """Update an existing question."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # Can only edit draft or active questions
        if instance.status == Question.Status.ARCHIVED:
            return Response(
                {'error': 'Cannot edit archived questions'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(
            instance, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(
            {
                'message': 'Question updated successfully',
                'question': QuestionDetailSerializer(
                    instance, context=self.get_serializer_context()
                ).data
            }
        )

    def destroy(self, request, *args, **kwargs):
        """
        Delete a question.

        Only DRAFT questions can be deleted.
        Active and archived questions should be archived instead.

        DELETE /api/questions/{id}/
        """
        instance = self.get_object()

        if instance.status != Question.Status.DRAFT:
            return Response(
                {
                    'error': 'Only draft questions can be deleted',
                    'details': 'Use the archive action to archive active questions'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        self.perform_destroy(instance)
        return Response(
            {'message': 'Question deleted successfully'},
            status=status.HTTP_204_NO_CONTENT
        )

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def preview(self, request):
        """
        Preview question before saving.

        Validates the question without creating it.

        POST /api/questions/preview/
        """
        serializer = QuestionPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response(
            {
                'message': 'Question validation successful',
                'preview': serializer.validated_data
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated])
    def change_status(self, request, pk=None):
        """
        Change question status.

        PATCH /api/questions/{id}/change_status/
        {
            "status": "active"  // draft, active, or archived
        }
        """
        instance = self.get_object()
        serializer = QuestionStatusChangeSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                'message': f'Question status changed to {instance.status}',
                'question': QuestionDetailSerializer(
                    instance, context=self.get_serializer_context()
                ).data
            }
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def publish(self, request, pk=None):
        """
        Publish a question (change status to ACTIVE).

        POST /api/questions/{id}/publish/
        """
        instance = self.get_object()

        if instance.status == Question.Status.ACTIVE:
            return Response(
                {'error': 'Question is already active'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate test cases before publishing
        if not instance.test_cases.exists():
            return Response(
                {'error': 'Question must have at least one test case'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not instance.test_cases.filter(is_sample=True).exists():
            return Response(
                {'error': 'Question must have at least one sample test case'},
                status=status.HTTP_400_BAD_REQUEST
            )

        total_test_marks = sum(
            tc.marks for tc in instance.test_cases.all()
        )
        if total_test_marks != instance.total_marks:
            return Response(
                {
                    'error': 'Test case marks do not match question marks',
                    'total_marks': instance.total_marks,
                    'test_marks': total_test_marks
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        instance.status = Question.Status.ACTIVE
        instance.save()

        return Response(
            {
                'message': 'Question published successfully',
                'question': QuestionDetailSerializer(
                    instance, context=self.get_serializer_context()
                ).data
            }
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def archive(self, request, pk=None):
        """
        Archive a question (change status to ARCHIVED).

        POST /api/questions/{id}/archive/
        """
        instance = self.get_object()

        if instance.status == Question.Status.ARCHIVED:
            return Response(
                {'error': 'Question is already archived'},
                status=status.HTTP_400_BAD_REQUEST
            )

        instance.status = Question.Status.ARCHIVED
        instance.save()

        return Response(
            {
                'message': 'Question archived successfully',
                'question': QuestionDetailSerializer(
                    instance, context=self.get_serializer_context()
                ).data
            }
        )

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def statistics(self, request):
        """
        Get statistics about questions.

        GET /api/questions/statistics/
        """
        user = request.user
        questions = self.get_queryset()

        if not questions.exists():
            return Response(
                {
                    'total_questions': 0,
                    'by_difficulty': {},
                    'by_status': {},
                    'by_topic': {},
                    'average_marks': 0
                }
            )

        stats = {
            'total_questions': questions.count(),
            'by_difficulty': dict(
                questions.values('difficulty').annotate(count=Count('id')).values_list(
                    'difficulty', 'count'
                )
            ),
            'by_status': dict(
                questions.values('status').annotate(count=Count('id')).values_list(
                    'status', 'count'
                )
            ),
            'by_topic': dict(
                questions.filter(topic__isnull=False).values('topic').annotate(
                    count=Count('id')
                ).values_list('topic', 'count')
            ),
            'average_marks': questions.aggregate(avg=Avg('total_marks'))['avg'] or 0
        }

        serializer = QuestionStatsSerializer(stats)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def test_cases(self, request, pk=None):
        """
        Get all test cases for a question.

        GET /api/questions/{id}/test_cases/
        """
        question = self.get_object()
        test_cases = question.test_cases.all()
        serializer = TestCaseDetailSerializer(test_cases, many=True)

        return Response(
            {
                'question_id': str(question.id),
                'question_title': question.title,
                'test_case_count': test_cases.count(),
                'sample_count': test_cases.filter(is_sample=True).count(),
                'hidden_count': test_cases.filter(is_sample=False).count(),
                'test_cases': serializer.data
            }
        )


class TestCaseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing test cases.

    Faculty can create, update, and delete test cases for their questions.
    """

    queryset = TestCase.objects.all()
    permission_classes = [IsAuthenticated, IsApprovedFaculty]
    serializer_class = TestCaseDetailSerializer

    def get_queryset(self):
        """Filter test cases by faculty's questions."""
        user = self.request.user

        if user.is_faculty():
            return TestCase.objects.filter(
                question__created_by=user
            ).select_related('question')

        return TestCase.objects.none()

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return TestCaseCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TestCaseUpdateSerializer
        return TestCaseDetailSerializer

    def create(self, request, *args, **kwargs):
        """
        Create a new test case for a question.

        POST /api/test_cases/
        {
            "question_id": "uuid",
            "input": "3\n1 2 3",
            "expected_output": "6",
            "is_sample": true,
            "marks": 5,
            "order": 1
        }
        """
        question_id = request.data.get('question_id')

        if not question_id:
            return Response(
                {'error': 'question_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            question = Question.objects.get(id=question_id, created_by=request.user)
        except Question.DoesNotExist:
            return Response(
                {'error': 'Question not found or you do not have permission'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(
            data=request.data,
            context={'question': question, 'request': request}
        )
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(
            {
                'message': 'Test case created successfully',
                'test_case': TestCaseDetailSerializer(serializer.instance).data
            },
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        """Update an existing test case."""
        instance = self.get_object()

        serializer = self.get_serializer(instance, data=request.data, partial=kwargs.get('partial', False))
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(
            {
                'message': 'Test case updated successfully',
                'test_case': TestCaseDetailSerializer(instance).data
            }
        )

    def destroy(self, request, *args, **kwargs):
        """Delete a test case."""
        instance = self.get_object()
        question = instance.question

        # Check if question is published
        if question.status == Question.Status.ACTIVE:
            # Warn user but allow deletion if test case count > 1
            if question.test_cases.count() <= 1:
                return Response(
                    {
                        'error': 'Cannot delete the only test case from an active question',
                        'details': 'Archive the question first if you need to remove all test cases'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        self.perform_destroy(instance)
        return Response(
            {'message': 'Test case deleted successfully'},
            status=status.HTTP_204_NO_CONTENT
        )
