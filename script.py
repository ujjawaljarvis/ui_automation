import os
import django
import time
import datetime
import sys
import traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager
from django.core.files.base import ContentFile

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "automation_testing.settings") 
django.setup()

from testmanager.models import TestPlan, TestStep, TestRun, TestStepResult

def setup_driver():
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def get_locator(selector_type):
    locator_map = {
        'byid': By.ID,
        'byxpath': By.XPATH,
        'byclass': By.CLASS_NAME,
        'byname': By.NAME,
        'bytag': By.TAG_NAME,
        'bycss': By.CSS_SELECTOR,
        'bylinktext': By.LINK_TEXT,
    }
    return locator_map.get(selector_type.lower())

def take_screenshot(driver):
    """Take a screenshot and return the binary data"""
    return driver.get_screenshot_as_png()

def run_test_plan(plan_id, run_id):
    test_plan = TestPlan.objects.get(id=plan_id)
    test_run = TestRun.objects.get(id=run_id)
    steps = test_plan.steps.order_by('step_order')

    log_lines = []
    driver = setup_driver()
    wait = WebDriverWait(driver, 10)
    actions = ActionChains(driver)

    try:
        for step in steps:
            log_lines.append(f"[STEP {step.step_order}] ACTION: {step.action}")
            
            # Create a step result
            step_result = TestStepResult(
                test_run=test_run,
                test_step=step,
                step_order=step.step_order,
                action=step.action,
                status='success'  
            )
            
            try:
                if step.action == 'goto':
                    # For goto, URL is in input_value
                    url = step.input_value.strip()
                    driver.get(url)
                    log_lines.append(f"→ Navigated to: {url}")
                    time.sleep(2)

                elif step.action == 'click':
                    locator = get_locator(step.selector_type)
                    elem = wait.until(EC.element_to_be_clickable((locator, step.selector_value)))
                    elem.click()
                    log_lines.append(f"→ Clicked: {step.selector_type}={step.selector_value}")
                    time.sleep(1)

                elif step.action == 'input':
                    locator = get_locator(step.selector_type)
                    elem = wait.until(EC.presence_of_element_located((locator, step.selector_value)))
                    elem.clear()
                    elem.send_keys(step.input_value)
                    log_lines.append(f"→ Input: '{step.input_value}' into {step.selector_type}={step.selector_value}")
                    time.sleep(1)

                elif step.action == 'assert':
                    locator = get_locator(step.selector_type)
                    element = wait.until(EC.presence_of_element_located((locator, step.selector_value)))
                    if step.input_value:
                        # If expected value is provided, check text content
                        assert step.input_value in element.text, f"Expected '{step.input_value}' not found in element text: '{element.text}'"
                        log_lines.append(f"→ Asserted text '{step.input_value}' in {step.selector_type}={step.selector_value}")
                    else:
                        log_lines.append(f"→ Asserted presence of {step.selector_type}={step.selector_value}")

                elif step.action == 'select':
                    locator = get_locator(step.selector_type)
                    element = wait.until(EC.presence_of_element_located((locator, step.selector_value)))
                    select = Select(element)
                    
                    # Check if we're selecting by value, text, or index
                    if step.input_value.startswith('value:'):
                        value = step.input_value[6:].strip()
                        select.select_by_value(value)
                        log_lines.append(f"→ Selected option with value '{value}' from dropdown")
                    elif step.input_value.startswith('index:'):
                        index = int(step.input_value[6:].strip())
                        select.select_by_index(index)
                        log_lines.append(f"→ Selected option at index {index} from dropdown")
                    else:
                        # Default to select by visible text
                        select.select_by_visible_text(step.input_value)
                        log_lines.append(f"→ Selected option '{step.input_value}' from dropdown")
                    
                    time.sleep(1)

                elif step.action == 'wait':
                    if step.wait_type == 'time':
                        # Wait for specified seconds
                        wait_time = float(step.input_value)
                        log_lines.append(f"→ Waiting for {wait_time} seconds")
                        time.sleep(wait_time)
                    else:
                        # Wait for element
                        locator = get_locator(step.selector_type)
                        log_lines.append(f"→ Waiting for element {step.selector_type}={step.selector_value}")
                        
                        if step.wait_type == 'element':
                            wait.until(EC.presence_of_element_located((locator, step.selector_value)))
                        elif step.wait_type == 'visible':
                            wait.until(EC.visibility_of_element_located((locator, step.selector_value)))
                        elif step.wait_type == 'clickable':
                            wait.until(EC.element_to_be_clickable((locator, step.selector_value)))
                        
                        log_lines.append(f"→ Element found")

                elif step.action == 'scrollto':
                    locator = get_locator(step.selector_type)
                    element = wait.until(EC.presence_of_element_located((locator, step.selector_value)))
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                    log_lines.append(f"→ Scrolled to element: {step.selector_type}={step.selector_value}")
                    time.sleep(1)

                elif step.action == 'hover':
                    locator = get_locator(step.selector_type)
                    element = wait.until(EC.presence_of_element_located((locator, step.selector_value)))
                    actions.move_to_element(element).perform()
                    log_lines.append(f"→ Hovered over element: {step.selector_type}={step.selector_value}")
                    time.sleep(1)

                elif step.action == 'screenshot':
                    # Take a screenshot and save it to the step result
                    screenshot_data = take_screenshot(driver)
                    step_result.screenshot.save(
                        f"step_{step.step_order}_{int(time.time())}.png",
                        ContentFile(screenshot_data),
                        save=False
                    )
                    log_lines.append(f"→ Took screenshot")

                elif step.action == 'manual':
                    log_lines.append(f"→ Manual step: {step.input_value}")
                    # In an automated run, we'll just log the manual step
                    log_lines.append(f"[MANUAL] {step.input_value or 'Manual step'} - Skipped in automated run")

                else:
                    raise Exception(f"Unknown action type: {step.action}")
                
                # Save successful step result
                step_result.message = "Step completed successfully"
                step_result.save()
                
            except Exception as e:
                # Handle step failure
                step_result.status = 'failed'
                step_result.message = str(e)
                
                # Take a screenshot of the failure
                try:
                    screenshot_data = take_screenshot(driver)
                    step_result.screenshot.save(
                        f"error_step_{step.step_order}_{int(time.time())}.png",
                        ContentFile(screenshot_data),
                        save=False
                    )
                except:
                    pass
                
                step_result.save()
                
                # Log the error
                log_lines.append(f"[ERROR] {str(e)}")
                log_lines.append(f"[TRACEBACK] {traceback.format_exc()}")
                
                # Save error screenshot to test run
                try:
                    if not test_run.error_screenshot:
                        test_run.error_screenshot.save(
                            f"error_{test_run.id}_{int(time.time())}.png",
                            ContentFile(screenshot_data),
                            save=False
                        )
                except:
                    pass
                
                # Mark test run as failed
                test_run.status = 'failed'
                break

        # If we got here without setting status to failed, it's a success
        if test_run.status != 'failed':
            test_run.status = 'success'

    except Exception as e:
        test_run.status = 'failed'
        log_lines.append(f"[ERROR] {str(e)}")
        log_lines.append(f"[TRACEBACK] {traceback.format_exc()}")
        
        # Take a screenshot of the failure
        try:
            screenshot_data = take_screenshot(driver)
            test_run.error_screenshot.save(
                f"error_{test_run.id}_{int(time.time())}.png",
                ContentFile(screenshot_data),
                save=False
            )
        except:
            pass

    finally:
        test_run.ended_at = datetime.datetime.now()
        test_run.log = "\n".join(log_lines)
        test_run.save()
        
        try:
            driver.quit()
        except:
            pass
        
        print(f"Test run complete for Plan: {test_plan.name} → Status: {test_run.status}")
        print("\n".join(log_lines))

# Run test plan with ID from cli
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python script.py <test_plan_id> <test_run_id>")
        sys.exit(1)
    
    plan_id = int(sys.argv[1])
    run_id = int(sys.argv[2])
    run_test_plan(plan_id=plan_id, run_id=run_id)