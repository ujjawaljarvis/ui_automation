
from django.urls import path
from . import views

urlpatterns = [
    path('interceptor/', views.home, name='home'),
    path('interceptor/projects/', views.project_list, name='project_list'),
    path('interceptor/projects/create/', views.project_create, name='project_create'),
    path('interceptor/projects/<int:project_id>/', views.project_detail, name='project_detail'),
    path('interceptor/projects/<int:project_id>/delete/', views.project_delete, name='project_delete'),
    path('interceptor/projects/<int:project_id>/requests/create/', views.request_create, name='request_create'),
    path('interceptor/projects/<int:project_id>/requests/<int:request_id>/', views.request_detail, name='request_detail'),
    path('interceptor/projects/<int:project_id>/requests/<int:request_id>/delete/', views.request_delete, name='request_delete'),
    path('interceptor/projects/<int:project_id>/requests/<int:request_id>/rerun/', views.request_rerun, name='request_rerun'),
    path('interceptor/projects/<int:project_id>/requests/<int:request_id>/export/', views.export_har, name='export_har'),
]