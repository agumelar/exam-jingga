from django.urls import path
from .views import (
    BankSoalView,
    QuestionFilterView,
    QuestionCreateView,
    QuestionEditView,
    QuestionDeleteView,
    QuestionDetailView,
)
from .import_views import QuestionImportConfirmView, QuestionImportView, QuestionTemplateDownloadView

app_name = 'questions'

urlpatterns = [
    path('', BankSoalView.as_view(), name='bank_soal'),
    path('filter/', QuestionFilterView.as_view(), name='filter'),
    path('create/', QuestionCreateView.as_view(), name='create'),
    path('import/', QuestionImportView.as_view(), name='import'),
    path('import/save/', QuestionImportConfirmView.as_view(), name='import_confirm'),
    path('import/template/', QuestionTemplateDownloadView.as_view(), name='import_template'),
    path('<uuid:pk>/edit/', QuestionEditView.as_view(), name='edit'),
    path('<uuid:pk>/delete/', QuestionDeleteView.as_view(), name='delete'),
    path('<uuid:pk>/', QuestionDetailView.as_view(), name='detail'),
]
