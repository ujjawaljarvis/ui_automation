from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import time
from io import BytesIO
from PIL import Image
import threading
import uuid
import csv
from django.conf import settings
from django.core.files.base import ContentFile
from xpath.models import CapturedElement

class ElementInspector(threading.Thread):
    def __init__(self, url, project_id=None, capture_id=None):
        threading.Thread.__init__(self)
        self.url = url
        self.project_id = project_id
        self.capture_id = capture_id
        self.captured_elements = []
        self.running = True
        self.status = "initializing"
        self.message = "Initializing capture session..."
        self.element_count = 0
        self.daemon = True  # Thread will exit when main program exits
        self.browser_closed = False
    
    def setup_driver(self):
        """Initialize the Chrome WebDriver with appropriate options"""
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-web-security")  # Disable CORS
        chrome_options.add_argument("--disable-features=IsolateOrigins,site-per-process")  # Disable site isolation
        
        # For production, we'll use headless mode
        if not settings.DEBUG:
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.actions = ActionChains(self.driver)
    
    def get_xpath_script(self):
        """JavaScript function to get XPath of an element"""
        return """
            function getXPath(el) {
                if (el.id) return '//*[@id=\"' + el.id + '\"]';
                const path = [];
                while (el.nodeType === Node.ELEMENT_NODE) {
                    let index = 1;
                    let sibling = el.previousSibling;
                    while (sibling) {
                        if (sibling.nodeType === Node.ELEMENT_NODE && sibling.tagName === el.tagName) index++;
                        sibling = sibling.previousSibling;
                    }
                    path.unshift(el.tagName.toLowerCase() + '[' + index + ']');
                    el = el.parentNode;
                }
                return '/' + path.join('/');
            }
            return getXPath(arguments[0]);
        """
    
    def get_css_selector_script(self):
        """JavaScript function to get CSS selector of an element"""
        return """
            function getCssSelector(el) {
                if (el.id) return '#' + el.id;
                if (el.classList && el.classList.length > 0) 
                    return el.tagName.toLowerCase() + '.' + Array.from(el.classList).join('.');
                
                let path = [];
                while (el.nodeType === Node.ELEMENT_NODE) {
                    let selector = el.tagName.toLowerCase();
                    if (el.id) {
                        selector += '#' + el.id;
                        path.unshift(selector);
                        break;
                    } else {
                        let sibling = el.previousElementSibling;
                        let index = 1;
                        while (sibling) {
                            if (sibling.tagName === el.tagName) index++;
                            sibling = sibling.previousElementSibling;
                        }
                        if (index > 1) selector += ':nth-of-type(' + index + ')';
                    }
                    path.unshift(selector);
                    el = el.parentNode;
                }
                return path.join(' > ');
            }
            return getCssSelector(arguments[0]);
        """
    
    def capture_element_screenshot(self, element):
        """Capture a screenshot of the specific element"""
        try:
            # Scroll element into view
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.5)
            
            # Get element location and size
            location = element.location_once_scrolled_into_view
            size = element.size
            
            # Take screenshot of the entire page
            screenshot = self.driver.get_screenshot_as_png()
            img = Image.open(BytesIO(screenshot))
            
            # Calculate element boundaries
            left = location['x']
            top = location['y']
            right = location['x'] + size['width']
            bottom = location['y'] + size['height']
            
            # Crop the image to the element
            img = img.crop((left, top, right, bottom))
            
            # Save to BytesIO
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            return buffered.getvalue()
        except Exception as e:
            print(f"Error capturing screenshot: {e}")
            return None
    
    def run(self):
        """Main thread method that runs the element inspection"""
        try:
            self.setup_driver()
            self.status = "running"
            self.message = "Capture session running. Hover over elements to capture them."
            
            # Navigate to URL
            self.driver.get(self.url)
            time.sleep(3)  # Wait for page to load
            
            # Inject highlight script
            self.driver.execute_script("""
                // Add highlight styles
                var style = document.createElement('style');
                style.id = 'xpath-capture-styles';
                style.textContent = `
                    .xpath-highlight {
                        outline: 2px solid #4f46e5 !important;
                        background-color: rgba(79, 70, 229, 0.1) !important;
                    }
                `;
                document.head.appendChild(style);
                
                // Store the currently highlighted element
                window.currentHighlightedElement = null;
                
                // Add mouseover event listener
                document.addEventListener('mouseover', function(e) {
                    // Remove highlight from previous element
                    if (window.currentHighlightedElement) {
                        window.currentHighlightedElement.classList.remove('xpath-highlight');
                    }
                    
                    // Highlight current element
                    e.target.classList.add('xpath-highlight');
                    window.currentHighlightedElement = e.target;
                });
            """)
            
            last_element = None
            hover_start_time = None
            captured_elements_set = set()
            
            while self.running:
                try:
                    # Try to get hovered element
                    hovered = self.driver.execute_script("""
                        const hoveredElements = document.querySelectorAll(':hover');
                        return hoveredElements[hoveredElements.length - 1] || null;
                    """)
                    
                    if hovered:
                        tag_name = hovered.tag_name
                        
                        if hovered != last_element:
                            last_element = hovered
                            hover_start_time = time.time()
                        else:
                            if hover_start_time and (time.time() - hover_start_time >= 0.5):
                                # Use element's unique reference to check if already captured
                                element_ref = self.driver.execute_script("return arguments[0];", hovered)
                                element_id = id(element_ref)
                                
                                if element_id not in captured_elements_set:
                                    captured_elements_set.add(element_id)
                                    
                                    # Get attributes
                                    el_id = hovered.get_attribute("id") or ""
                                    el_class = hovered.get_attribute("class") or ""
                                    outer_html = hovered.get_attribute("outerHTML") or ""
                                    xpath = self.driver.execute_script(self.get_xpath_script(), hovered)
                                    css_selector = self.driver.execute_script(self.get_css_selector_script(), hovered)
                                    
                                    # Generate a descriptive name
                                    name = el_id or f"{tag_name}_{self.element_count + 1}"
                                    
                                    # Capture screenshot
                                    screenshot_data = self.capture_element_screenshot(hovered)
                                    
                                    # Create element in database
                                    element = CapturedElement(
                                        project_id=self.project_id,
                                        name=name,
                                        url=self.url,
                                        xpath=xpath,
                                        css_selector=css_selector,
                                        id_selector=el_id,
                                        class_selector=el_class,
                                        tag_name=tag_name,
                                        html_snippet=outer_html[:500] + ("..." if len(outer_html) > 500 else "")
                                    )
                                    
                                    # Save the element to get an ID
                                    element.save()
                                    
                                    # Save screenshot if available
                                    if screenshot_data:
                                        filename = f"element_{element.id}.png"
                                        element.screenshot.save(filename, ContentFile(screenshot_data), save=False)
                                    
                                    # Save element again to update screenshot field
                                    element.save()
                                    
                                    self.captured_elements.append(element)
                                    self.element_count += 1
                    else:
                        last_element = None
                        hover_start_time = None
                
                except WebDriverException as e:
                    # Browser was likely closed
                    print(f"Browser connection lost: {e}")
                    self.browser_closed = True
                    self.status = "browser_closed"
                    self.message = "Browser window was closed. Click 'View Results' to see captured elements."
                    break
                
                time.sleep(0.1)
                
        except Exception as e:
            self.status = "error"
            self.message = f"Error: {str(e)}"
            print(f"Error in capture thread: {e}")
        finally:
            try:
                if hasattr(self, 'driver'):
                    self.driver.quit()
            except:
                pass
            
            if self.status != "browser_closed" and self.status != "error":
                self.status = "completed"
                self.message = f"Capture completed successfully. {self.element_count} elements captured."

    def stop(self):
        """Stop the capture process"""
        self.running = False
        try:
            if hasattr(self, 'driver'):
                self.driver.quit()
        except:
            pass

