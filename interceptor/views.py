
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from interceptor.models import Request
from interceptor.models import Project, PostmanCollection, CollectionRequest, BackgroundRequest, CollectionBackgroundRequest
from interceptor.forms import ProjectForm, RequestForm, PostmanCollectionForm
from interceptor.utils import run_interceptor
import json
import traceback
from .utils_postman import run_collection
import threading
import os
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
                    wait_time=req.wait_time,
                    capture_background=True
                )
                req.har_data = har_data
                req.save()
                
                # Process background requests
                if har_data and 'log' in har_data and 'entries' in har_data['log']:
                    for entry in har_data['log']['entries']:
                        # Skip the main request
                        if entry.get('_is_main_request', False):
                            continue
                        
                        # Process background request
                        if entry.get('_is_background_request', False):
                            background_req = BackgroundRequest(
                                parent_request=req,
                                url=entry['request']['url'],
                                method=entry['request']['method'],
                                headers=json.dumps([{h['name']: h['value']} for h in entry['request']['headers']]),
                                body=entry['request']['body'],
                                status_code=entry['response']['status'],
                                resource_type=entry.get('_resource_type', 'xhr'),
                                har_data=entry
                            )
                            background_req.save()
                
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


# -----------------------postman_collection.py-----------------------

def collection_list(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    collections = project.collections.order_by('-uploaded_at')
    return render(request, 'collections/list.html', {'project': project, 'collections': collections})


def collection_upload(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        form = PostmanCollectionForm(request.POST, request.FILES)
        if form.is_valid():
            collection = form.save(commit=False)
            collection.project = project
            collection.save()
            messages.success(request, 'Collection uploaded successfully!')
            return redirect('collection_detail', project_id=project.id, collection_id=collection.id)
    else:
        form = PostmanCollectionForm()
    
    return render(request, 'collections/upload.html', {'form': form, 'project': project})


def collection_detail(request, project_id, collection_id):
    project = get_object_or_404(Project, id=project_id)
    collection = get_object_or_404(PostmanCollection, id=collection_id, project=project)
    requests = collection.collection_requests.order_by('-created_at')
    return render(request, 'collections/detail.html', {'project': project, 'collection': collection, 'requests': requests})

def collection_run(request, project_id, collection_id):
    project = get_object_or_404(Project, id=project_id)
    collection = get_object_or_404(PostmanCollection, id=collection_id, project=project)
    
    if collection.is_running:
        messages.error(request, 'Collection is already running!')
        return redirect('collection_detail', project_id=project.id, collection_id=collection.id)

    # Run collection in background thread
    thread = threading.Thread(target=run_collection, args=(collection.id,))
    thread.daemon = True
    thread.start()
    
    messages.success(request, 'Collection is now running. Refresh the page to see results.')
    return redirect('collection_detail', project_id=project.id, collection_id=collection.id)


def collection_request_detail(request, project_id, collection_id, request_id):
    project = get_object_or_404(Project, id=project_id)
    collection = get_object_or_404(PostmanCollection, id=collection_id, project=project)
    collection_request = get_object_or_404(CollectionRequest, id=request_id, collection=collection)
    
    return render(request, 'collections/request_detail.html', {
        'project': project, 
        'collection': collection, 
        'request': collection_request
    })

def collection_status(request, project_id, collection_id):
    """AJAX endpoint to check collection run status"""
    project = get_object_or_404(Project, id=project_id)
    collection = get_object_or_404(PostmanCollection, id=collection_id, project=project)
    
    return JsonResponse({
        'is_running': collection.is_running,
        'total_requests': collection.request_count(),
        'successful_requests': collection.successful_requests(),
        'failed_requests': collection.failed_requests(),
        'last_run': collection.last_run.isoformat() if collection.last_run else None
    })

def collection_delete(request, project_id, collection_id):
    project = get_object_or_404(Project, id=project_id)
    collection = get_object_or_404(PostmanCollection, id=collection_id, project=project)
    
    if request.method == 'POST':
        collection.delete()
        messages.success(request, 'Collection deleted successfully!')
        return redirect('collection_list', project_id=project.id)
    
    return render(request, 'collections/delete.html', {'project': project, 'collection': collection})


# Update in collection_runner.py for collection requests
def process_request_v2(collection, item, name):
    """Process a single request from Postman collection v2.x format and run it"""
    request = item.get('request', {})
    
    if not request:
        return
    
    # Get request method
    method = request.get('method', 'GET')
    
    # Get URL
    url = ""
    if isinstance(request.get('url'), str):
        url = request.get('url', '')
    elif isinstance(request.get('url'), dict):
        url_data = request.get('url', {})
        if 'raw' in url_data:
            url = url_data.get('raw', '')
        else:
            # Construct URL from host and path
            host = '.'.join(url_data.get('host', []))
            path = '/'.join(url_data.get('path', []))
            protocol = url_data.get('protocol', 'https')
            url = f"{protocol}://{host}/{path}"
    
    # Skip if URL is empty
    if not url:
        return
    
    # Get headers
    headers = {}
    for header in request.get('header', []):
        if isinstance(header, dict) and 'key' in header and 'value' in header:
            headers[header.get('key')] = header.get('value')
    
    # Get body
    body = None
    if 'body' in request:
        body_data = request.get('body', {})
        if body_data.get('mode') == 'raw':
            raw_body = body_data.get('raw', '')
            try:
                body = json.loads(raw_body)
            except:
                body = raw_body
        elif body_data.get('mode') == 'formdata':
            form_data = {}
            for param in body_data.get('formdata', []):
                if isinstance(param, dict) and 'key' in param and 'value' in param:
                    form_data[param.get('key')] = param.get('value')
            body = form_data
    
    # Create CollectionRequest object
    collection_request = CollectionRequest(
        collection=collection,
        name=name,
        url=url,
        method=method,
        headers=json.dumps(headers) if headers else None,
        body=json.dumps(body) if body else None
    )
    
    # Run the request through wire.py
    try:
        har_data = run_interceptor(
            method=method,
            url=url,
            headers=headers,
            body=body,
            wait_time=5,
            capture_background=True
        )
        
        # Extract status code
        if har_data and 'log' in har_data and 'entries' in har_data['log'] and har_data['log']['entries']:
            for entry in har_data['log']['entries']:
                if entry.get('_is_main_request', False):
                    collection_request.status_code = entry['response']['status']
                    break
        
        # Save HAR data
        collection_request.har_data = har_data
        collection_request.save()
        
        # Process background requests
        if har_data and 'log' in har_data and 'entries' in har_data['log']:
            for entry in har_data['log']['entries']:
                # Skip the main request
                if entry.get('_is_main_request', False):
                    continue
                
                # Process background request
                if entry.get('_is_background_request', False):
                    background_req = CollectionBackgroundRequest(
                        parent_request=collection_request,
                        url=entry['request']['url'],
                        method=entry['request']['method'],
                        headers=json.dumps([{h['name']: h['value']} for h in entry['request']['headers']]),
                        body=entry['request']['body'],
                        status_code=entry['response']['status'],
                        resource_type=entry.get('_resource_type', 'xhr'),
                        har_data=entry
                    )
                    background_req.save()
        
    except Exception as e:
        # If request fails, save error
        collection_request.status_code = 0
        collection_request.har_data = {
            'error': str(e)
        }
        collection_request.save()

def background_request_detail(request, project_id, request_id, background_id):
    project = get_object_or_404(Project, id=project_id)
    req = get_object_or_404(Request, id=request_id, project=project)
    background_req = get_object_or_404(BackgroundRequest, id=background_id, parent_request=req)
    
    return render(request, 'requests/background_detail.html', {
        'project': project,
        'request': req,
        'background_request': background_req
    })


def collection_background_request_detail(request, project_id, collection_id, request_id, background_id):
    project = get_object_or_404(Project, id=project_id)
    collection = get_object_or_404(PostmanCollection, id=collection_id, project=project)
    req = get_object_or_404(CollectionRequest, id=request_id, collection=collection)
    background_req = get_object_or_404(CollectionBackgroundRequest, id=background_id, parent_request=req)
    
    return render(request, 'collections/background_detail.html', {
        'project': project,
        'collection': collection,
        'request': req,
        'background_request': background_req
    })