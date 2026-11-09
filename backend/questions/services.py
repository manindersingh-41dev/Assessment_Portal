"""
Business logic services for Question Bank management.

Handles validation, calculations, and complex operations for questions and test cases.
"""

from django.apps import apps
from django.db import transaction
from django.db.models import Sum, Count, Q
from .models import Question, TestCase


def has_test_case_results(test_case):
    """Check verdicts using the active submission model's test-case order key."""
    verdict_model = apps.get_model("submissions", "TestCaseVerdict")
    return verdict_model.objects.filter(
        submission__question__question_id=test_case.question_id,
        test_case_order=test_case.order,
    ).exists()


def question_has_submissions(question):
    """Check whether a question has any submissions through an assessment."""
    submission_model = apps.get_model("submissions", "CodeSubmission")
    return submission_model.objects.filter(question__question_id=question.pk).exists()


def publish_question(question):
    """Publish a question (move to ACTIVE status).

    Args:
        question (Question): Question to publish

    Returns:
        tuple: (success: bool, message: str)
    """
    service = QuestionService()
    can_publish, message = service.can_publish(question)
    if not can_publish:
        return False, message

    question.status = Question.Status.ACTIVE
    question.is_published = True
    question.save()
    return True, 'Question published successfully'


def archive_question(question):
    """Archive a question (move to ARCHIVED status).

    Args:
        question (Question): Question to archive

    Returns:
        tuple: (success: bool, message: str)
    """
    question.status = Question.Status.ARCHIVED
    question.is_published = False
    question.save()
    return True, 'Question archived successfully'


class QuestionService:
    """Service for question-related business logic."""

    @staticmethod
    def validate_test_case_marks(question):
        """
        Validate that total test case marks equals question total marks.

        Args:
            question (Question): Question to validate

        Returns:
            tuple: (is_valid: bool, message: str, total_marks: int)
        """
        test_cases = question.test_cases.all()

        if not test_cases.exists():
            return False, 'Question must have at least one test case', 0

        total_marks = test_cases.aggregate(Sum('marks'))['marks__sum'] or 0

        if total_marks != question.total_marks:
            return False, f'Test case marks ({total_marks}) do not match question marks ({question.total_marks})', total_marks

        return True, 'Test case marks are valid', total_marks

    @staticmethod
    def validate_sample_test_cases(question):
        """
        Validate that question has at least one sample test case.

        Args:
            question (Question): Question to validate

        Returns:
            tuple: (is_valid: bool, message: str)
        """
        sample_count = question.test_cases.filter(is_sample=True).count()

        if sample_count == 0:
            return False, 'Question must have at least one sample test case'

        return True, f'Question has {sample_count} sample test case(s)'

    @staticmethod
    def can_publish(question):
        """
        Check if question can be published (moved to ACTIVE status).

        Args:
            question (Question): Question to check

        Returns:
            tuple: (can_publish: bool, message: str)
        """
        # Check test cases exist
        marks_valid, marks_message, total_marks = QuestionService.validate_test_case_marks(question)
        if not marks_valid:
            return False, marks_message

        # Check sample test cases exist
        sample_valid, sample_message = QuestionService.validate_sample_test_cases(question)
        if not sample_valid:
            return False, sample_message

        return True, 'Question can be published'

    @staticmethod
    def get_question_stats(questions_qs):
        """
        Get statistics about a set of questions.

        Args:
            questions_qs (QuerySet): QuerySet of questions

        Returns:
            dict: Statistics dictionary
        """
        return {
            'total_questions': questions_qs.count(),
            'by_difficulty': dict(
                questions_qs.values('difficulty').annotate(
                    count=Count('id')
                ).values_list('difficulty', 'count')
            ),
            'by_status': dict(
                questions_qs.values('status').annotate(
                    count=Count('id')
                ).values_list('status', 'count')
            ),
            'by_topic': dict(
                questions_qs.filter(topic__isnull=False).values('topic').annotate(
                    count=Count('id')
                ).values_list('topic', 'count')
            ),
        }

    @staticmethod
    @transaction.atomic
    def bulk_update_status(question_ids, new_status, user):
        """
        Update status for multiple questions.

        Args:
            question_ids (list): List of question IDs
            new_status (str): New status value
            user: Current user

        Returns:
            dict: Operation result with count and details
        """
        questions = Question.objects.filter(
            id__in=question_ids,
            created_by=user
        )

        count = questions.update(status=new_status)

        return {
            'updated_count': count,
            'message': f'Successfully updated {count} question(s) to {new_status}'
        }

    @staticmethod
    def get_question_difficulty_stats(user):
        """Get distribution of questions by difficulty."""
        questions = Question.objects.filter(created_by=user)
        return dict(
            questions.values('difficulty').annotate(
                count=Count('id')
            ).values_list('difficulty', 'count')
        )

    @staticmethod
    def search_questions(user, query):
        """
        Search questions by title or description.

        Args:
            user: Current user
            query (str): Search query

        Returns:
            QuerySet: Matching questions
        """
        return Question.objects.filter(
            created_by=user
        ).filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )


