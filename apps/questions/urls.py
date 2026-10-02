from django.urls import path
from .views import (
    BankSoalView,
    QuestionFilterView,
    QuestionCreateView,
    QuestionEditView,
    QuestionDeleteView,
    QuestionDetailView,
)

app_name = 'questions'

urlpatterns = [
    path('', BankSoalView.as_view(), name='bank_soal'),
    path('filter/', QuestionFilterView.as_view(), name='filter'),
    path('create/', QuestionCreateView.as_view(), name='create'),
    path('<uuid:pk>/edit/', QuestionEditView.as_view(), name='edit'),
    path('<uuid:pk>/delete/', QuestionDeleteView.as_view(), name='delete'),
    path('<uuid:pk>/', QuestionDetailView.as_view(), name='detail'),
]
