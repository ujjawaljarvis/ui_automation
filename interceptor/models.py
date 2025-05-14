from django.db import models
import json
from testmanager.models import Project

class PostmanCollection(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='collections')
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to='postman_collections/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_running = models.BooleanField(default=False)
    last_run = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name
    
    def request_count(self):
        return self.collection_requests.count()
    
    def successful_requests(self):
        return self.collection_requests.filter(status_code__lt=400).count()
    
    def failed_requests(self):
        return self.collection_requests.filter(status_code__gte=400).count()

class CollectionRequest(models.Model):
    collection = models.ForeignKey(PostmanCollection, on_delete=models.CASCADE, related_name='collection_requests')
    name = models.CharField(max_length=255)
    url = models.URLField(max_length=500)
    method = models.CharField(max_length=10)
    headers = models.TextField(blank=True, null=True)
    body = models.TextField(blank=True, null=True)
    status_code = models.IntegerField(null=True, blank=True)
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


class BackgroundRequest(models.Model):
    """Background requests captured during a regular request"""
    parent_request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name='background_requests')
    url = models.URLField(max_length=500)
    method = models.CharField(max_length=10)
    headers = models.TextField(blank=True, null=True)
    body = models.TextField(blank=True, null=True)
    status_code = models.IntegerField(null=True, blank=True)
    resource_type = models.CharField(max_length=20, default='xhr')  # xhr, fetch, script, etc.
    har_data = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.method} {self.url} ({self.status_code})"

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

class CollectionBackgroundRequest(models.Model):
    """Background requests captured during a collection request"""
    parent_request = models.ForeignKey(CollectionRequest, on_delete=models.CASCADE, related_name='background_requests')
    url = models.URLField(max_length=500)
    method = models.CharField(max_length=10)
    headers = models.TextField(blank=True, null=True)
    body = models.TextField(blank=True, null=True)
    status_code = models.IntegerField(null=True, blank=True)
    resource_type = models.CharField(max_length=20, default='xhr')  # xhr, fetch, script, etc.
    har_data = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.method} {self.url} ({self.status_code})"

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