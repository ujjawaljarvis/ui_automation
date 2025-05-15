from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
import json
import os
import tempfile
import json
from .selenium_manager import (
    start_capture, 
    stop_capture, 
    get_capture_status, 
    export_elements_to_csv,
    active_captures,
)
from testmanager.models import Project
from xpath.models import CapturedElement

def xpath_capture_home(request):
    """Home page for XPath capture"""
    projects = Project.objects.all().order_by('-created_at')
    
    if request.method == 'POST':
        url = request.POST.get('url')
        project_id = request.POST.get('project_id')
        new_project_name = request.POST.get('new_project_name')
        
        if not url:
            messages.error(request, 'URL is required')
            return render(request, 'xpath_capture_home.html', {'projects': projects})
        
        # Create new project if specified
        if new_project_name:
            project = Project.objects.create(name=new_project_name)
            project_id = project.id
            messages.success(request, f'Project "{new_project_name}" created successfully')
        
        # Store capture info in session
        request.session['capture_url'] = url
        request.session['capture_project_id'] = project_id
        
        # Redirect to instructions page
        return redirect('xpath_capture_instructions')
    
    return render(request, 'xpath_capture_home.html', {'projects': projects})

def xpath_capture_instructions(request):
    """Instructions page before starting capture"""
    url = request.session.get('capture_url')
    project_id = request.session.get('capture_project_id')
    
    if not url:
        messages.error(request, 'No URL specified')
        return redirect('xpath_capture_home')
    
    project = None
    if project_id:
        project = get_object_or_404(Project, id=project_id)
    
    return render(request, 'xpath_capture_instructions.html', {
        'url': url,
        'project': project,
        'countdown': 20  # 20 seconds countdown
    })

def start_xpath_capture(request):
    """Start the XPath capture process"""
    url = request.session.get('capture_url')
    project_id = request.session.get('capture_project_id')
    
    if not url:
        messages.error(request, 'No URL specified')
        return redirect('xpath_capture_home')
    
    # Start capture session
    capture_id = start_capture(url, project_id)
    
    # Store capture ID in session
    request.session['capture_id'] = capture_id
    
    return redirect('xpath_capture_running')

def xpath_capture_running(request):
    """Page showing the running capture process"""
    capture_id = request.session.get('capture_id')
    
    if not capture_id:
        messages.error(request, 'No active capture session')
        return redirect('xpath_capture_home')
    
    return render(request, 'xpath_capture_running.html', {
        'capture_id': capture_id
    })

@csrf_exempt
def get_capture_status_view(request):
    """API endpoint to get capture status"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method is allowed'})
    
    data = json.loads(request.body)
    capture_id = data.get('capture_id')
    
    if not capture_id:
        return JsonResponse({'success': False, 'error': 'Capture ID is required'})
    
    status = get_capture_status(capture_id)
    
    if status is None:
        return JsonResponse({'success': False, 'error': 'Invalid capture ID'})
    
    return JsonResponse({
        'success': True,
        'status': status
    })

@csrf_exempt
def stop_capture_view(request):
    """API endpoint to stop capture"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method is allowed'})
    
    data = json.loads(request.body)
    capture_id = data.get('capture_id')
    
    if not capture_id:
        return JsonResponse({'success': False, 'error': 'Capture ID is required'})
    
    # Check if capture exists
    if capture_id not in active_captures:
        # Capture might have been removed or never existed
        # Get project ID from session and redirect to results
        project_id = request.session.get('capture_project_id')
        return JsonResponse({
            'success': True,
            'redirect': f'/xpath-capture/results/{project_id}/' if project_id else '/xpath-capture/results/'
        })
    
    # Get status before stopping
    status = get_capture_status(capture_id)
    
    # Stop the capture
    result = stop_capture(capture_id)
    
    # Get project ID from session
    project_id = request.session.get('capture_project_id')
    
    # Redirect to results page
    return JsonResponse({
        'success': True,
        'redirect': f'/xpath/results/{project_id}/' if project_id else '/xpath/results/'
    })

def xpath_capture_results(request, project_id=None):
    """Show capture results"""
    if project_id:
        project = get_object_or_404(Project, id=project_id)
        elements = CapturedElement.objects.filter(project=project).order_by('-created_at')
    else:
        project = None
        elements = CapturedElement.objects.filter(project__isnull=True).order_by('-created_at')
    
    return render(request, 'xpath_capture_results.html', {
        'project': project,
        'elements': elements
    })

def delete_element(request, element_id):
    """Delete a captured element"""
    element = get_object_or_404(CapturedElement, id=element_id)
    project_id = element.project.id if element.project else None
    
    # Delete the element
    element.delete()
    
    messages.success(request, 'Element deleted successfully')
    
    # Redirect back to results page
    if project_id:
        return redirect('xpath_capture_results', project_id=project_id)
    else:
        return redirect('xpath_capture_results')
def get_element_details(request, element_id):
    try:
        element = CapturedElement.objects.get(id=element_id)
        data = {
            "success": True,
            "element": {
                "name": element.name,
                "url": element.url,
                "xpath": element.xpath,
                "css_selector": element.css_selector,
                "id_selector": element.id_selector,
                "class_selector": element.class_selector,
                "tag_name": element.tag_name,
                "html_snippet": element.html_snippet,
                "screenshot": element.screenshot.url if element.screenshot else None,
            }
        }
        return JsonResponse(data)
    except CapturedElement.DoesNotExist:
        return JsonResponse({"success": False, "error": "Element not found"}, status=404)
    
def export_csv(request, project_id=None):
    """Export elements to CSV"""
    if project_id:
        project = get_object_or_404(Project, id=project_id)
        elements = CapturedElement.objects.filter(project=project).order_by('-created_at')
        filename = f"xpath_elements_{project.name}.csv"
    else:
        elements = CapturedElement.objects.filter(project__isnull=True).order_by('-created_at')
        filename = "xpath_elements.csv"
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
        export_elements_to_csv(elements, temp_file.name)
        temp_file_path = temp_file.name
    
    # Read the file and create response
    with open(temp_file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # Delete the temporary file
    os.unlink(temp_file_path)
    
    return response