#!/usr/bin/env python
import os
import django
import time
import datetime
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "automation_testing.settings") 
django.setup()

from testmanager.models import TestPlan, TestStep, TestRun  


def setup_driver():
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless=new")  # Run in headless mode for CI
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver


def get_locator(selector_type):
    locator_map = {
        'byid': By.ID,
        'byxpath': By.XPATH,
        'byclass': By.CLASS_NAME,
        'byname': By.NAME,
        'bytag': By.TAG_NAME,
    }
    return locator_map.get(selector_type.lower())


def run_test_plan(plan_id):
    test_plan = TestPlan.objects.get(id=plan_id)
    steps = test_plan.steps.order_by('step_order')

    test_run = TestRun.objects.create(
        test_plan=test_plan,
        status='running',
        started_at=datetime.datetime.now()
    )

    log_lines = []
    driver = setup_driver()
    wait = WebDriverWait(driver, 10)

    try:
        for step in steps:
            log_lines.append(f"[STEP {step.step_order}] ACTION: {step.action}")

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

            elif step.action == 'manual':
                log_lines.append(f"→ Manual step: {step.input_value}")
                # In an automated run, we'll just log the manual step
                log_lines.append(f"[MANUAL] {step.input_value or 'Manual step'} - Skipped in automated run")

            else:
                raise Exception(f"Unknown action type: {step.action}")

        test_run.status = 'success'

    except Exception as e:
        test_run.status = 'failed'
        log_lines.append(f"[ERROR] {str(e)}")

    finally:
        test_run.ended_at = datetime.datetime.now()
        test_run.log = "\n".join(log_lines)
        test_run.save()
        driver.quit()
        print(f"Test run complete for Plan: {test_plan.name} → Status: {test_run.status}")
        print("\n".join(log_lines))


# Run test plan with ID from cli
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_test.py <test_plan_id>")
        sys.exit(1)
    
    plan_id = int(sys.argv[1])
    run_test_plan(plan_id=plan_id)