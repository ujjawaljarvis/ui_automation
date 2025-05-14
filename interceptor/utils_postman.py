import json
import tempfile
import os
import subprocess
import re
from django.utils import timezone
from .models import PostmanCollection, CollectionRequest, CollectionBackgroundRequest

def extract_variables_from_collection(collection_data):
    """Extract variables from a Postman collection"""
    variables = {}
    
    # Extract collection variables
    if 'variable' in collection_data:
        for var in collection_data.get('variable', []):
            if isinstance(var, dict) and 'key' in var and 'value' in var:
                variables[var['key']] = var['value']
    
    # Extract environment variables if present
    if 'environment' in collection_data:
        env_data = collection_data.get('environment', {})
        for var in env_data.get('values', []):
            if isinstance(var, dict) and 'key' in var and 'value' in var:
                variables[var['key']] = var['value']
    
    return variables

def replace_variables(text, variables):
    """Replace {{var}} placeholders with actual values"""
    if not isinstance(text, str):
        return text
    
    # Find all variables in the text
    pattern = r'\{\{([^}]+)\}\}'
    matches = re.findall(pattern, text)
    
    # Replace each variable
    for match in matches:
        var_name = match.strip()
        if var_name in variables:
            text = text.replace(f"{{{{{var_name}}}}}", str(variables[var_name]))
    
    return text

def replace_variables_in_dict(data, variables):
    """Recursively replace variables in a dict or list"""
    if isinstance(data, dict):
        return {k: replace_variables_in_dict(v, variables) for k, v in data.items()}
    elif isinstance(data, list):
        return [replace_variables_in_dict(v, variables) for v in data]
    elif isinstance(data, str):
        return replace_variables(data, variables)
    else:
        return data

def parse_postman_collection(collection, variables=None):
    """Parse a Postman collection file and extract requests"""
    try:
        with open(collection.file.path, 'r') as f:
            collection_data = json.load(f)
        
        # Extract variables from collection
        collection_variables = extract_variables_from_collection(collection_data)
        
        # Merge with provided variables, with provided variables taking precedence
        if variables:
            collection_variables.update(variables)
        else:
            variables = collection_variables
        
        requests = []
        
        if 'item' in collection_data:
            requests = extract_requests_v2(collection_data, variables=variables)
        elif 'requests' in collection_data:
            requests = extract_requests_v1(collection_data, variables=variables)
        elif 'request' in collection_data:
            requests = [extract_single_request(collection_data, variables=variables)]
        
        return requests
    
    except Exception as e:
        raise Exception(f"Error parsing Postman collection: {str(e)}")

def extract_requests_v2(collection_data, parent_name="", variables=None):
    """Extract requests from a Postman v2.x collection"""
    variables = variables or {}
    requests = []
    
    # Process collection variables if present
    if 'variable' in collection_data:
        for var in collection_data.get('variable', []):
            if isinstance(var, dict) and 'key' in var and 'value' in var:
                variables[var['key']] = var['value']
    
    for item in collection_data.get('item', []):
        # Process folder/item variables if present
        item_variables = variables.copy()
        if 'variable' in item:
            for var in item.get('variable', []):
                if isinstance(var, dict) and 'key' in var and 'value' in var:
                    item_variables[var['key']] = var['value']
        
        if 'item' in item:
            # This is a folder
            folder_name = item.get('name', '')
            folder_path = f"{parent_name}/{folder_name}" if parent_name else folder_name
            requests.extend(extract_requests_v2(item, folder_path, variables=item_variables))
        elif 'request' in item:
            # This is a request
            request_name = item.get('name', '')
            request_path = f"{parent_name}/{request_name}" if parent_name else request_name
            
            # Process pre-request script for variables
            if 'event' in item:
                for event in item.get('event', []):
                    if event.get('listen') == 'prerequest' and 'script' in event:
                        script = event.get('script', {})
                        if 'exec' in script:
                            # Extract variables from script
                            for line in script.get('exec', []):
                                if 'pm.variables.set' in line or 'pm.collectionVariables.set' in line:
                                    var_match = re.search(r'set$$"([^"]+)",\s*([^)]+)$$', line)
                                    if var_match:
                                        var_name = var_match.group(1)
                                        var_value = var_match.group(2).strip('"\'')
                                        item_variables[var_name] = var_value
            
            request_data = extract_single_request(item, name=request_path, variables=item_variables)
            if request_data:
                requests.append(request_data)
    
    return requests

