from django.db import models
import json
from testmanager.models import Project

class Request(models.Model):
    METHOD_CHOICES = [
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('DELETE', 'DELETE'),
        ('PATCH', 'PATCH'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='requests')
    url = models.URLField(max_length=500)
    method = models.CharField(max_length=10, choices=METHOD_CHOICES, default='GET')
    headers = models.TextField(blank=True, null=True)
    body = models.TextField(blank=True, null=True)
    wait_time = models.IntegerField(default=5)
    har_data = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.method} {self.url}"
    
    def get_headers_dict(self):
        if not self.headers:
            return {}
        try:
            return json.loads(self.headers)
        except:
            return {}
    
    def get_body_dict(self):
        if not self.body:
            return {}
        try:
            return json.loads(self.body)
        except:
            return {}
    
    def get_status_code(self):
        if not self.har_data:
            return None
        try:
            return self.har_data['log']['entries'][0]['response']['status']
        except (KeyError, IndexError):
            return None