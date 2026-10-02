from django.contrib import admin
from .models import SchoolSetting


@admin.register(SchoolSetting)
class SchoolSettingAdmin(admin.ModelAdmin):
    list_display = ('school_name', 'academic_year', 'semester', 'exam_name', 'updated_at')

    def has_add_permission(self, request):
        # Disallow adding more than 1 instance
        if self.model.objects.exists():
            return False
        return super().has_add_permission(request)
