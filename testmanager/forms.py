from django import forms
from django.forms import inlineformset_factory
from testmanager.models import Project, TestPlan, TestStep

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'git_repo']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'}),
            'git_repo': forms.URLInput(attrs={'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'}),
        }

class TestPlanForm(forms.ModelForm):
    class Meta:
        model = TestPlan
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'}),
        }

class TestStepForm(forms.ModelForm):
    class Meta:
        model = TestStep
        fields = ['step_order', 'action', 'selector_type', 'selector_value', 'input_value']
        widgets = {
            'step_order': forms.NumberInput(attrs={'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'}),
            'action': forms.Select(attrs={'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'}),
            'selector_type': forms.Select(attrs={'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'}),
            'selector_value': forms.TextInput(attrs={'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'}),
            'input_value': forms.TextInput(attrs={'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'}),
        }

# Create a formset for test steps
TestStepFormSet = inlineformset_factory(
    TestPlan, 
    TestStep, 
    form=TestStepForm,
    extra=1,
    can_delete=True
)