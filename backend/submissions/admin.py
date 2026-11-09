"""
Django admin interface for Code Submissions.

Provides admin panel for managing submissions and results.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import CodeSubmission, TestCaseVerdict, ExecutionLog


@admin.register(CodeSubmission)
class CodeSubmissionAdmin(admin.ModelAdmin):
    """Admin interface for CodeSubmission model."""

    list_display = (
        'submission_id_display', 'student_name', 'question_title',
        'status_colored', 'verdict_colored', 'marks_display',
        'test_results_display', 'created_at'
    )
    list_filter = ('status', 'verdict', 'created_at', 'language', 'runner_type')
    search_fields = ('student__email', 'question__question__title', 'id')
    readonly_fields = (
        'id', 'student', 'assignment', 'question', 'created_at', 'updated_at',
        'execution_job_id', 'source_code_display', 'compilation_error_display',
        'execution_summary', 'runner_type', 'runner_version', 'compiler_version',
        'client_submission_id'
    )
    ordering = ('-created_at',)

    fieldsets = (
        ('Submission Info', {
            'fields': ('id', 'student', 'assignment', 'question', 'attempt_number')
        }),
        ('Source Code', {
            'fields': ('source_code_display', 'language'),
            'classes': ('collapse',)
        }),
        ('Execution Status', {
            'fields': (
                'status', 'verdict', 'execution_job_id',
                'execution_started_at', 'execution_completed_at'
            )
        }),
        ('Compilation', {
            'fields': ('compilation_error_display', 'compilation_time_ms'),
            'classes': ('collapse',)
        }),
        ('Results', {
            'fields': (
                'marks_obtained', 'total_test_cases', 'passed_test_cases',
                'failed_test_cases', 'execution_summary'
            )
        }),
        ('Performance', {
            'fields': ('execution_time_ms', 'max_memory_used_mb', 'ip_address'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': (
                'created_at', 'updated_at', 'runner_type', 'runner_version',
                'compiler_version', 'client_submission_id'
            ),
            'classes': ('collapse',)
        }),
    )

    def submission_id_display(self, obj):
        """Display submission ID."""
        return format_html(
            '<span style="font-family: monospace;">{}</span>',
            str(obj.id)[:8]
        )
    submission_id_display.short_description = 'Submission'

    def student_name(self, obj):
        """Display student name."""
        return obj.student.get_full_name()
    student_name.short_description = 'Student'

    def question_title(self, obj):
        """Display question title."""
        return obj.question.question.title[:50]
    question_title.short_description = 'Question'

    def status_colored(self, obj):
        """Display status with color coding."""
        colors = {
            'pending': '#6C757D',
            'compiling': '#FFC107',
            'compiled': '#17a2b8',
            'executing': '#0dcaf0',
            'completed': '#28A745',
            'failed': '#DC3545',
        }
        color = colors.get(obj.status, '#6C757D')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_colored.short_description = 'Status'

    def verdict_colored(self, obj):
        """Display verdict with color coding."""
        colors = {
            'accepted': '#28A745',
            'wrong_answer': '#FFC107',
            'compilation_error': '#DC3545',
            'runtime_error': '#DC3545',
            'time_limit_exceeded': '#FFC107',
            'memory_limit_exceeded': '#FFC107',
            'internal_error': '#DC3545',
            'not_evaluated': '#6C757D',
        }
        color = colors.get(obj.verdict, '#6C757D')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_verdict_display()
        )
    verdict_colored.short_description = 'Verdict'

    def marks_display(self, obj):
        """Display marks."""
        if obj.marks_obtained is None:
            return '-'
        return format_html(
            '<strong>{}</strong>',
            obj.marks_obtained
        )
    marks_display.short_description = 'Marks'

    def test_results_display(self, obj):
        """Display test results."""
        if obj.total_test_cases == 0:
            return '-'
        return format_html(
            '<span style="color: #28A745; font-weight: bold;">{}/{}</span>',
            obj.passed_test_cases,
            obj.total_test_cases
        )
    test_results_display.short_description = 'Tests'

    def source_code_display(self, obj):
        """Display source code preview."""
        lines = obj.source_code.split('\n')[:10]
        code_html = '<pre style="background: #f5f5f5; padding: 10px; border-radius: 3px;">'
        for line in lines:
            code_html += f'{line}\n'
        if len(obj.source_code.split('\n')) > 10:
            code_html += '\n... (truncated)'
        code_html += '</pre>'
        return format_html(code_html)
    source_code_display.short_description = 'Source Code'

    def compilation_error_display(self, obj):
        """Display compilation error."""
        if not obj.compilation_error:
            return format_html('<span style="color: #28A745;">✓ Compiled successfully</span>')
        return format_html(
            '<span style="color: #DC3545; font-family: monospace;">{}</span>',
            obj.compilation_error[:200]
        )
    compilation_error_display.short_description = 'Compilation'

    def execution_summary(self, obj):
        """Display execution summary."""
        return format_html(
            '<strong>Tests:</strong> {}/{}<br>'
            '<strong>Marks:</strong> {}<br>'
            '<strong>Time:</strong> {}ms<br>'
            '<strong>Memory:</strong> {:.2f}MB<br>'
            '<strong>Success Rate:</strong> {:.1f}%',
            obj.passed_test_cases,
            obj.total_test_cases,
            obj.marks_obtained or '-',
            obj.execution_time_ms or '-',
            obj.max_memory_used_mb or 0,
            obj.get_success_rate()
        )
    execution_summary.short_description = 'Summary'


@admin.register(TestCaseVerdict)
class TestCaseVerdictAdmin(admin.ModelAdmin):
    """Admin interface for TestCaseVerdict model."""

    list_display = (
        'submission_id', 'test_case_order', 'status_colored',
        'marks_display', 'execution_time_display', 'created_at'
    )
    list_filter = ('status', 'is_sample', 'created_at')
    search_fields = ('submission__id', 'error_message')
    readonly_fields = (
        'id', 'submission', 'test_case_order', 'created_at', 'updated_at',
        'actual_output_display', 'error_message_display'
    )
    ordering = ('-created_at',)

    fieldsets = (
        ('Test Case', {
            'fields': ('id', 'submission', 'test_case_order', 'is_sample')
        }),
        ('Verdict', {
            'fields': ('status', 'marks_obtained')
        }),
        ('Execution Details', {
            'fields': ('execution_time_ms', 'memory_used_mb')
        }),
        ('Output', {
            'fields': ('actual_output_display', 'error_message_display'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def submission_id(self, obj):
        """Display submission ID."""
        return format_html(
            '<span style="font-family: monospace;">{}</span>',
            str(obj.submission.id)[:8]
        )
    submission_id.short_description = 'Submission'

    def status_colored(self, obj):
        """Display status with color coding."""
        colors = {
            'accepted': '#28A745',
            'wrong_answer': '#FFC107',
            'runtime_error': '#DC3545',
            'time_limit_exceeded': '#FFC107',
            'memory_limit_exceeded': '#FFC107',
        }
        color = colors.get(obj.status, '#6C757D')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_colored.short_description = 'Status'

    def marks_display(self, obj):
        """Display marks."""
        return format_html('<strong>{}</strong>', obj.marks_obtained)
    marks_display.short_description = 'Marks'

    def execution_time_display(self, obj):
        """Display execution time."""
        if obj.execution_time_ms is None:
            return '-'
        return f'{obj.execution_time_ms}ms'
    execution_time_display.short_description = 'Time'

    def actual_output_display(self, obj):
        """Display actual output."""
        if not obj.actual_output:
            return '-'
        return format_html(
            '<pre style="background: #f5f5f5; padding: 10px; border-radius: 3px; '
            'max-height: 300px; overflow: auto;">{}</pre>',
            obj.actual_output[:500]
        )
    actual_output_display.short_description = 'Actual Output'

    def error_message_display(self, obj):
        """Display error message."""
        if not obj.error_message:
            return format_html('<span style="color: #28A745;">✓ No errors</span>')
        return format_html(
            '<span style="color: #DC3545; font-family: monospace;">{}</span>',
            obj.error_message[:500]
        )
    error_message_display.short_description = 'Error Message'


@admin.register(ExecutionLog)
class ExecutionLogAdmin(admin.ModelAdmin):
    """Admin interface for ExecutionLog model."""

    list_display = (
        'submission_id', 'compilation_status', 'system_info_display', 'created_at'
    )
    search_fields = ('submission__id',)
    readonly_fields = (
        'id', 'submission', 'created_at', 'updated_at',
        'compilation_output_display', 'compilation_stderr_display',
        'execution_output_display'
    )
    ordering = ('-created_at',)

    fieldsets = (
        ('Submission', {
            'fields': ('id', 'submission')
        }),
        ('Compilation', {
            'fields': ('compilation_output_display', 'compilation_stderr_display'),
            'classes': ('collapse',)
        }),
        ('Execution', {
            'fields': ('execution_output_display',),
            'classes': ('collapse',)
        }),
        ('System Info', {
            'fields': ('system_info',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def submission_id(self, obj):
        """Display submission ID."""
        return format_html(
            '<span style="font-family: monospace;">{}</span>',
            str(obj.submission.id)[:8]
        )
    submission_id.short_description = 'Submission'

    def compilation_status(self, obj):
        """Display compilation status."""
        if obj.compilation_stderr:
            return format_html(
                '<span style="color: #DC3545; font-weight: bold;">✗ Error</span>'
            )
        return format_html(
            '<span style="color: #28A745; font-weight: bold;">✓ Success</span>'
        )
    compilation_status.short_description = 'Compilation'

    def system_info_display(self, obj):
        """Display system info summary."""
        info = obj.system_info
        if not info:
            return '-'

        info_html = '<ul style="margin: 0; padding-left: 20px;">'
        for key, value in info.items():
            info_html += f'<li><strong>{key}:</strong> {value}</li>'
        info_html += '</ul>'

        return format_html(info_html)
    system_info_display.short_description = 'System Info'

    def compilation_output_display(self, obj):
        """Display compilation output."""
        if not obj.compilation_output:
            return '-'
        return format_html(
            '<pre style="background: #f5f5f5; padding: 10px; border-radius: 3px; '
            'max-height: 300px; overflow: auto;">{}</pre>',
            obj.compilation_output[:1000]
        )
    compilation_output_display.short_description = 'Stdout'

    def compilation_stderr_display(self, obj):
        """Display compilation stderr."""
        if not obj.compilation_stderr:
            return format_html('<span style="color: #28A745;">✓ No errors</span>')
        return format_html(
            '<pre style="background: #ffe0e0; padding: 10px; border-radius: 3px; '
            'max-height: 300px; overflow: auto; color: #DC3545;">{}</pre>',
            obj.compilation_stderr[:1000]
        )
    compilation_stderr_display.short_description = 'Stderr'

    def execution_output_display(self, obj):
        """Display execution output."""
        if not obj.execution_output:
            return '-'
        return format_html(
            '<pre style="background: #f5f5f5; padding: 10px; border-radius: 3px; '
            'max-height: 300px; overflow: auto;">{}</pre>',
            obj.execution_output[:1000]
        )
    execution_output_display.short_description = 'Output'
