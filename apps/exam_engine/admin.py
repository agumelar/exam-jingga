from django.contrib import admin
from apps.exam_engine.models import ExamSession, StudentAnswer


class StudentAnswerInline(admin.TabularInline):
    model = StudentAnswer
    extra = 0
    fields = ('question', 'chosen_answer', 'is_doubt', 'is_correct', 'updated_at')
    readonly_fields = ('updated_at',)


@admin.register(ExamSession)
class ExamSessionAdmin(admin.ModelAdmin):
    list_display = ('student', 'schedule', 'status', 'violation_count', 'score', 'started_at', 'finished_at')
    list_filter = ('status', 'started_at', 'schedule__exam__subject')
    search_fields = ('student__full_name', 'student__nis', 'schedule__exam__title')
    inlines = [StudentAnswerInline]


@admin.register(StudentAnswer)
class StudentAnswerAdmin(admin.ModelAdmin):
    list_display = ('session', 'question', 'chosen_answer', 'is_doubt', 'is_correct', 'updated_at')
    list_filter = ('chosen_answer', 'is_doubt', 'is_correct')
    search_fields = ('session__student__full_name', 'question__question_text')
