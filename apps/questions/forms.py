from django import forms
from .models import Question
from apps.master_data.models import Subject, Teacher


class QuestionForm(forms.ModelForm):
    """Formulir input / edit butir soal bank soal."""
    
    clear_question_image = forms.BooleanField(required=False)
    clear_image_a = forms.BooleanField(required=False)
    clear_image_b = forms.BooleanField(required=False)
    clear_image_c = forms.BooleanField(required=False)
    clear_image_d = forms.BooleanField(required=False)
    clear_image_e = forms.BooleanField(required=False)

    class Meta:
        model = Question
        fields = [
            'subject',
            'created_by',
            'level',
            'cp_code',
            'cp_name',
            'question_text',
            'question_image',
            'option_a',
            'image_a',
            'option_b',
            'image_b',
            'option_c',
            'image_c',
            'option_d',
            'image_d',
            'option_e',
            'image_e',
            'correct_answer',
        ]
        widgets = {
            'cp_code': forms.Select(attrs={'class': 'w-full'}),
            'cp_name': forms.TextInput(attrs={'placeholder': 'Nama/topik Capaian Pembelajaran (opsional)...'}),
            'question_text': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Tuliskan butir soal di sini...'}),
            'option_a': forms.TextInput(attrs={'placeholder': 'Pilihan jawaban A...'}),
            'option_b': forms.TextInput(attrs={'placeholder': 'Pilihan jawaban B...'}),
            'option_c': forms.TextInput(attrs={'placeholder': 'Pilihan jawaban C...'}),
            'option_d': forms.TextInput(attrs={'placeholder': 'Pilihan jawaban D...'}),
            'option_e': forms.TextInput(attrs={'placeholder': 'Pilihan jawaban E...'}),
            'correct_answer': forms.RadioSelect(choices=Question.ANSWER_CHOICES),
        }

    def clean(self):
        cleaned_data = super().clean()
        for opt in ['a', 'b', 'c', 'd', 'e']:
            text_val = str(cleaned_data.get(f'option_{opt}') or '').strip()
            img_val = cleaned_data.get(f'image_{opt}')
            instance_img = getattr(self.instance, f'image_{opt}', None)
            clear_img = cleaned_data.get(f'clear_image_{opt}')
            has_img = bool(img_val or (instance_img and not clear_img))
            if not text_val and not has_img:
                self.add_error(f'option_{opt}', f'Pilihan jawaban {opt.upper()} wajib diisi (teks atau gambar) untuk jenjang SMK.')
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Handle explicit image clearing
        if self.cleaned_data.get('clear_question_image') and instance.question_image:
            instance.question_image.delete(save=False)
            instance.question_image = None

        for opt in ['a', 'b', 'c', 'd', 'e']:
            if self.cleaned_data.get(f'clear_image_{opt}'):
                field = getattr(instance, f'image_{opt}', None)
                if field:
                    field.delete(save=False)
                    setattr(instance, f'image_{opt}', None)

        if commit:
            instance.save()
        return instance