def extract_requests_v1(collection_data, variables=None):
    """Extract requests from a Postman v1.x collection"""
    variables = variables or {}
    requests = []
    
    for request in collection_data.get('requests', []):
        url = replace_variables(request.get('url', ''), variables)
        headers = {}
        for header in request.get('headers', '').split('\n'):
            if ':' in header:
                key, value = header.split(':', 1)
                headers[key.strip()] = replace_variables(value.strip(), variables)
        
        body = None
        if 'rawModeData' in request and request.get('dataMode') == 'raw':
            try:
                body_str = replace_variables(request.get('rawModeData', '{}'), variables)
                body = json.loads(body_str)
            except:
                body = body_str
        
        requests.append({
            'name': replace_variables(request.get('name', ''), variables),
            'method': request.get('method', 'GET'),
            'url': url,
            'headers': headers,
            'body': body
        })
    
    return requests

def extract_single_request(item, name=None, variables=None):
    """Extract a single request from a Postman item"""
    variables = variables or {}
    request = item.get('request', {})
    
    if not request:
        return None
    
    request_name = replace_variables(name or item.get('name', ''), variables)
    method = request.get('method', 'GET')
    
    # Extract URL
    url = ""
    if isinstance(request.get('url'), str):
        url = replace_variables(request.get('url', ''), variables)
    elif isinstance(request.get('url'), dict):
        url_data = request.get('url', {})
        if 'raw' in url_data:
            url = replace_variables(url_data.get('raw', ''), variables)
        else:
            # Construct URL from components
            protocol = url_data.get('protocol', 'https')
            
            # Handle host
            host = url_data.get('host', [])
            if isinstance(host, list):
                host = '.'.join(host)
            host = replace_variables(host, variables)
            
            # Handle path
            path = url_data.get('path', [])
            if isinstance(path, list):
                path = '/'.join(path)
            path = replace_variables(path, variables)
            
            # Construct URL
            url = f"{protocol}://{host}/{path}"
            
            # Add query parameters
            if 'query' in url_data and url_data['query']:
                query_params = []
                for param in url_data['query']:
                    if isinstance(param, dict) and 'key' in param:
                        key = replace_variables(param['key'], variables)
                        value = replace_variables(param.get('value', ''), variables)
                        query_params.append(f"{key}={value}")
                
                if query_params:
                    url += '?' + '&'.join(query_params)
    
    # Extract headers
    headers = {}
    for header in request.get('header', []):
        if isinstance(header, dict) and 'key' in header and 'value' in header:
            key = replace_variables(header.get('key'), variables)
            value = replace_variables(header.get('value'), variables)
            headers[key] = value
    
    # Extract body
    body = None
    if 'body' in request:
        body_data = request.get('body', {})
        if body_data.get('mode') == 'raw':
            raw_body = replace_variables(body_data.get('raw', ''), variables)
            try:
                body = json.loads(raw_body)
            except:
                body = raw_body
        elif body_data.get('mode') == 'formdata':
            form_data = {}
            for param in body_data.get('formdata', []):
                if isinstance(param, dict) and 'key' in param and 'value' in param:
                    key = replace_variables(param['key'], variables)
                    value = replace_variables(param['value'], variables)
                    form_data[key] = value
            body = form_data
        elif body_data.get('mode') == 'urlencoded':
            form_data = {}
            for param in body_data.get('urlencoded', []):
                if isinstance(param, dict) and 'key' in param and 'value' in param:
                    key = replace_variables(param['key'], variables)
                    value = replace_variables(param['value'], variables)
                    form_data[key] = value
            body = form_data
    
    return {
        'name': request_name,
        'method': method,
        'url': url,
        'headers': headers,
        'body': body
    }

