from django.db import models
from testmanager.models import Project
from django.utils.timezone import now

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
