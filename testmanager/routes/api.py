from rest_framework import viewsets
from testmanager.models import Project, TestPlan, TestStep, TestRun
from testmanager.serializers import ProjectSerializer, TestPlanSerializer, TestStepSerializer, TestRunSerializer

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

class TestPlanViewSet(viewsets.ModelViewSet):
    queryset = TestPlan.objects.all()
    serializer_class = TestPlanSerializer

class TestStepViewSet(viewsets.ModelViewSet):
    queryset = TestStep.objects.all()
    serializer_class = TestStepSerializer

class TestRunViewSet(viewsets.ModelViewSet):
    queryset = TestRun.objects.all()
    serializer_class = TestRunSerializer
