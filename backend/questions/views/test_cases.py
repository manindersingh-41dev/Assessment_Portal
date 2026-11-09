"""Faculty-owned test-case CRUD endpoints."""

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from questions.models import Question, TestCase
from questions.permissions import IsFacultyOrReadOnly
from questions.serializers import (
    TestCaseCreateSerializer,
    TestCaseSerializer,
    TestCaseUpdateSerializer,
)
from questions.services import TestCaseService


def _is_faculty(user):
    value = getattr(user, "is_faculty", False)
    return value() if callable(value) else bool(value)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def question_test_cases(request, pk):
    """Return all test cases for a question owned by the requesting faculty."""
    if not _is_faculty(request.user):
        return Response({"detail": "Faculty only."}, status=status.HTTP_403_FORBIDDEN)

    question = get_object_or_404(Question, pk=pk, created_by=request.user)
    test_cases = question.test_cases.all()
    return Response(
        {
            "question_id": str(question.id),
            "question_title": question.title,
            "test_case_count": test_cases.count(),
            "sample_count": test_cases.filter(is_sample=True).count(),
            "hidden_count": test_cases.filter(is_sample=False).count(),
            "test_cases": TestCaseSerializer(
                test_cases, many=True, context={"request": request}
            ).data,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsFacultyOrReadOnly])
def test_case_list_create(request):
    """Create a test case for a question owned by the authenticated faculty."""
    serializer = TestCaseCreateSerializer(
        data=request.data, context={"request": request}
    )
    serializer.is_valid(raise_exception=True)
    test_case = serializer.save()
    return Response(
        {
            "message": "Test case created successfully.",
            "test_case": TestCaseSerializer(
                test_case, context={"request": request}
            ).data,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated, IsFacultyOrReadOnly])
def test_case_detail(request, pk):
    """Update or delete a test case belonging to the authenticated faculty."""
    test_case = get_object_or_404(
        TestCase.objects.select_related("question"),
        pk=pk,
        question__created_by=request.user,
    )

    if request.method in ("PUT", "PATCH"):
        serializer = TestCaseUpdateSerializer(
            test_case,
            data=request.data,
            partial=(request.method == "PATCH"),
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        updated_test_case = serializer.save()
        return Response(
            {
                "message": "Test case updated successfully.",
                "test_case": TestCaseSerializer(
                    updated_test_case, context={"request": request}
                ).data,
            }
        )

    can_delete, message = TestCaseService.can_delete_test_case(test_case)
    if not can_delete:
        return Response({"detail": message}, status=status.HTTP_400_BAD_REQUEST)

    test_case.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
