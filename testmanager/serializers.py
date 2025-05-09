from rest_framework import serializers
from .models import Project, TestPlan, TestStep, TestRun

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'

class TestPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestPlan
        fields = '__all__'
    
    def create(self, validated_data):
        steps_data = validated_data.pop('steps', [])  # default to empty list
        test_plan = TestPlan.objects.create(**validated_data)
        for step_data in steps_data:
            TestStep.objects.create(plan=test_plan, **step_data)
        return test_plan

class TestStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestStep
        fields = '__all__'
    

class TestRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestRun
        fields = '__all__'
