from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
import subprocess
import sys
import json

from testmanager.models import Project, TestPlan, TestStep, TestRun
from testmanager.forms import ProjectForm, TestPlanForm, TestStepFormSet, TestStepForm

def index(request):
    """Render the landing page"""
    return render(request, 'index.html')

def project_list(request):
    """Render the projects list page"""
    projects = Project.objects.all()
    
    # Get selected project and test plan from query parameters
    project_id = request.GET.get('project')
    test_plan_id = request.GET.get('test_plan')
    
    selected_project = None
    selected_test_plan = None
    test_plans = []
    test_steps = []
    
    if project_id:
        selected_project = get_object_or_404(Project, id=project_id)
        test_plans = TestPlan.objects.filter(project=selected_project)
        
        if test_plan_id:
            selected_test_plan = get_object_or_404(TestPlan, id=test_plan_id)
            test_steps = TestStep.objects.filter(test_plan=selected_test_plan).order_by('step_order')
    
    context = {
        'projects': projects,
        'selected_project': selected_project,
        'test_plans': test_plans,
        'selected_test_plan': selected_test_plan,
        'test_steps': test_steps,
    }
    
    return render(request, 'projects.html', context)

def project_detail(request, project_id):
    """Redirect to project list with project selected"""
    return redirect(f"{reverse('project_list1')}?project={project_id}")

def test_plan_detail(request, project_id, test_plan_id):
    """Redirect to project list with project and test plan selected"""
    return redirect(f"{reverse('project_list1')}?project={project_id}&test_plan={test_plan_id}")

def create_test_plan(request):
    """Render the create test plan page"""
    # Check if we're coming from a specific step
    project_created = request.session.get('project_created', False)
    test_plan_created = request.session.get('test_plan_created', False)
    
    # Get existing projects for selection
    existing_projects = Project.objects.all()
    
    # Check if we should show existing projects selection
    show_existing = request.GET.get('show_existing', 'false') == 'true'
    
    # Get selected project and test plan if they exist
    selected_project = None
    selected_test_plan = None
    
    if project_created:
        project_id = request.session.get('selected_project_id')
        if project_id:
            selected_project = get_object_or_404(Project, id=project_id)
    
    if test_plan_created:
        test_plan_id = request.session.get('selected_test_plan_id')
        if test_plan_id:
            selected_test_plan = get_object_or_404(TestPlan, id=test_plan_id)
    
    context = {
        'project_created': project_created,
        'test_plan_created': test_plan_created,
        'existing_projects': existing_projects,
        'show_existing': show_existing,
        'selected_project': selected_project,
        'selected_test_plan': selected_test_plan,
    }
    
    return render(request, 'create_test_plan.html', context)

@transaction.atomic
def create_project(request):
    """Create a new project"""
    if request.method == 'POST':
        name = request.POST.get('name')
        git_repo = request.POST.get('git_repo')
        
        if not name or not git_repo:
            messages.error(request, 'Project name and Git repository URL are required.')
            return redirect('create_test_plan')
        
        project = Project.objects.create(name=name, git_repo=git_repo)
        
        # Store in session that we've created a project
        request.session['project_created'] = True
        request.session['selected_project_id'] = project.id
        
        return redirect('create_test_plan')
    
    return redirect('create_test_plan')

def select_project(request):
    """Select an existing project"""
    if request.method == 'POST':
        project_id = request.POST.get('project_id')
        
        if not project_id:
            messages.error(request, 'Please select a project.')
            return redirect('create_test_plan')
        
        # Store in session that we've selected a project
        request.session['project_created'] = True
        request.session['selected_project_id'] = project_id
        
        return redirect('create_test_plan')
    
    return redirect('create_test_plan')

@transaction.atomic
def create_test_plan_for_project(request, project_id):
    """Create a test plan for a specific project"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        
        if not name:
            messages.error(request, 'Test plan name is required.')
            return redirect('create_test_plan')
        
        test_plan = TestPlan.objects.create(project=project, name=name)
        
        # Store in session that we've created a test plan
        request.session['test_plan_created'] = True
        request.session['selected_test_plan_id'] = test_plan.id
        
        return redirect('create_test_plan')
    
    return redirect('create_test_plan')

@transaction.atomic
def create_test_steps(request, test_plan_id):
    """Create test steps for a test plan"""
    test_plan = get_object_or_404(TestPlan, id=test_plan_id)
    
    if request.method == 'POST':
        # First, delete any existing steps
        TestStep.objects.filter(test_plan=test_plan).delete()
        
        # Get all form fields
        form_data = request.POST
        
        # Find all step indices by looking for step_order_X fields
        step_indices = []
        for key in form_data:
            if key.startswith('step_order_'):
                step_index = key.split('_')[-1]
                step_indices.append(step_index)
        
        # Create test steps
        for index in step_indices:
            step_order = form_data.get(f'step_order_{index}')
            action = form_data.get(f'action_{index}')
            selector_type = form_data.get(f'selector_type_{index}')
            selector_value = form_data.get(f'selector_value_{index}')
            input_value = form_data.get(f'input_value_{index}')
            
            # Validate required fields based on action type
            if action == 'goto' and not input_value:
                messages.error(request, f'URL is required for "Goto" action in step {step_order}.')
                continue
                
            if action in ['click', 'input', 'assert'] and (not selector_type or not selector_value):
                messages.error(request, f'Selector type and value are required for "{action}" action in step {step_order}.')
                continue
                
            if action == 'input' and not input_value:
                messages.error(request, f'Input value is required for "Input" action in step {step_order}.')
                continue
            
            # Create the test step
            TestStep.objects.create(
                test_plan=test_plan,
                step_order=step_order,
                action=action,
                selector_type=selector_type if action not in ['goto', 'manual'] else None,
                selector_value=selector_value if action not in ['goto', 'manual'] else None,
                input_value=input_value
            )
        
        # Clear session variables
        request.session['project_created'] = False
        request.session['test_plan_created'] = False
        request.session['selected_project_id'] = None
        request.session['selected_test_plan_id'] = None
        
        messages.success(request, 'Test steps created successfully!')
        return redirect('test_plan_detail', project_id=test_plan.project.id, test_plan_id=test_plan.id)
    
    return redirect('create_test_plan')

def edit_project(request, project_id):
    """Edit an existing project"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, 'Project updated successfully!')
            return redirect('project_detail1', project_id=project.id)
    else:
        form = ProjectForm(instance=project)
    
    context = {
        'form': form,
        'project': project,
    }
    
    return render(request, 'edit_project.html', context)

