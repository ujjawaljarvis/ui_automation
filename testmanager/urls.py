from django.urls import path, include
from rest_framework.routers import DefaultRouter
from testmanager.routes.api import ProjectViewSet, TestPlanViewSet, TestStepViewSet, TestRunViewSet
from testmanager.routes import views
router = DefaultRouter()
router.register(r'projects', ProjectViewSet)
router.register(r'test-plans', TestPlanViewSet)
router.register(r'test-steps', TestStepViewSet)
router.register(r'test-runs', TestRunViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    # HTML Pages
    path('', views.index, name='index'),
    path('projects/', views.project_list, name='project_list'),
    path('projects/<int:project_id>/', views.project_detail, name='project_detail'),
    path('projects/<int:project_id>/test-plans/<int:test_plan_id>/', views.test_plan_detail, name='test_plan_detail'),
    path('create-test-plan/', views.create_test_plan, name='create_test_plan'),
    
    # Project CRUD
    path('projects/create/', views.create_project, name='create_project'),
    path('projects/select/', views.select_project, name='select_project'),
    path('projects/<int:project_id>/edit/', views.edit_project, name='edit_project'),
    path('projects/<int:project_id>/delete/', views.delete_project, name='delete_project'),
    
    # Test Plan CRUD
    path('projects/<int:project_id>/test-plans/create/', views.create_test_plan_for_project, name='create_test_plan_for_project'),
    path('test-plans/<int:test_plan_id>/edit/', views.edit_test_plan, name='edit_test_plan'),
    path('test-plans/<int:test_plan_id>/delete/', views.delete_test_plan, name='delete_test_plan'),
    
    # Test Step CRUD
    path('test-plans/<int:test_plan_id>/steps/create/', views.create_test_steps, name='create_test_steps'),
    path('test-steps/<int:test_step_id>/edit/', views.edit_test_step, name='edit_test_step'),
    path('test-steps/<int:test_step_id>/delete/', views.delete_test_step, name='delete_test_step'),
    
    # Test Run
    path('test-plans/<int:test_plan_id>/run/', views.run_test_plan, name='run_test_plan'),
    path('test-runs/<int:test_run_id>/', views.test_run_detail, name='test_run_detail'),
    path('test-plans/<int:test_plan_id>/runs/', views.get_test_runs, name='get_test_runs'),
]