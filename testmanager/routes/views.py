from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.urls import reverse
from django.conf import settings
from django.utils.timezone import now
import json
import os
import subprocess
import threading
from testmanager.models import Project, TestPlan, TestStep, TestRun, TestStepResult
from testmanager.forms import ProjectForm, TestPlanForm, TestStepFormSet, TestStepForm

def index(request):
    """Home page view"""
    projects = Project.objects.all().order_by('-created_at')[:5]
    recent_test_runs = TestRun.objects.all().order_by('-created_at')[:5]
    
    return render(request, 'index.html', {
        'projects': projects,
        'recent_test_runs': recent_test_runs
    })

def project_list(request):
    """List all projects"""
    projects = Project.objects.all().order_by('-created_at')
    return render(request, 'projects.html', {'projects': projects})

def project_detail(request, project_id):
    """View project details"""
    project = get_object_or_404(Project, id=project_id)
    test_plans = project.test_plans.all().order_by('-created_at')
    
    return render(request, 'projects.html', {
        'projects': Project.objects.all().order_by('-created_at'),
        'selected_project': project,
        'test_plans': test_plans
    })

def create_project(request):
    """Create a new project"""
    if request.method == 'POST':
        name = request.POST.get('name')
        git_repo = request.POST.get('git_repo')
        redirect_to = request.POST.get('redirect_to', 'project_detail1')
        
        if not name or not git_repo:
            messages.error(request, 'Please provide both name and git repository URL')
            return redirect('create_project')
        
        project = Project.objects.create(
            name=name,
            git_repo=git_repo
        )
        
        messages.success(request, f'Project "{name}" created successfully!')
        
        # Automatic redirect to test plan creation
        if redirect_to == 'create_test_plan':
            return redirect('create_test_plan_for_project', project_id=project.id)
        
        return redirect('project_detail1', project_id=project.id)
    
    return render(request, 'projects/create.html')

def select_project(request):
    """Select an existing project"""
    if request.method == 'POST':
        project_id = request.POST.get('project_id')
        redirect_to = request.POST.get('redirect_to', 'project_detail1')
        
        if not project_id:
            messages.error(request, 'Please select a project')
            return redirect('create_test_plan')
        
        project = get_object_or_404(Project, id=project_id)
        
        # Automatic redirect to test plan creation
        if redirect_to == 'create_test_plan':
            return redirect('create_test_plan_for_project', project_id=project.id)
        
        return redirect('project_detail1', project_id=project.id)
    
    return redirect('create_test_plan')

def create_test_plan(request):
    """Create a new test plan (step 1: select project)"""
    existing_projects = Project.objects.all().order_by('-created_at')
    show_existing = request.GET.get('show_existing', 'false') == 'true'
    
    return render(request, 'create_test_plan.html', {
        'existing_projects': existing_projects,
        'show_existing': show_existing,
        'current_step': 1
    })

def create_test_plan_for_project(request, project_id):
    """Create a test plan for a specific project (step 2)"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        redirect_to = request.POST.get('redirect_to', 'test_plan_detail')
        
        if not name:
            messages.error(request, 'Please provide a name for the test plan')
            return redirect('create_test_plan_for_project', project_id=project.id)
        
        test_plan = TestPlan.objects.create(
            project=project,
            name=name
        )
        
        messages.success(request, f'Test plan "{name}" created successfully!')
        
        # Automatic redirect to add test steps
        if redirect_to == 'create_test_plan':
            return redirect('create_test_steps', test_plan_id=test_plan.id)
        
        return redirect('test_plan_detail', project_id=project.id, test_plan_id=test_plan.id)
    
    existing_projects = Project.objects.all().order_by('-created_at')
    
    return render(request, 'create_test_plan.html', {
        'existing_projects': existing_projects,
        'selected_project': project,
        'current_step': 2
    })

def test_plan_detail(request, project_id, test_plan_id):
    """View test plan details"""
    project = get_object_or_404(Project, id=project_id)
    test_plan = get_object_or_404(TestPlan, id=test_plan_id, project=project)
    steps = test_plan.steps.all().order_by('step_order')
    recent_runs = test_plan.runs.all().order_by('-created_at')[:5]
    
    return render(request, 'projects.html', {
        'projects': Project.objects.all().order_by('-created_at'),
        'selected_project': project,
        'test_plans': project.test_plans.all().order_by('-created_at'),
        'selected_test_plan': test_plan,
        'test_steps': steps
    })

def create_test_steps(request, test_plan_id):
    """Add test steps to a test plan (step 3)"""
    test_plan = get_object_or_404(TestPlan, id=test_plan_id)
    project = test_plan.project
    
    if request.method == 'POST':
        # Get all step data from the form
        step_count = 0
        for key in request.POST:
            if key.startswith('step_order_'):
                step_count = max(step_count, int(key.split('_')[-1]))
        
        # Process each step
        for i in range(1, step_count + 1):
            step_order = request.POST.get(f'step_order_{i}')
            action = request.POST.get(f'action_{i}')
            
            if not step_order or not action:
                continue
            
            # Get selector type and value if applicable
            selector_type = request.POST.get(f'selector_type_{i}')
            selector_value = request.POST.get(f'selector_value_{i}')
            input_value = request.POST.get(f'input_value_{i}')
            wait_type = request.POST.get(f'wait_type_{i}')
            
            # Create the test step
            TestStep.objects.create(
                test_plan=test_plan,
                step_order=step_order,
                action=action,
                selector_type=selector_type,
                selector_value=selector_value,
                input_value=input_value,
                wait_type=wait_type
            )
        
        messages.success(request, 'Test steps added successfully!')
        return redirect('test_plan_detail', project_id=project.id, test_plan_id=test_plan.id)
    
    existing_projects = Project.objects.all().order_by('-created_at')
    
    return render(request, 'create_test_plan.html', {
        'existing_projects': existing_projects,
        'selected_project': project,
        'selected_test_plan': test_plan,
        'current_step': 3
    })

def edit_project(request, project_id):
    """Edit a project"""
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

def delete_project(request, project_id):
    """Delete a project"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        project.delete()
        messages.success(request, f'Project "{project.name}" deleted successfully!')
        return redirect('project_list1')
    
    return render(request, 'projects/delete.html', {'project': project})

