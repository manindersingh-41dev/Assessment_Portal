"""
Django admin interface for Assessment Management.

Provides admin panel for managing assessments, assignments, and results.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from django.utils import timezone
from .models import (
    Assessment, AssessmentQuestion,
    AssessmentAssignment, AssessmentResult
)


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    """Admin interface for Assessment model."""

    list_display = (
        'title', 'status_colored', 'published_badge', 'is_open_to_all_students',
        'start_time',
        'end_time', 'total_marks', 'question_count', 'assignment_count',
        'created_by_name', 'created_at'
    )
    list_filter = ('status', 'is_published', 'is_open_to_all_students', 'created_at', 'start_time')
    search_fields = ('title', 'description', 'created_by__email')
    readonly_fields = (
        'id', 'created_by', 'created_at', 'updated_at', 'published_at',
        'question_count_display', 'assignment_summary'
    )
    ordering = ('-created_at',)

    fieldsets = (
        ('Assessment Information', {
            'fields': ('id', 'title', 'description', 'instructions', 'status')
        }),
        ('Timing', {
            'fields': ('start_time', 'end_time', 'duration_minutes', 'is_timed')
        }),
        ('Marks', {'fields': ('total_marks',)}),
        ('Availability', {
            'fields': ('is_published', 'is_open_to_all_students', 'published_at')
        }),
        ('Questions', {
            'fields': ('question_count_display',),
            'classes': ('collapse',)
        }),
        ('Assignments', {
            'fields': ('assignment_summary',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['publish_assessments', 'archive_assessments']

    def get_readonly_fields(self, request, obj=None):
        fields = super().get_readonly_fields(request, obj)
        if obj and (obj.is_published or obj.published_at):
            return fields + ('is_open_to_all_students',)
        return fields

    def get_queryset(self, request):
        """Optimize queryset with annotations."""
        qs = super().get_queryset(request)
        return qs.annotate(
            question_count=Count('assessment_questions', distinct=True),
            assignment_count=Count('assignments', distinct=True)
        )

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

    def published_badge(self, obj):
        """Display published badge."""
        if obj.is_published:
            return format_html(
                '<span style="background-color: #28A745; color: white; '
                'padding: 3px 8px; border-radius: 3px;">Published</span>'
            )
        return format_html(
            '<span style="background-color: #6C757D; color: white; '
            'padding: 3px 8px; border-radius: 3px;">Draft</span>'
        )
    published_badge.short_description = 'Published'

    def created_by_name(self, obj):
        """Display creator's name."""
        return obj.created_by.get_full_name() if obj.created_by else 'Unknown'
    created_by_name.short_description = 'Created By'

    def question_count(self, obj):
        """Display count of questions."""
        count = obj.question_count
        return format_html(
            '<span style="background-color: #007bff; color: white; '
            'padding: 3px 8px; border-radius: 3px;">{}</span>',
            count
        )
    question_count.short_description = 'Questions'

    def assignment_count(self, obj):
        """Display count of assignments."""
        count = obj.assignment_count
        return format_html(
            '<span style="background-color: #17a2b8; color: white; '
            'padding: 3px 8px; border-radius: 3px;">{}</span>',
            count
        )
    assignment_count.short_description = 'Assignments'

    def question_count_display(self, obj):
        """Display detailed question information."""
        questions = obj.assessment_questions.all()
        count = questions.count()
        if not count:
            return 'No questions'
        return f'Total: {count} questions'
    question_count_display.short_description = 'Questions'

    def assignment_summary(self, obj):
        """Display assignment summary."""
        assignments = obj.assignments.all()
        if not assignments.exists():
            return 'No assignments'

        summary = {
            'assigned': assignments.filter(status='assigned').count(),
            'started': assignments.filter(status='started').count(),
            'submitted': assignments.filter(status='submitted').count(),
            'evaluated': assignments.filter(status=AssessmentAssignment.Status.GRADED).count(),
        }

        return format_html(
            'Assigned: {}<br>Started: {}<br>Submitted: {}<br>Evaluated: {}',
            summary['assigned'], summary['started'],
            summary['submitted'], summary['evaluated']
        )
    assignment_summary.short_description = 'Assignment Summary'

    def publish_assessments(self, request, queryset):
        """Action to publish assessments."""
        count = 0
        for assessment in queryset:
            if assessment.status == Assessment.Status.DRAFT:
                if assessment.assessment_questions.exists():
                    assessment.is_published = True
                    assessment.status = Assessment.Status.ACTIVE
                    if assessment.published_at is None:
                        assessment.published_at = timezone.now()
                    assessment.save()
                    count += 1
        self.message_user(request, f'{count} assessment(s) published.')
    publish_assessments.short_description = 'Publish selected assessments'

    def archive_assessments(self, request, queryset):
        """Action to archive assessments."""
        count = queryset.exclude(status=Assessment.Status.ARCHIVED).update(
            status=Assessment.Status.ARCHIVED
        )
        self.message_user(request, f'{count} assessment(s) archived.')
    archive_assessments.short_description = 'Archive selected assessments'


