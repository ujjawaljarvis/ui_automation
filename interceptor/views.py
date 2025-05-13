# interceptor/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from interceptor.models import Request
from interceptor.models import Project
from interceptor.forms import ProjectForm, RequestForm
from interceptor.utils import run_interceptor
import json
import traceback


def home(request):
    return render(request, 'home.html')


def project_list(request):
    projects = Project.objects.all().order_by('-updated_at')
    return render(request, 'projects/list.html', {'projects': projects})


def project_create(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.save()
            messages.success(request, 'Project created successfully!')
            return redirect('project_detail', project_id=project.id)
    else:
        form = ProjectForm()
    
    return render(request, 'projects/create.html', {'form': form})


def project_detail(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    requests = project.requests.order_by('-created_at')
    return render(request, 'projects/detail.html', {'project': project, 'requests': requests})


def project_delete(request, project_id):
    project = get_object_or_404(Project, id=project_id, user=request.user)
    
    if request.method == 'POST':
        project.delete()
        messages.success(request, 'Project deleted successfully!')
        return redirect('project_list')
    
    return render(request, 'projects/delete.html', {'project': project})


def request_create(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        form = RequestForm(request.POST)
        if form.is_valid():
            req = form.save(commit=False)
            req.project = project
            
            # Run the interceptor
            try:
                har_data = run_interceptor(
                    method=req.method,
                    url=req.url,
                    headers=req.get_headers_dict(),
                    body=req.get_body_dict(),
                    wait_time=req.wait_time
                )
                req.har_data = har_data
                req.save()
                messages.success(request, 'Request intercepted successfully!')
                return redirect('request_detail', project_id=project.id, request_id=req.id)
            except Exception as e:
                messages.error(request, f'Error intercepting request: {str(e)}')
                return render(request, 'requests/create.html', {'form': form, 'project': project, 'error': str(e)})
    else:
        form = RequestForm()
    
    return render(request, 'requests/create.html', {'form': form, 'project': project})


def request_detail(request, project_id, request_id):
    project = get_object_or_404(Project, id=project_id)
    req = get_object_or_404(Request, id=request_id, project=project)
    
    return render(request, 'requests/detail.html', {'project': project, 'request': req})


def request_delete(request, project_id, request_id):
    project = get_object_or_404(Project, id=project_id)
    req = get_object_or_404(Request, id=request_id, project=project)
    
    if request.method == 'POST':
        req.delete()
        messages.success(request, 'Request deleted successfully!')
        return redirect('project_detail', project_id=project.id)
    
    return render(request, 'requests/delete.html', {'project': project, 'request': req})


def request_rerun(request, project_id, request_id):
    project = get_object_or_404(Project, id=project_id)
    req = get_object_or_404(Request, id=request_id, project=project)
    
    try:
        har_data = run_interceptor(
            method=req.method,
            url=req.url,
            headers=req.get_headers_dict(),
            body=req.get_body_dict(),
            wait_time=req.wait_time
        )
        
        # Create a new request with the same parameters but new HAR data
        new_req = Request.objects.create(
            project=project,
            url=req.url,
            method=req.method,
            headers=req.headers,
            body=req.body,
            wait_time=req.wait_time,
            har_data=har_data
        )
        
        messages.success(request, 'Request re-run successfully!')
        return redirect('request_detail', project_id=project.id, request_id=new_req.id)
    except Exception as e:
        messages.error(request, f'Error re-running request: {str(e)}')
        return redirect('request_detail', project_id=project.id, request_id=req.id)

@csrf_exempt
def export_har(request, project_id, request_id):
    project = get_object_or_404(Project, id=project_id)
    req = get_object_or_404(Request, id=request_id, project=project)
    
    response = HttpResponse(json.dumps(req.har_data, indent=2), content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename="{req.method}_{req.url.replace("/", "_")}.har"'
    return response