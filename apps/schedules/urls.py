from django.urls import path
from apps.schedules import views

app_name = 'schedules'

urlpatterns = [
    path('', views.ScheduleListView.as_view(), name='list'),
    path('create/', views.ScheduleCreateModalView.as_view(), name='create'),
    path('<uuid:pk>/edit/', views.ScheduleEditModalView.as_view(), name='edit'),
    path('<uuid:pk>/delete/', views.ScheduleDeleteView.as_view(), name='delete'),
    path('bulk-delete/', views.BulkDeleteSchedulesView.as_view(), name='bulk_delete'),
    path('<uuid:pk>/action/<str:action>/', views.ScheduleActionView.as_view(), name='action'),
    path('exam/<uuid:exam_id>/questions/', views.SelectQuestionsView.as_view(), name='select_questions'),
    path('exam/<uuid:exam_id>/toggle-question/<uuid:question_id>/', views.ToggleQuestionView.as_view(), name='toggle_question'),
    path('exam/<uuid:exam_id>/save-questions/', views.SaveQuestionsView.as_view(), name='save_questions'),
]
