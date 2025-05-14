import json
from django.utils import timezone
from .models import PostmanCollection, CollectionRequest
from .utils import run_interceptor

def replace_variables(text, variables):
    """Replace {{var}} placeholders with actual values"""
    if not isinstance(text, str):
        return text
    for key, value in variables.items():
        text = text.replace(f"{{{{{key}}}}}", value)
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
    variables = variables or {}

    try:
        with open(collection.file.path, 'r') as f:
            collection_data = json.load(f)

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
    variables = variables or {}
    requests = []

    for item in collection_data.get('item', []):
        if 'item' in item:
            folder_name = item.get('name', '')
            folder_path = f"{parent_name}/{folder_name}" if parent_name else folder_name
            requests.extend(extract_requests_v2(item, folder_path, variables=variables))
        elif 'request' in item:
            request_name = item.get('name', '')
            request_path = f"{parent_name}/{request_name}" if parent_name else request_name
            request_data = extract_single_request(item, name=request_path, variables=variables)
            if request_data:
                requests.append(request_data)

    return requests

def extract_requests_v1(collection_data, variables=None):
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
                body = json.loads(replace_variables(request.get('rawModeData', '{}'), variables))
            except:
                body = replace_variables(request.get('rawModeData', ''), variables)

        requests.append({
            'name': replace_variables(request.get('name', ''), variables),
            'method': request.get('method', 'GET'),
            'url': url,
            'headers': headers,
            'body': body
        })

    return requests

def extract_single_request(item, name=None, variables=None):
    variables = variables or {}
    request = item.get('request', {})

    if not request:
        return None

    request_name = replace_variables(name or item.get('name', ''), variables)
    method = request.get('method', 'GET')

    url = ""
    if isinstance(request.get('url'), str):
        url = replace_variables(request.get('url', ''), variables)
    elif isinstance(request.get('url'), dict):
        url_data = request.get('url', {})
        if 'raw' in url_data:
            url = replace_variables(url_data.get('raw', ''), variables)
        else:
            host = '.'.join(url_data.get('host', []))
            path = '/'.join(url_data.get('path', []))
            protocol = url_data.get('protocol', 'https')
            url = f"{protocol}://{host}/{path}"
            url = replace_variables(url, variables)

    headers = {}
    for header in request.get('header', []):
        if isinstance(header, dict) and 'key' in header and 'value' in header:
            key = replace_variables(header.get('key'), variables)
            value = replace_variables(header.get('value'), variables)
            headers[key] = value

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

    return {
        'name': request_name,
        'method': method,
        'url': url,
        'headers': headers,
        'body': body
    }

def run_collection(collection_id, variables=None):
    variables = variables or {}

    try:
        collection = PostmanCollection.objects.get(id=collection_id)
        collection.is_running = True
        collection.save()

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
                    wait_time=5
                )

                if har_data and 'log' in har_data and har_data['log'].get('entries'):
                    collection_request.status_code = har_data['log']['entries'][0]['response']['status']

                collection_request.har_data = har_data

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