@admin.register(AssessmentQuestion)
class AssessmentQuestionAdmin(admin.ModelAdmin):
    """Admin interface for AssessmentQuestion model."""

    list_display = (
        'assessment_title', 'order', 'question',
        'marks', 'created_at'
    )
    list_filter = ('assessment', 'created_at')
    search_fields = ('assessment__title', 'question__title')
    readonly_fields = (
        'id', 'assessment', 'question', 'created_at', 'updated_at'
    )
    ordering = ('assessment', 'order')

    fieldsets = (
        ('Question Link', {
            'fields': ('id', 'assessment', 'question', 'order')
        }),
        ('Assessment Settings', {
            'fields': ('marks',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def assessment_title(self, obj):
        """Display assessment title with link."""
        return obj.assessment.title
    assessment_title.short_description = 'Assessment'


@admin.register(AssessmentAssignment)
class AssessmentAssignmentAdmin(admin.ModelAdmin):
    """Admin interface for AssessmentAssignment model."""

    list_display = (
        'assessment_title', 'student_name', 'status_colored',
        'started_at', 'submitted_at', 'due_at', 'created_at'
    )
    list_filter = ('status', 'created_at')
    search_fields = ('assessment__title', 'student__email', 'student__first_name')
    readonly_fields = (
        'id', 'assessment', 'student', 'created_at', 'started_at',
        'submitted_at', 'assignment_timeline'
    )
    ordering = ('-created_at',)

    fieldsets = (
        ('Assignment', {
            'fields': ('id', 'assessment', 'student', 'status')
        }),
        ('Timeline', {
            'fields': (
                'created_at', 'started_at', 'submitted_at',
                'due_at', 'assignment_timeline'
            )
        }),
        ('Metadata', {
            'fields': (),
        }),
    )

    def assessment_title(self, obj):
        """Display assessment title."""
        return obj.assessment.title
    assessment_title.short_description = 'Assessment'

    def student_name(self, obj):
        """Display student name."""
        return obj.student.get_full_name()
    student_name.short_description = 'Student'

    def status_colored(self, obj):
        """Display status with color coding."""
        colors = {
            'assigned': '#6C757D',
            'started': '#FFC107',
            'submitted': '#17a2b8',
            'graded': '#28A745',
            'expired': '#DC3545',
        }
        color = colors.get(obj.status, '#6C757D')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_colored.short_description = 'Status'

    def assignment_timeline(self, obj):
        """Display assignment timeline."""
        timeline = '<strong>Timeline:</strong><br>'
        timeline += f'Assigned: {obj.created_at.strftime("%Y-%m-%d %H:%M") if obj.created_at else "—"}<br>'
        timeline += f'Started: {obj.started_at.strftime("%Y-%m-%d %H:%M") if obj.started_at else "—"}<br>'
        timeline += f'Submitted: {obj.submitted_at.strftime("%Y-%m-%d %H:%M") if obj.submitted_at else "—"}<br>'
        timeline += f'Due: {obj.due_at.strftime("%Y-%m-%d %H:%M") if obj.due_at else "No deadline"}<br>'

        return format_html(timeline)
    assignment_timeline.short_description = 'Timeline'


@admin.register(AssessmentResult)
class AssessmentResultAdmin(admin.ModelAdmin):
    """Admin interface for AssessmentResult model."""

    list_display = (
        'assessment_title', 'student_name', 'marks_display',
        'percentage_display', 'passed_badge', 'evaluated_at'
    )
    list_filter = ('passed', 'evaluated_at', 'percentage')
    search_fields = ('assessment__title', 'student__email', 'student__first_name')
    readonly_fields = (
        'id', 'assessment', 'student', 'attempted_at', 'evaluated_at',
        'result_summary'
    )
    ordering = ('-evaluated_at',)

    fieldsets = (
        ('Result', {
            'fields': ('id', 'assessment', 'student')
        }),
        ('Performance', {
            'fields': (
                'total_marks_obtained', 'percentage', 'passed', 'result_summary'
            )
        }),
        ('Feedback', {
            'fields': ('feedback',)
        }),
        ('Metadata', {
            'fields': ('attempted_at', 'evaluated_at'),
            'classes': ('collapse',)
        }),
    )

    def assessment_title(self, obj):
        """Display assessment title."""
        return obj.assessment.title
    assessment_title.short_description = 'Assessment'

    def student_name(self, obj):
        """Display student name."""
        return obj.student.get_full_name()
    student_name.short_description = 'Student'

    def marks_display(self, obj):
        """Display marks."""
        return format_html(
            '<strong>{}/{}</strong>',
            obj.total_marks_obtained,
            obj.assessment.total_marks
        )
    marks_display.short_description = 'Marks'

    def percentage_display(self, obj):
        """Display percentage with color."""
        if obj.percentage >= 80:
            color = '#28A745'
        elif obj.percentage >= 60:
            color = '#FFC107'
        else:
            color = '#DC3545'

        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color,
            obj.percentage
        )
    percentage_display.short_description = 'Percentage'

    def passed_badge(self, obj):
        """Display pass/fail badge."""
        if obj.passed:
            return format_html(
                '<span style="background-color: #28A745; color: white; '
                'padding: 3px 8px; border-radius: 3px;">Passed</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #DC3545; color: white; '
                'padding: 3px 8px; border-radius: 3px;">Failed</span>'
            )
    passed_badge.short_description = 'Result'

    def result_summary(self, obj):
        """Display result summary."""
        return format_html(
            '<strong>Marks:</strong> {}/{} ({:.1f}%)<br>'
            '<strong>Status:</strong> {}<br>'
            '<strong>Maximum Marks:</strong> {}',
            obj.total_marks_obtained,
            obj.assessment.total_marks,
            obj.percentage,
            'Passed' if obj.passed else 'Failed',
            obj.assessment.total_marks
        )
    result_summary.short_description = 'Result Summary'
