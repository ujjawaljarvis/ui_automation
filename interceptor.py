#!/usr/bin/env python
from seleniumwire import webdriver
from seleniumwire.utils import decode
import json
import datetime
import time
import sys
import os
import argparse
import traceback
import urllib.parse

def try_decode_body(body):
    """Safely decode response/request body"""
    if not body:
        return ""
    try:
        return body.decode('utf-8', errors='replace')
    except Exception as e:
        return f"<Failed to decode: {e}>"

def load_json_from_file(file_path):
    """Load JSON data from a file"""
    if not file_path or not os.path.exists(file_path):
        return {}
    
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        sys.stderr.write(f"Error loading JSON from {file_path}: {str(e)}\n")
        return {}

def determine_resource_type(req):
    """Determine the type of resource being requested"""
    content_type = req.response.headers.get('Content-Type', '') if req.response else ''
    
    # Check if it's an XHR request
    if req.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return 'xhr'
    
    # Check Accept header for API calls
    accept = req.headers.get('Accept', '')
    if 'application/json' in accept or 'application/xml' in accept:
        return 'xhr'
    
    # Check Content-Type for JSON responses
    if 'application/json' in content_type:
        return 'xhr'
    
    # Check for common resource types
    if 'text/css' in content_type:
        return 'stylesheet'
    elif 'image/' in content_type:
        return 'image'
    elif 'font/' in content_type or 'application/font' in content_type:
        return 'font'
    elif 'text/javascript' in content_type or 'application/javascript' in content_type:
        return 'script'
    elif 'text/html' in content_type:
        return 'document'
    
    # Default to XHR for API-like endpoints
    url_path = urllib.parse.urlparse(req.url).path.lower()
    if '/api/' in url_path or '/graphql' in url_path:
        return 'xhr'
    
    return 'other'

def intercept_and_log(
    method: str,
    url: str,
    headers_file: str = None,
    body_file: str = None,
    wait_time: int = 5,
    debug: bool = False,
    capture_all: bool = True
):
    """
    Intercept HTTP requests using Selenium Wire and log them in HAR format
    
    Args:
        method: HTTP method (GET, POST, etc.)
        url: Target URL
        headers_file: Path to JSON file containing headers
        body_file: Path to JSON file containing request body
        wait_time: Time to wait for requests to complete (seconds)
        debug: Enable debug output
        capture_all: Capture all requests, not just the main one
    """
    # Load headers and body from files if provided
    headers = load_json_from_file(headers_file)
    body_dict = load_json_from_file(body_file)
    
    if debug:
        sys.stderr.write(f"Method: {method}\n")
        sys.stderr.write(f"URL: {url}\n")
        sys.stderr.write(f"Headers: {json.dumps(headers)}\n")
        sys.stderr.write(f"Body: {json.dumps(body_dict)}\n")
        sys.stderr.write(f"Wait time: {wait_time}\n")
    
    # Configure Chrome options
    chrome_opts = webdriver.ChromeOptions()
    chrome_opts.add_argument('--headless')
    chrome_opts.add_argument('--disable-gpu')
    chrome_opts.add_argument('--no-sandbox')
    chrome_opts.add_argument('--disable-dev-shm-usage')
    
    # Configure Selenium Wire options
    seleniumwire_options = {
        'disable_encoding': True,  # Don't decode responses
        'enable_har': True,        # Enable HAR format
    }
    
    try:
        driver = webdriver.Chrome(
            options=chrome_opts,
            seleniumwire_options=seleniumwire_options
        )
    except Exception as e:
        sys.stderr.write(f"Error initializing Chrome driver: {str(e)}\n")
        raise

    try:
        # Clear existing requests
        del driver.requests
        
        # Navigate to a blank page first
        driver.get("about:blank")

        # Execute the request based on the method
        if method.upper() == "GET":
            driver.get(url)
        else:
            # Build JavaScript fetch command
            js = [
                "return fetch(", 
                json.dumps(url), ", {",
                f"method: {json.dumps(method.upper())},"
            ]
            
            if headers:
                js.append(f"headers: {json.dumps(headers)},")
            
            if body_dict:
                js.append(f"body: JSON.stringify({json.dumps(body_dict)}),")
            
            js.append("});")
            fetch_script = " ".join(js)
            
            if debug:
                sys.stderr.write(f"Executing script: {fetch_script}\n")
            
            driver.execute_script(fetch_script)

        # Wait for requests to complete
        time.sleep(wait_time)

        # Initialize HAR structure
        har = {
            "log": {
                "version": "1.2",
                "creator": {
                    "name": "URL Interceptor",
                    "version": "1.0"
                },
                "entries": []
            }
        }

        # Track if we've found the main request
        main_request_found = False
        url_base = url.split('?')[0]
        
        # First, find and process the main request
        for req in driver.requests:
            if not req.response:
                continue
            
            # Check if this is the main request
            if req.url.startswith(url_base) and not main_request_found:
                main_request_found = True
                
                # Process the main request
                entry = process_request(req)
                entry["_is_main_request"] = True
                har["log"]["entries"].append(entry)
        
        # Then process background requests if capture_all is True
        if capture_all:
            background_entries = []
            
            for req in driver.requests:
                if not req.response:
                    continue
                
                # Skip the main request
                if req.url.startswith(url_base) and main_request_found:
                    continue
                
                # Process background request
                entry = process_request(req)
                entry["_is_background_request"] = True
                entry["_resource_type"] = determine_resource_type(req)
                background_entries.append(entry)
            
            # Add background entries to HAR
            har["log"]["entries"].extend(background_entries)

        # Output HAR data as JSON
        print(json.dumps(har, indent=2))
        return har

    except Exception as e:
        sys.stderr.write(f"Error during interception: {str(e)}\n")
        if debug:
            traceback.print_exc(file=sys.stderr)
        raise
    finally:
        # Always close the driver
        driver.quit()

