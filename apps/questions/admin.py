from django.contrib import admin
from .forms import QuestionForm
from .models import Question


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    # Form yang sama dengan Bank Soal: 5 opsi A-E wajib dan batas ukuran gambar berlaku juga di admin
    form = QuestionForm
    list_display = ('id', 'subject', 'level', 'created_by', 'correct_answer', 'created_at')
    list_filter = ('subject', 'level', 'correct_answer')
    search_fields = ('question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'option_e')
    ordering = ('-created_at',)
