from django.db import models
from django.utils.timezone import now

class Project(models.Model):
    name = models.CharField(max_length=100)
    git_repo = models.URLField()
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(default=now)

    def __str__(self):
        return self.name

class TestPlan(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='test_plans')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(default=now)

    def __str__(self):
        return self.name

class TestStep(models.Model):
    ACTION_CHOICES = [
        ('goto', 'Go to URL'),
        ('click', 'Click'),
        ('input', 'Input Text'),
        ('assert', 'Assert'),
        ('manual', 'Manual Step'),
    ]
    
    SELECTOR_TYPE_CHOICES = [
        ('byid', 'By ID'),
        ('byxpath', 'By XPath'),
        ('byclass', 'By Class'),
        ('byname', 'By Name'),
        ('bytag', 'By Tag'),
    ]
    
    test_plan = models.ForeignKey(TestPlan, on_delete=models.CASCADE, related_name='steps')
    step_order = models.IntegerField()
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    selector_type = models.CharField(max_length=20, choices=SELECTOR_TYPE_CHOICES, null=True, blank=True)
    selector_value = models.CharField(max_length=255, null=True, blank=True)
    input_value = models.TextField(null=True, blank=True)
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

    def __str__(self):
        return f"{self.test_plan.name} - {self.started_at}"
    
class CapturedElement(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='captured_elements', null=True, blank=True)
    name = models.CharField(max_length=255)
    url = models.URLField()
    xpath = models.TextField()
    css_selector = models.TextField(null=True, blank=True)
    id_selector = models.CharField(max_length=255, null=True, blank=True)
    class_selector = models.CharField(max_length=255, null=True, blank=True)
    tag_name = models.CharField(max_length=50)
    html_snippet = models.TextField(null=True, blank=True)
    screenshot = models.ImageField(upload_to='element_screenshots/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.xpath}"