from django.db import models
from django.utils.timezone import now
from django.urls import reverse
import os

class Project(models.Model):
    name = models.CharField(max_length=100)
    git_repo = models.URLField()
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(default=now)

    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('create_test_plan_for_project', args=[self.id])

class TestPlan(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='test_plans')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(default=now)

    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('create_test_steps', args=[self.id])

class TestStep(models.Model):
    ACTION_CHOICES = [
        ('goto', 'Go to URL'),
        ('click', 'Click'),
        ('input', 'Input Text'),
        ('assert', 'Assert'),
        ('manual', 'Manual Step'),
        ('select', 'Select Dropdown'),
        ('wait', 'Wait'),
        ('scrollto', 'Scroll To'),
        ('hover', 'Hover'),
        ('screenshot', 'Take Screenshot'),
    ]
    
    SELECTOR_TYPE_CHOICES = [
        ('byid', 'By ID'),
        ('byxpath', 'By XPath'),
        ('byclass', 'By Class'),
        ('byname', 'By Name'),
        ('bytag', 'By Tag'),
        ('bycss', 'By CSS Selector'),
        ('bylinktext', 'By Link Text'),
    ]
    
    WAIT_TYPE_CHOICES = [
        ('time', 'Wait for Time (seconds)'),
        ('element', 'Wait for Element'),
        ('visible', 'Wait for Element Visible'),
        ('clickable', 'Wait for Element Clickable'),
    ]
    
    test_plan = models.ForeignKey(TestPlan, on_delete=models.CASCADE, related_name='steps')
    step_order = models.IntegerField()
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    selector_type = models.CharField(max_length=20, choices=SELECTOR_TYPE_CHOICES, null=True, blank=True)
    selector_value = models.CharField(max_length=255, null=True, blank=True)
    input_value = models.TextField(null=True, blank=True)
    wait_type = models.CharField(max_length=20, choices=WAIT_TYPE_CHOICES, null=True, blank=True)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(default=now)

    class Meta:
        ordering = ['step_order']

    def __str__(self):
        return f"{self.test_plan.name} - Step {self.step_order}: {self.get_action_display()}"

class TestRun(models.Model):
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]
    
    test_plan = models.ForeignKey(TestPlan, on_delete=models.CASCADE, related_name='runs')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    log = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=now)
    error_screenshot = models.ImageField(upload_to='test_screenshots/', null=True, blank=True)
    
    def __str__(self):
        return f"{self.test_plan.name} - {self.started_at}"
    
    @property
    def duration(self):
        if self.ended_at and self.started_at:
            duration = self.ended_at - self.started_at
            return f"{duration.total_seconds():.2f} seconds"
        return "N/A"
    
    def get_absolute_url(self):
        return reverse('test_run_detail', args=[self.id])

class TestStepResult(models.Model):
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
    ]
    
    test_run = models.ForeignKey(TestRun, on_delete=models.CASCADE, related_name='step_results')
    test_step = models.ForeignKey(TestStep, on_delete=models.SET_NULL, null=True, related_name='results')
    step_order = models.IntegerField()
    action = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    message = models.TextField(null=True, blank=True)
    screenshot = models.ImageField(upload_to='step_screenshots/', null=True, blank=True)
    created_at = models.DateTimeField(default=now)
    
    class Meta:
        ordering = ['step_order']
    
    def __str__(self):
        return f"Step {self.step_order} - {self.action} - {self.status}"