# Dictionary to store active capture sessions
active_captures = {}

def start_capture(url, project_id=None):
    """Start a new capture session"""
    capture_id = str(uuid.uuid4())
    
    inspector = ElementInspector(url, project_id, capture_id)
    active_captures[capture_id] = inspector
    inspector.start()
    
    return capture_id

def get_capture_status(capture_id):
    """Get the status of a capture session"""
    if capture_id not in active_captures:
        return None
    
    inspector = active_captures[capture_id]
    return {
        'status': inspector.status,
        'message': inspector.message,
        'elementCount': inspector.element_count,
        'browserClosed': inspector.browser_closed
    }

def stop_capture(capture_id):
    """Stop a capture session"""
    if capture_id not in active_captures:
        return False
    
    inspector = active_captures[capture_id]
    inspector.stop()
    
    # Wait for thread to finish
    inspector.join(timeout=5)
    
    return True

def get_capture_results(capture_id):
    """Get the results of a capture session"""
    if capture_id not in active_captures:
        return None
    
    inspector = active_captures[capture_id]
    return inspector.captured_elements

def export_elements_to_csv(elements, file_path):
    """Export captured elements to CSV file"""
    with open(file_path, 'w', newline='') as csvfile:
        fieldnames = ['name', 'url', 'xpath', 'css_selector', 'id_selector', 'class_selector', 'tag_name']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for element in elements:
            writer.writerow({
                'name': element.name,
                'url': element.url,
                'xpath': element.xpath,
                'css_selector': element.css_selector,
                'id_selector': element.id_selector,
                'class_selector': element.class_selector,
                'tag_name': element.tag_name
            })