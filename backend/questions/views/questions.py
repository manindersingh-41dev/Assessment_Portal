"""
Views for managing the question bank.

Faculty: create, list, retrieve, update, publish/archive questions.
Students: list/retrieve active questions (sample test cases only exposed).
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from questions.models import Question
from questions.permissions import IsFacultyOrReadOnly, IsQuestionOwner
from questions.serializers import (
    QuestionBulkCreateSerializer,
    QuestionCreateUpdateSerializer,
    QuestionSerializer,
)
from questions.services import archive_question, publish_question, question_has_submissions


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsFacultyOrReadOnly])
def question_list_create(request):
    """List questions (filtered to active for students) or create a new one."""

    if request.method == "GET":
        queryset = Question.objects.all()
        # Faculty manage only their own questions; students only see active ones.
        if request.user.is_faculty():
            queryset = queryset.filter(created_by=request.user)
        else:
            queryset = queryset.filter(status=Question.Status.ACTIVE)

        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = QuestionSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    # POST - create (faculty only enforced by permission)
    serializer = QuestionCreateUpdateSerializer(
        data=request.data, context={"request": request}
    )
    if serializer.is_valid():
        serializer.save()
        return Response(
            QuestionSerializer(serializer.instance, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsFacultyOrReadOnly])
def question_bulk_create(request):
    """Atomically create up to 100 questions, each with its own test cases."""
    serializer = QuestionBulkCreateSerializer(
        data=request.data,
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)
    questions = serializer.save()
    return Response(
        {
            "message": f"{len(questions)} questions created successfully.",
            "created_count": len(questions),
            "questions": QuestionSerializer(
                questions,
                many=True,
                context={"request": request},
            ).data,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated, IsFacultyOrReadOnly, IsQuestionOwner])
def question_detail(request, pk):
    """Retrieve, update, or delete a single question."""

    try:
        question = Question.objects.get(pk=pk)
    except Question.DoesNotExist:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.user.is_faculty():
        if question.created_by != request.user:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    # Students can only retrieve active questions and cannot modify them.
    elif request.method != "GET" or question.status != Question.Status.ACTIVE:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = QuestionSerializer(question, context={"request": request})
        return Response(serializer.data)

    if request.method in ("PUT", "PATCH"):
        serializer = QuestionCreateUpdateSerializer(
            question,
            data=request.data,
            partial=(request.method == "PATCH"),
            context={"request": request},
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                QuestionSerializer(serializer.instance, context={"request": request}).data
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # DELETE
    if question.status != Question.Status.DRAFT:
        return Response(
            {
                "error": "Only draft questions can be deleted.",
                "details": "Change the question to draft before deleting it.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    if question_has_submissions(question):
        return Response(
            {
                "error": "This question has submissions and cannot be deleted.",
                "details": "Change the question status instead of deleting it.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    question.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def question_publish(request, pk):
    """Publish a draft question (set status to active). Faculty only."""
    if not request.user.is_faculty:
        return Response({"detail": "Faculty only."}, status=status.HTTP_403_FORBIDDEN)

    try:
        question = Question.objects.get(pk=pk)
    except Question.DoesNotExist:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    if question.created_by != request.user:
        return Response({"detail": "You do not own this question."}, status=status.HTTP_403_FORBIDDEN)

    publish_question(question)
    serializer = QuestionSerializer(question, context={"request": request})
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def question_archive(request, pk):
    """Archive a question. Faculty only."""
    if not request.user.is_faculty:
        return Response({"detail": "Faculty only."}, status=status.HTTP_403_FORBIDDEN)

    try:
        question = Question.objects.get(pk=pk)
    except Question.DoesNotExist:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    if question.created_by != request.user:
        return Response({"detail": "You do not own this question."}, status=status.HTTP_403_FORBIDDEN)

    archive_question(question)
    serializer = QuestionSerializer(question, context={"request": request})
    return Response(serializer.data)