def process_request(req):
    """Process a request and create a HAR entry"""
    # Extract request headers
    request_headers = [{"name": k, "value": v} for k, v in req.headers.items()]
    
    # Extract response headers
    response_headers = [{"name": k, "value": v} for k, v in req.response.headers.items()]

    # Extract cookies from request (Cookie header)
    cookies = []
    try:
        if req.headers.get("Cookie"):
            cookie_header = req.headers.get("Cookie")
            for c in cookie_header.split(";"):
                if "=" in c:
                    name, value = c.strip().split("=", 1)
                    cookies.append({"name": name, "value": value})
    except Exception as e:
        cookies.append({"error": f"Failed to parse cookies: {str(e)}"})

    # Extract Set-Cookie headers from response
    set_cookies = []
    for k, v in req.response.headers.items():
        if k.lower() == "set-cookie":
            set_cookies.append({"name": "Set-Cookie", "value": v})

    # Create HAR entry
    entry = {
        "startedDateTime": datetime.datetime.utcnow().isoformat() + "Z",
        "request": {
            "method": req.method,
            "url": req.url,
            "httpVersion": "HTTP/1.1",
            "headers": request_headers,
            "cookies": cookies,
            "queryString": parse_query_string(req.url),
            "headersSize": -1,
            "bodySize": -1,
            "body": try_decode_body(req.body)
        },
        "response": {
            "status": req.response.status_code,
            "statusText": "",
            "httpVersion": "HTTP/1.1",
            "headers": response_headers,
            "cookies": set_cookies,
            "content": {
                "size": len(req.response.body) if req.response.body else 0,
                "mimeType": req.response.headers.get('Content-Type', 'text/plain'),
                "text": try_decode_body(
                    decode(req.response.body, req.response.headers.get('Content-Encoding', 'identity'))
                )
            },
            "redirectURL": "",
            "headersSize": -1,
            "bodySize": -1,
        },
        "cache": {},
        "timings": {
            "wait": -1
        },
        "connection": req.id,
        "_resourceType": determine_resource_type(req)
    }
    
    return entry

def parse_query_string(url):
    """Parse query string parameters from URL"""
    try:
        parsed_url = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qsl(parsed_url.query)
        return [{"name": k, "value": v} for k, v in query_params]
    except:
        return []

def main():
    """Command line interface for the interceptor"""
    parser = argparse.ArgumentParser(description='Intercept HTTP requests and log them in HAR format')
    parser.add_argument('method', help='HTTP method (GET, POST, etc.)')
    parser.add_argument('url', help='Target URL')
    parser.add_argument('headers_file', nargs='?', default='', help='Path to JSON file containing headers')
    parser.add_argument('body_file', nargs='?', default='', help='Path to JSON file containing request body')
    parser.add_argument('wait_time', nargs='?', type=int, default=5, help='Time to wait for requests to complete (seconds)')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--capture-all', action='store_true', help='Capture all requests, not just the main one')
    
    args = parser.parse_args()
    
    try:
        intercept_and_log(
            method=args.method,
            url=args.url,
            headers_file=args.headers_file if args.headers_file else None,
            body_file=args.body_file if args.body_file else None,
            wait_time=args.wait_time,
            debug=args.debug,
            capture_all=args.capture_all
        )
    except Exception as e:
        sys.stderr.write(f"Error: {str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()