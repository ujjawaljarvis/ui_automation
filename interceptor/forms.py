# interceptor/forms.py
from django import forms
from interceptor.models import Request
from testmanager.models import Project

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'git_repo']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'}),
            'git_repo': forms.URLInput(attrs={'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'}),
        }

class RequestForm(forms.ModelForm):
    class Meta:
        model = Request
        fields = ['url', 'method', 'headers', 'body', 'wait_time']
        widgets = {
            'url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://example.com/api/endpoint'}),
            'method': forms.Select(attrs={'class': 'form-control'}),
            'headers': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 5, 
                'placeholder': '{\n  "Content-Type": "application/json",\n  "User-Agent": "Mozilla/5.0"\n}'
            }),
            'body': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 5, 
                'placeholder': '{\n  "key": "value"\n}'
            }),
            'wait_time': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 30}),
        }