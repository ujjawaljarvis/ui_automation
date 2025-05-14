from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

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

# -----------------------postman_collection-----------------------
    path('postman_interceptor/projects/<int:project_id>/collections/', views.collection_list, name='collection_list'),
    path('postman_interceptor/projects/<int:project_id>/collections/upload/', views.collection_upload, name='collection_upload'),
    path('postman_interceptor/projects/<int:project_id>/collections/<int:collection_id>/', views.collection_detail, name='collection_detail'),
    path('postman_interceptor/projects/<int:project_id>/collections/<int:collection_id>/run/', views.collection_run, name='collection_run'),
    path('postman_interceptor/projects/<int:project_id>/collections/<int:collection_id>/status/', views.collection_status, name='collection_status'),
    path('postman_interceptor/projects/<int:project_id>/collections/<int:collection_id>/delete/', views.collection_delete, name='collection_delete'),
    path('postman_interceptor/projects/<int:project_id>/collections/<int:collection_id>/requests/<int:request_id>/', views.collection_request_detail, name='collection_request_detail'),
# Add to urls.py
path('projects/<int:project_id>/requests/<int:request_id>/background/<int:background_id>/', views.background_request_detail, name='background_request_detail'),
path('projects/<int:project_id>/collections/<int:collection_id>/requests/<int:request_id>/background/<int:background_id>/', views.collection_background_request_detail, name='collection_background_request_detail'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)