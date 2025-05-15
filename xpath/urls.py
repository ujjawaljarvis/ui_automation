from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from xpath import views


urlpatterns = [
    # XPath Capture URLs
    path('xpath/', views.xpath_capture_home, name='xpath_capture_home'),
    path('xpath/instructions/', views.xpath_capture_instructions, name='xpath_capture_instructions'),
    path('xpath/start/', views.start_xpath_capture, name='start_xpath_capture'),
    path('xpath/running/', views.xpath_capture_running, name='xpath_capture_running'),
    path('xpath/status/', views.get_capture_status_view, name='get_capture_status'),
    path('xpath/stop/', views.stop_capture_view, name='stop_capture'),
    path('xpath/results/', views.xpath_capture_results, name='xpath_capture_results'),
    path('xpath/results/<int:project_id>/', views.xpath_capture_results, name='xpath_capture_results'),
    path('xpath/delete-element/<int:element_id>/', views.delete_element, name='delete_element'),
    path('xpath/export-csv/', views.export_csv, name='export_csv'),
    path('xpath/export-csv/<int:project_id>/', views.export_csv, name='export_csv'),
    path('xpath-capture/element/<int:element_id>/', views.get_element_details, name='element_details'),
]


if settings.DEBUG:
    if getattr(settings, "STATICFILES_DIRS", None):
        urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