def edit_test_plan(request, test_plan_id):
    """Edit an existing test plan and its steps"""
    test_plan = get_object_or_404(TestPlan, id=test_plan_id)
    
    if request.method == 'POST':
        form = TestPlanForm(request.POST, instance=test_plan)
        formset = TestStepFormSet(request.POST, instance=test_plan)
        
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, 'Test plan updated successfully!')
            return redirect('test_plan_detail', project_id=test_plan.project.id, test_plan_id=test_plan.id)
    else:
        form = TestPlanForm(instance=test_plan)
        formset = TestStepFormSet(instance=test_plan)
    
    context = {
        'form': form,
        'formset': formset,
        'test_plan': test_plan,
    }
    
    return render(request, 'edit_test_plan.html', context)

def edit_test_step(request, test_step_id):
    """Edit a single test step"""
    test_step = get_object_or_404(TestStep, id=test_step_id)
    
    if request.method == 'POST':
        form = TestStepForm(request.POST, instance=test_step)
        if form.is_valid():
            form.save()
            messages.success(request, 'Test step updated successfully!')
            return redirect('test_plan_detail', project_id=test_step.test_plan.project.id, test_plan_id=test_step.test_plan.id)
    else:
        form = TestStepForm(instance=test_step)
    
    context = {
        'form': form,
        'test_step': test_step,
    }
    
    return render(request, 'edit_test_step.html', context)

@require_http_methods(["POST"])
def delete_project(request, project_id):
    """Delete a project"""
    project = get_object_or_404(Project, id=project_id)
    project.delete()
    messages.success(request, 'Project deleted successfully!')
    return redirect('project_list')

@require_http_methods(["POST"])
def delete_test_plan(request, test_plan_id):
    """Delete a test plan"""
    test_plan = get_object_or_404(TestPlan, id=test_plan_id)
    project_id = test_plan.project.id
    test_plan.delete()
    messages.success(request, 'Test plan deleted successfully!')
    return redirect('project_detail1', project_id=project_id)

@require_http_methods(["POST"])
def delete_test_step(request, test_step_id):
    """Delete a test step"""
    test_step = get_object_or_404(TestStep, id=test_step_id)
    project_id = test_step.test_plan.project.id
    test_plan_id = test_step.test_plan.id
    test_step.delete()
    
    # Reorder remaining steps
    remaining_steps = TestStep.objects.filter(test_plan_id=test_plan_id).order_by('step_order')
    for i, step in enumerate(remaining_steps, 1):
        step.step_order = i
        step.save()
    
    messages.success(request, 'Test step deleted successfully!')
    return redirect('test_plan_detail', project_id=project_id, test_plan_id=test_plan_id)

def run_test_plan(request, test_plan_id):
    """Run a test plan and show results"""
    test_plan = get_object_or_404(TestPlan, id=test_plan_id)
    
    # Create a new test run
    test_run = TestRun.objects.create(
        test_plan=test_plan,
        status='running',
        started_at=timezone.now()
    )
    
    # In a production environment, you would run this asynchronously
    # For simplicity, we'll run it synchronously here
    try:
        # Run the test script as a subprocess
        cmd = [sys.executable, 'script.py', str(test_plan_id)]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        # Update test run with results
        if process.returncode == 0:
            test_run.status = 'success'
            test_run.log = stdout.decode('utf-8')
        else:
            test_run.status = 'failed'
            test_run.log = f"STDOUT:\n{stdout.decode('utf-8')}\n\nSTDERR:\n{stderr.decode('utf-8')}"
    except Exception as e:
        test_run.status = 'failed'
        test_run.log = f"Error running test: {str(e)}"
    
    test_run.ended_at = timezone.now()
    test_run.save()
    
    return redirect('test_run_detail', test_run_id=test_run.id)

def test_run_detail(request, test_run_id):
    """Show test run details"""
    test_run = get_object_or_404(TestRun, id=test_run_id)
    
    # Calculate duration
    if test_run.ended_at and test_run.started_at:
        duration = test_run.ended_at - test_run.started_at
        # Format as minutes:seconds
        minutes, seconds = divmod(duration.total_seconds(), 60)
        test_run.duration = f"{int(minutes)}m {int(seconds)}s"
    
    context = {
        'test_run': test_run,
    }
    
    return render(request, 'test_run.html', context)

def get_test_runs(request, test_plan_id):
    """Get all test runs for a test plan"""
    test_plan = get_object_or_404(TestPlan, id=test_plan_id)
    test_runs = TestRun.objects.filter(test_plan=test_plan).order_by('-started_at')
    
    context = {
        'test_plan': test_plan,
        'test_runs': test_runs,
    }
    
    return render(request, 'test_runs.html', context)