class TestCaseService:
    """Service for test case-related business logic."""

    @staticmethod
    def create_test_cases(question, test_cases_data):
        """
        Create multiple test cases for a question.

        Args:
            question (Question): Question to add test cases to
            test_cases_data (list): List of test case data dictionaries

        Returns:
            tuple: (success: bool, message: str, created_count: int)
        """
        try:
            with transaction.atomic():
                total_marks = sum(tc.get('marks', 0) for tc in test_cases_data)

                if total_marks != question.total_marks:
                    return False, f'Test case marks ({total_marks}) do not match question marks ({question.total_marks})', 0

                created_test_cases = []
                for order, tc_data in enumerate(test_cases_data, start=1):
                    tc = TestCase.objects.create(
                        question=question,
                        order=order,
                        **tc_data
                    )
                    created_test_cases.append(tc)

                return True, f'Successfully created {len(created_test_cases)} test cases', len(created_test_cases)

        except Exception as e:
            return False, str(e), 0

    @staticmethod
    def update_test_case(test_case, data):
        """
        Update a test case with validation.

        Args:
            test_case (TestCase): Test case to update
            data (dict): Data to update

        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            question = test_case.question

            # If updating marks, validate against question
            if 'marks' in data:
                new_marks = data['marks']
                other_marks = question.test_cases.exclude(
                    id=test_case.id
                ).aggregate(Sum('marks'))['marks__sum'] or 0

                if other_marks + new_marks > question.total_marks:
                    return False, f'New total marks ({other_marks + new_marks}) would exceed question limit ({question.total_marks})'

            # Update test case
            for key, value in data.items():
                setattr(test_case, key, value)
            test_case.save()

            return True, 'Test case updated successfully'

        except Exception as e:
            return False, str(e)

    @staticmethod
    def get_test_case_stats(question):
        """
        Get statistics about test cases for a question.

        Args:
            question (Question): Question to analyze

        Returns:
            dict: Statistics dictionary
        """
        test_cases = question.test_cases.all()

        return {
            'total_test_cases': test_cases.count(),
            'sample_test_cases': test_cases.filter(is_sample=True).count(),
            'hidden_test_cases': test_cases.filter(is_sample=False).count(),
            'total_marks': test_cases.aggregate(Sum('marks'))['marks__sum'] or 0,
        }

    @staticmethod
    def can_delete_test_case(test_case):
        """
        Check if a test case can be deleted.

        Args:
            test_case (TestCase): Test case to check

        Returns:
            tuple: (can_delete: bool, message: str)
        """
        question = test_case.question

        if has_test_case_results(test_case):
            return False, 'Test cases with recorded results cannot be deleted'

        # Cannot delete if only test case remains
        if question.test_cases.count() <= 1:
            return False, 'Question must have at least one test case'

        # Cannot delete sample test case if it's the only one
        if test_case.is_sample and question.test_cases.filter(is_sample=True).count() == 1:
            return False, 'Question must have at least one sample test case'

        return True, 'Test case can be deleted'

    @staticmethod
    def reorder_test_cases(question, orders):
        """
        Reorder test cases for a question.

        Args:
            question (Question): Question whose test cases to reorder
            orders (dict): Mapping of test_case_id to new order

        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            with transaction.atomic():
                for test_case_id, order in orders.items():
                    TestCase.objects.filter(
                        id=test_case_id,
                        question=question
                    ).update(order=order)

                return True, f'Reordered {len(orders)} test cases'

        except Exception as e:
            return False, str(e)

    @staticmethod
    def get_sample_test_cases(question):
        """
        Get all sample test cases for a question.

        Args:
            question (Question): Question to get samples from

        Returns:
            QuerySet: Sample test cases
        """
        return question.test_cases.filter(is_sample=True).order_by('order')

    @staticmethod
    def validate_test_case_input_output(input_data, expected_output):
        """
        Validate test case input and output format.

        Args:
            input_data (str): Input data
            expected_output (str): Expected output

        Returns:
            tuple: (is_valid: bool, message: str)
        """
        if not input_data or not input_data.strip():
            return False, 'Input data cannot be empty'

        if not expected_output or not expected_output.strip():
            return False, 'Expected output cannot be empty'

        return True, 'Input and output are valid'