def edit_test_plan(request, test_plan_id):
    """Edit a test plan"""
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

def delete_test_plan(request, test_plan_id):
    """Delete a test plan"""
    test_plan = get_object_or_404(TestPlan, id=test_plan_id)
    project_id = test_plan.project.id
    
    if request.method == 'POST':
        test_plan.delete()
        messages.success(request, f'Test plan "{test_plan.name}" deleted successfully!')
        return redirect('project_detail1', project_id=project_id)
    
    return render(request, 'test_plans/delete.html', {'test_plan': test_plan})

def edit_test_step(request, test_step_id):
    """Edit a test step"""
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

def delete_test_step(request, test_step_id):
    """Delete a test step"""
    test_step = get_object_or_404(TestStep, id=test_step_id)
    test_plan = test_step.test_plan
    
    if request.method == 'POST':
        test_step.delete()
        
        # Reorder remaining steps
        steps = test_plan.steps.all().order_by('step_order')
        for i, step in enumerate(steps, 1):
            step.step_order = i
            step.save()
        
        messages.success(request, 'Test step deleted successfully!')
        return redirect('test_plan_detail', project_id=test_plan.project.id, test_plan_id=test_plan.id)
    
    return render(request, 'test_steps/delete.html', {'test_step': test_step})

def run_test_plan(request, test_plan_id):
    """Run a test plan"""
    test_plan = get_object_or_404(TestPlan, id=test_plan_id)
    
    # Create a new test run
    test_run = TestRun.objects.create(
        test_plan=test_plan,
        status='running',
        started_at=now()
    )
    
    # Run the test plan in a separate thread
    thread = threading.Thread(
        target=run_test_in_background,
        args=(test_plan_id, test_run.id)
    )
    thread.daemon = True
    thread.start()
    
    messages.success(request, f'Test plan "{test_plan.name}" is now running!')
    return redirect('test_run_detail', test_run_id=test_run.id)

def run_test_in_background(test_plan_id, test_run_id):
    """Run the test plan in a background thread"""
    script_path = os.path.join(settings.BASE_DIR, 'script.py')
    subprocess.run([
        'python', script_path, str(test_plan_id), str(test_run_id)
    ])

def test_run_detail(request, test_run_id):
    """View test run details"""
    test_run = get_object_or_404(TestRun, id=test_run_id)
    step_results = test_run.step_results.all().order_by('step_order')
    
    return render(request, 'test_run.html', {
        'test_run': test_run,
        'step_results': step_results
    })

def get_test_runs(request, test_plan_id):
    """List all test runs for a test plan"""
    test_plan = get_object_or_404(TestPlan, id=test_plan_id)
    test_runs = test_plan.runs.all().order_by('-created_at')
    
    return render(request, 'test_runs.html', {
        'test_plan': test_plan,
        'test_runs': test_runs
    })

@csrf_exempt
def get_test_run_status(request, test_run_id):
    """AJAX endpoint to get test run status"""
    test_run = get_object_or_404(TestRun, id=test_run_id)
    
    return JsonResponse({
        'status': test_run.status,
        'log': test_run.log,
        'ended_at': test_run.ended_at.isoformat() if test_run.ended_at else None,
        'duration': test_run.duration,
        'has_error_screenshot': bool(test_run.error_screenshot)
    })