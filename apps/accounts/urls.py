"""URL configuration for Accounts application."""
from django.urls import path
from apps.accounts import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('sso/redirect/', views.sso_login_redirect_view, name='sso_redirect'),
    path('callback/', views.sso_callback_view, name='sso_callback'),
    path('darurat/', views.emergency_login_view, name='emergency_login'),
    path('logout/', views.logout_view, name='logout'),
]