def run_interceptor(method, url, headers=None, body=None, wait_time=5, capture_background=True):
    """
    Run the Selenium interceptor script and return the HAR data
    """
    # Create temporary files for headers and body
    headers_file = None
    body_file = None
    
    try:
        # Write headers to temp file if provided
        if headers:
            headers_file = tempfile.NamedTemporaryFile(mode='w+', delete=False)
            json.dump(headers, headers_file)
            headers_file.close()
        
        # Write body to temp file if provided
        if body:
            body_file = tempfile.NamedTemporaryFile(mode='w+', delete=False)
            json.dump(body, body_file)
            body_file.close()
        
        # Build command
        command = [
            'python', 'interceptor.py',
            method,
            url,
            headers_file.name if headers_file else '',
            body_file.name if body_file else '',
            str(wait_time)
        ]
        
        # Add capture-all flag if needed
        if capture_background:
            command.append('--capture-all')
        
        # Run the command
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Error running interceptor: {stderr.decode('utf-8')}")
        
        # Parse the HAR data
        har_data = json.loads(stdout.decode('utf-8'))
        return har_data
    
    finally:
        # Clean up temp files
        if headers_file and os.path.exists(headers_file.name):
            os.unlink(headers_file.name)
        
        if body_file and os.path.exists(body_file.name):
            os.unlink(body_file.name)

def run_collection(collection_id, variables=None):
    """Run a Postman collection and save the results"""
    variables = variables or {}
    
    try:
        collection = PostmanCollection.objects.get(id=collection_id)
        collection.is_running = True
        collection.save()
        
        # Parse collection file to extract variables
        with open(collection.file.path, 'r') as f:
            collection_data = json.load(f)
        
        # Extract collection variables
        collection_variables = extract_variables_from_collection(collection_data)
        
        # Merge with provided variables, with provided variables taking precedence
        if variables:
            collection_variables.update(variables)
        else:
            variables = collection_variables
        
        # Parse collection to get requests
        requests = parse_postman_collection(collection, variables=variables)
        
        for request_data in requests:
            if not request_data.get('url'):
                continue
            
            collection_request = CollectionRequest(
                collection=collection,
                name=request_data.get('name', ''),
                url=request_data.get('url', ''),
                method=request_data.get('method', 'GET'),
                headers=json.dumps(request_data.get('headers', {})),
                body=json.dumps(request_data.get('body', {})) if request_data.get('body') else None
            )
            
            try:
                har_data = run_interceptor(
                    method=collection_request.method,
                    url=collection_request.url,
                    headers=request_data.get('headers', {}),
                    body=request_data.get('body', {}),
                    wait_time=5,
                    capture_background=True
                )
                
                # Set status code and HAR data
                if har_data and 'log' in har_data and har_data['log'].get('entries'):
                    main_entry = None
                    background_entries = []
                    
                    # Separate main request from background requests
                    for entry in har_data['log']['entries']:
                        if entry.get('_is_main_request', False):
                            main_entry = entry
                            collection_request.status_code = entry['response']['status']
                        elif entry.get('_is_background_request', False):
                            background_entries.append(entry)
                
                collection_request.har_data = har_data
                collection_request.save()
                
                # Process background requests
                for entry in background_entries:
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
                collection_request.status_code = 0
                collection_request.har_data = {
                    'error': str(e)
                }
                collection_request.save()
        
        collection.is_running = False
        collection.last_run = timezone.now()
        collection.save()
        return True
    
    except Exception as e:
        try:
            collection.is_running = False
            collection.save()
        except:
            pass
        
        raise Exception(f"Error running collection: {str(e)}")