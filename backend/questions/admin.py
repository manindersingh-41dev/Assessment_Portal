"""
Django admin interface for Question Bank management.

Provides admin panel for managing questions and test cases.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import Question, TestCase


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """Admin interface for Question model."""

    list_display = (
        'question_id', 'title', 'difficulty_colored', 'status_colored', 'topic',
        'total_marks', 'test_case_count', 'created_by_name', 'created_at'
    )
    list_filter = ('status', 'difficulty', 'topic', 'created_at', 'language')
    search_fields = ('=id', 'title', 'description', 'topic')
    readonly_fields = (
        'question_id', 'created_by', 'created_at', 'updated_at', 'test_case_count_display',
        'test_case_marks_validation'
    )
    ordering = ('-created_at',)

    fieldsets = (
        ('Question Information', {
            'fields': ('question_id', 'title', 'topic', 'difficulty', 'status')
        }),
        ('Problem Statement', {
            'fields': (
                'description', 'input_format', 'output_format', 'constraints'
            )
        }),
        ('Sample Test Case', {
            'fields': (
                'sample_input', 'sample_output', 'sample_explanation'
            )
        }),
        ('Configuration', {
            'fields': (
                'language', 'total_marks', 'time_limit_seconds', 'memory_limit_mb'
            )
        }),
        ('Test Cases', {
            'fields': ('test_case_count_display', 'test_case_marks_validation'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['publish_questions', 'archive_questions', 'make_draft']

    def get_queryset(self, request):
        """Optimize queryset with annotations."""
        qs = super().get_queryset(request)
        return qs.annotate(test_case_count=Count('test_cases'))

    def difficulty_colored(self, obj):
        """Display difficulty with color coding."""
        colors = {
            'easy': '#28A745',
            'medium': '#FFC107',
            'hard': '#DC3545',
        }
        color = colors.get(obj.difficulty, '#6C757D')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_difficulty_display()
        )
    difficulty_colored.short_description = 'Difficulty'

    def status_colored(self, obj):
        """Display status with color coding."""
        colors = {
            'draft': '#6C757D',
            'active': '#28A745',
            'archived': '#DC3545',
        }
        color = colors.get(obj.status, '#6C757D')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_colored.short_description = 'Status'

    def created_by_name(self, obj):
        """Display creator's name."""
        return obj.created_by.get_full_name() if obj.created_by else 'Unknown'
    created_by_name.short_description = 'Created By'

    def test_case_count(self, obj):
        """Display count of test cases."""
        count = obj.test_case_count
        return format_html(
            '<span style="background-color: #007bff; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            count
        )
    test_case_count.short_description = 'Test Cases'

    def test_case_count_display(self, obj):
        """Display detailed test case information."""
        sample_count = obj.test_cases.filter(is_sample=True).count()
        hidden_count = obj.test_cases.filter(is_sample=False).count()
        total_count = obj.test_cases.count()
        return f'Total: {total_count} (Sample: {sample_count}, Hidden: {hidden_count})'
    test_case_count_display.short_description = 'Test Case Count'

    def test_case_marks_validation(self, obj):
        """Display test case marks validation status."""
        if not obj.test_cases.exists():
            return format_html(
                '<span style="color: #DC3545;">✗ No test cases</span>'
            )

        total_marks = sum(tc.marks for tc in obj.test_cases.all())
        if total_marks == obj.total_marks:
            return format_html(
                '<span style="color: #28A745;">✓ Valid ({} marks)</span>',
                total_marks
            )
        else:
            return format_html(
                '<span style="color: #FFC107;">⚠ Mismatch ({} vs {})</span>',
                total_marks,
                obj.total_marks
            )
    test_case_marks_validation.short_description = 'Marks Validation'

    def publish_questions(self, request, queryset):
        """Action to publish questions."""
        count = 0
        for question in queryset:
            if question.status == Question.Status.DRAFT:
                # Check if can publish
                if question.test_cases.exists():
                    question.status = Question.Status.ACTIVE
                    question.save()
                    count += 1
        self.message_user(request, f'{count} question(s) published.')
    publish_questions.short_description = 'Publish selected questions'

    def archive_questions(self, request, queryset):
        """Action to archive questions."""
        count = queryset.exclude(status=Question.Status.ARCHIVED).update(
            status=Question.Status.ARCHIVED
        )
        self.message_user(request, f'{count} question(s) archived.')
    archive_questions.short_description = 'Archive selected questions'

    def make_draft(self, request, queryset):
        """Action to move questions back to draft."""
        count = queryset.update(status=Question.Status.DRAFT)
        self.message_user(request, f'{count} question(s) moved to draft.')
    make_draft.short_description = 'Move selected questions to draft'


@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    """Admin interface for TestCase model."""

    list_display = (
        'question_title', 'order', 'sample_badge', 'marks', 'created_at'
    )
    list_filter = ('is_sample', 'marks', 'created_at')
    search_fields = ('question__title', 'input', 'expected_output')
    readonly_fields = ('id', 'created_at', 'updated_at', 'input_preview', 'output_preview')
    ordering = ('question', 'order')

    fieldsets = (
        ('Test Case Information', {
            'fields': ('id', 'question', 'order', 'is_sample')
        }),
        ('Input/Output', {
            'fields': ('input_preview', 'input', 'output_preview', 'expected_output')
        }),
        ('Marks', {
            'fields': ('marks',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_sample', 'mark_as_hidden']

    def question_title(self, obj):
        """Display question title with link."""
        return obj.question.title
    question_title.short_description = 'Question'

    def sample_badge(self, obj):
        """Display sample/hidden badge."""
        if obj.is_sample:
            return format_html(
                '<span style="background-color: #28A745; color: white; padding: 3px 8px; border-radius: 3px;">Sample</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #6C757D; color: white; padding: 3px 8px; border-radius: 3px;">Hidden</span>'
            )
    sample_badge.short_description = 'Type'

    def input_preview(self, obj):
        """Preview input (first 200 chars)."""
        preview = obj.input[:200]
        if len(obj.input) > 200:
            preview += '...'
        return preview
    input_preview.short_description = 'Input Preview'

    def output_preview(self, obj):
        """Preview output (first 200 chars)."""
        preview = obj.expected_output[:200]
        if len(obj.expected_output) > 200:
            preview += '...'
        return preview
    output_preview.short_description = 'Output Preview'

    def mark_as_sample(self, request, queryset):
        """Action to mark test cases as sample."""
        count = queryset.update(is_sample=True)
        self.message_user(request, f'{count} test case(s) marked as sample.')
    mark_as_sample.short_description = 'Mark selected as sample'

    def mark_as_hidden(self, request, queryset):
        """Action to mark test cases as hidden."""
        count = queryset.update(is_sample=False)
        self.message_user(request, f'{count} test case(s) marked as hidden.')
    mark_as_hidden.short_description = 'Mark selected as hidden'
