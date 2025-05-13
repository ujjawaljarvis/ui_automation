
from seleniumwire import webdriver
from seleniumwire.utils import decode
import json
import datetime
import time
import sys
import os
import argparse
import traceback

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

def intercept_and_log(
    method: str,
    url: str,
    headers_file: str = None,
    body_file: str = None,
    wait_time: int = 5,
    debug: bool = False
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
    
    try:
        driver = webdriver.Chrome(options=chrome_opts)
    except Exception as e:
        sys.stderr.write(f"Error initializing Chrome driver: {str(e)}\n")
        raise

    try:
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

        # Process all matching requests
        url_base = url.split('?')[0]
        for req in driver.requests:
            if not req.response:
                continue
            
            # Only include requests to the target URL
            if not req.url.startswith(url_base):
                continue
                
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
                    "queryString": [],  # Could parse URL query params here
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
                "_resourceType": "xhr"
            }

            har["log"]["entries"].append(entry)

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

def main():
    """Command line interface for the interceptor"""
    parser = argparse.ArgumentParser(description='Intercept HTTP requests and log them in HAR format')
    parser.add_argument('method', help='HTTP method (GET, POST, etc.)')
    parser.add_argument('url', help='Target URL')
    parser.add_argument('headers_file', nargs='?', default='', help='Path to JSON file containing headers')
    parser.add_argument('body_file', nargs='?', default='', help='Path to JSON file containing request body')
    parser.add_argument('wait_time', nargs='?', type=int, default=5, help='Time to wait for requests to complete (seconds)')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    
    args = parser.parse_args()
    
    try:
        intercept_and_log(
            method=args.method,
            url=args.url,
            headers_file=args.headers_file if args.headers_file else None,
            body_file=args.body_file if args.body_file else None,
            wait_time=args.wait_time,
            debug=args.debug
        )
    except Exception as e:
        sys.stderr.write(f"Error: {str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()