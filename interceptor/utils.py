# interceptor/utils.py
import subprocess
import json
import tempfile
import os

def run_interceptor(method, url, headers=None, body=None, wait_time=5):
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