import requests
from bs4 import BeautifulSoup
import json
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
import logging
from urllib.parse import urljoin, urlparse
from datetime import datetime
import base64
import os
from PIL import Image
import io
import socket

# Add timeout to prevent WebDriverManager from hanging
socket.setdefaulttimeout(30)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DelhiHighCourtScraper:
    def __init__(self):
        # Updated URLs based on the current Delhi High Court website
        self.base_url = "https://www.delhihighcourt.nic.in"
        self.search_url = "https://delhihighcourt.nic.in/app/get-case-type-status"
        
        # Alternative URLs to try if primary fails
        self.alternative_urls = [
            "https://dhccaseinfo.nic.in/pcase/guiCaseWise.php",
            "http://164.100.69.66/pcase/guiCaseWise.php",
            "https://www.delhihighcourt.nic.in/web/"
        ]
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        self.max_retries = 3
        self.retry_delay = 2
        
    def setup_driver(self):
        """Setup Chrome driver with optimal options and aggressive timeouts"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--ignore-ssl-errors')
        chrome_options.add_argument('--ignore-certificate-errors-spki-list')
        chrome_options.add_argument('--ignore-certificate-errors-invalid-spki')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--disable-images')
        chrome_options.add_argument('--timeout=30')
        
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Set aggressive timeouts to prevent hanging
            driver.set_page_load_timeout(20)  # 20 seconds max for page load
            driver.implicitly_wait(10)        # 10 seconds max for element finding
            
            return driver
        except Exception as e:
            logger.error(f"Failed to setup Chrome driver: {str(e)}")
            raise Exception(f"Chrome driver setup failed: {str(e)}")
        
    def fetch_case_data(self, case_type, case_number, filing_year):
        """
        Fetch case data from Delhi High Court with retry logic and multiple URL attempts
        """
        urls_to_try = [self.search_url] + self.alternative_urls
        
        for url in urls_to_try:
            logger.info(f"Trying URL: {url}")
            
            for attempt in range(self.max_retries):
                driver = None
                try:
                    logger.info(f"Attempt {attempt + 1}: Searching for case: {case_type}/{case_number}/{filing_year}")
                    
                    driver = self.setup_driver()
                    
                    # Navigate to case status page
                    logger.info(f"Navigating to {url}...")
                    driver.get(url)
                    
                    # Wait for page to load completely
                    WebDriverWait(driver, 20).until(
                        EC.any_of(
                            EC.presence_of_element_located((By.TAG_NAME, "form")),
                            EC.presence_of_element_located((By.NAME, "case_type")),
                            EC.presence_of_element_located((By.ID, "case_type")),
                            EC.presence_of_element_located((By.CLASS_NAME, "form-control"))
                        )
                    )
                    
                    # Check for maintenance or error messages
                    if self._check_site_status(driver):
                        logger.warning("Site under maintenance, trying next URL...")
                        break  # Try next URL
                    
                    # Fill the search form
                    success = self._fill_search_form(driver, case_type, case_number, filing_year)
                    if not success:
                        logger.warning("Failed to fill search form, trying next URL...")
                        break  # Try next URL
                    
                    # Handle CAPTCHA if present
                    captcha_result = self._handle_captcha(driver)
                    if captcha_result == "manual_required":
                        return "captcha_required", "Please solve the CAPTCHA and resubmit"
                    elif not captcha_result:
                        return None, "CAPTCHA handling failed"
                    
                    # Submit form and wait for results
                    case_data = self._submit_and_parse_results_with_timeout(driver)
                    if case_data == "timeout":
                        return None, "Search timed out - court website is responding slowly"
                    elif case_data:
                        logger.info("Case data retrieved successfully")
                        return case_data, None
                    else:
                        logger.info("No case data found with this URL, trying alternatives...")
                        break  # Try next URL
                        
                except TimeoutException:
                    logger.warning(f"Timeout on attempt {attempt + 1} with URL {url}")
                    if attempt == self.max_retries - 1:
                        logger.warning(f"Max retries reached for {url}, trying next URL...")
                        break  # Try next URL
                except WebDriverException as e:
                    logger.warning(f"WebDriver error on attempt {attempt + 1}: {str(e)}")
                    if attempt == self.max_retries - 1:
                        break  # Try next URL
                except Exception as e:
                    logger.error(f"Unexpected error on attempt {attempt + 1}: {str(e)}")
                    if attempt == self.max_retries - 1:
                        break  # Try next URL
                finally:
                    if driver:
                        try:
                            driver.quit()
                        except:
                            pass
                
                # Wait before retry
                if attempt < self.max_retries - 1:
                    logger.info(f"Waiting {self.retry_delay} seconds before retry...")
                    time.sleep(self.retry_delay)
        
        return None, "All URLs and retries exhausted - unable to fetch case data"

    def fetch_case_data_with_captcha(self, case_type, case_number, filing_year, captcha_solution=None):
        """Modified fetch method that handles CAPTCHA workflow with aggressive timeouts"""
        driver = None
        try:
            driver = self.setup_driver()
            logger.info(f"Fetching case data for {case_type}/{case_number}/{filing_year}")
            
            # Set very aggressive timeouts
            driver.set_page_load_timeout(15)  # 15 seconds max for any page load
            driver.implicitly_wait(5)         # 5 seconds max for element finding
            
            # Navigate to search page with timeout
            try:
                logger.info("Navigating to court website...")
                driver.get(self.search_url)
            except Exception as e:
                logger.error(f"Failed to load court website: {str(e)}")
                return None, "Failed to connect to court website"
            
            # Wait for page load with timeout
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "form"))
                )
            except TimeoutException:
                logger.error("Timeout waiting for search form to load")
                return None, "Court website took too long to load"
            
            # Fill search form with timeout
            logger.info("Filling search form...")
            if not self._fill_search_form(driver, case_type, case_number, filing_year):
                return None, "Failed to fill search form"
            
            # Handle CAPTCHA with timeout
            logger.info("Checking for CAPTCHA...")
            try:
                captcha_result = self._handle_captcha(driver)
                
                if captcha_result == "manual_required":
                    logger.info("CAPTCHA detected - redirecting to manual solver")
                    return "captcha_required", "Please solve the CAPTCHA and resubmit"
                elif captcha_result == False:
                    return None, "CAPTCHA handling failed"
                    
            except Exception as e:
                logger.error(f"CAPTCHA handling error: {str(e)}")
                return None, "Error during CAPTCHA detection"
            
            # Submit form with strict timeout
            logger.info("Submitting search form...")
            case_data = self._submit_and_parse_results_with_timeout(driver, captcha_solution)
            
            if case_data == "captcha_error":
                return None, "Incorrect CAPTCHA solution - please try again"
            elif case_data == "timeout":
                return None, "Search timed out - court website is responding slowly"
            elif case_data == "captcha_required":
                return "captcha_required", "New CAPTCHA appeared - please solve it"
            elif case_data:
                return case_data, None
            else:
                return None, "No case data found"
                
        except Exception as e:
            logger.error(f"Error in fetch_case_data_with_captcha: {str(e)}")
            return None, str(e)
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    def _check_site_status(self, driver):
        """Check if the website is showing maintenance or error messages"""
        try:
            # Check for common maintenance indicators
            maintenance_indicators = [
                "maintenance", "under maintenance", "temporarily unavailable",
                "service unavailable", "server error", "503", "502", "500",
                "access denied", "forbidden", "not found"
            ]
            
            page_text = driver.page_source.lower()
            page_title = driver.title.lower()
            
            for indicator in maintenance_indicators:
                if indicator in page_text or indicator in page_title:
                    logger.warning(f"Site issue detected: {indicator}")
                    return True
            return False
        except:
            return False
    
    def _fill_search_form(self, driver, case_type, case_number, filing_year):
        """Fill the search form with case details - supports multiple form layouts"""
        try:
            # Try multiple selectors for case type dropdown
            case_type_selectors = [
                (By.NAME, "case_type"),
                (By.ID, "case_type"),
                (By.CLASS_NAME, "case-type"),
                (By.XPATH, "//select[contains(@name,'case') and contains(@name,'type')]"),
                (By.XPATH, "//select[contains(@id,'case') and contains(@id,'type')]")
            ]
            
            case_type_element = None
            for selector in case_type_selectors:
                try:
                    case_type_element = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(selector)
                    )
                    break
                except:
                    continue
            
            if not case_type_element:
                logger.error("Could not find case type dropdown")
                return False
            
            # Select case type
            case_type_select = Select(case_type_element)
            
            # Try to select by visible text first, then by partial match
            try:
                case_type_select.select_by_visible_text(case_type)
                logger.info(f"Selected case type: {case_type}")
            except:
                # Try partial matching for case type
                for option in case_type_select.options:
                    if case_type.lower() in option.text.lower() or option.text.lower() in case_type.lower():
                        case_type_select.select_by_visible_text(option.text)
                        logger.info(f"Selected case type by partial match: {option.text}")
                        break
                else:
                    logger.warning(f"Could not find case type: {case_type}")
                    return False
            
            # Try multiple selectors for case number input
            case_number_selectors = [
                (By.NAME, "case_no"),
                (By.NAME, "case_number"),
                (By.ID, "case_no"),
                (By.ID, "case_number"),
                (By.XPATH, "//input[contains(@name,'case') and contains(@name,'no')]"),
                (By.XPATH, "//input[contains(@name,'case') and contains(@name,'number')]")
            ]
            
            case_number_input = None
            for selector in case_number_selectors:
                try:
                    case_number_input = driver.find_element(*selector)
                    break
                except:
                    continue
            
            if case_number_input:
                case_number_input.clear()
                case_number_input.send_keys(str(case_number))
                logger.info(f"Entered case number: {case_number}")
            else:
                logger.error("Could not find case number input field")
                return False
            
            # Try multiple selectors for filing year
            year_selectors = [
                (By.NAME, "case_year"),
                (By.NAME, "filing_year"),
                (By.NAME, "year"),
                (By.ID, "case_year"),
                (By.ID, "filing_year"),
                (By.XPATH, "//input[contains(@name,'year')]"),
                (By.XPATH, "//select[contains(@name,'year')]")
            ]
            
            year_input = None
            for selector in year_selectors:
                try:
                    year_input = driver.find_element(*selector)
                    break
                except:
                    continue
            
            if year_input:
                if year_input.tag_name == 'select':
                    # If it's a dropdown
                    year_select = Select(year_input)
                    try:
                        year_select.select_by_visible_text(str(filing_year))
                    except:
                        year_select.select_by_value(str(filing_year))
                else:
                    # If it's an input field
                    year_input.clear()
                    year_input.send_keys(str(filing_year))
                logger.info(f"Entered filing year: {filing_year}")
            else:
                logger.error("Could not find filing year field")
                return False
            
            logger.info("Search form filled successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error filling search form: {str(e)}")
            return False
    
    def _handle_captcha(self, driver):
        """Enhanced CAPTCHA handling with manual user interface"""
        try:
            # Check for CAPTCHA elements
            captcha_image = None
            captcha_input = None
            captcha_found = False
            
            # Multiple CAPTCHA detection methods
            captcha_image_selectors = [
                "//img[contains(@src,'captcha')]",
                "//img[contains(@alt,'captcha')]", 
                "//img[contains(@id,'captcha')]",
                "//img[contains(@class,'captcha')]",
                "//canvas[contains(@id,'captcha')]"
            ]
            
            # Find CAPTCHA image
            for selector in captcha_image_selectors:
                try:
                    captcha_image = driver.find_element(By.XPATH, selector)
                    captcha_found = True
                    logger.info(f"CAPTCHA image found with selector: {selector}")
                    break
                except NoSuchElementException:
                    continue
            
            # Find CAPTCHA input field
            captcha_input_selectors = [
                "//input[contains(@name,'captcha')]",
                "//input[contains(@id,'captcha')]", 
                "//input[contains(@placeholder,'captcha')]",
                "//input[contains(@class,'captcha')]"
            ]
            
            for selector in captcha_input_selectors:
                try:
                    captcha_input = driver.find_element(By.XPATH, selector)
                    logger.info(f"CAPTCHA input found with selector: {selector}")
                    break
                except NoSuchElementException:
                    continue
            
            # If CAPTCHA detected, handle manually
            if captcha_found and captcha_image and captcha_input:
                logger.info("CAPTCHA detected - initiating manual solving process")
                
                # Save CAPTCHA image for user
                captcha_filename = self._save_captcha_image(captcha_image, driver)
                
                if captcha_filename:
                    # Store CAPTCHA details in session for web interface
                    captcha_data = {
                        'image_path': captcha_filename,
                        'input_element': captcha_input,
                        'timestamp': datetime.now().isoformat(),
                        'status': 'waiting_for_user'
                    }
                    
                    # Save to temporary file for Flask to access
                    captcha_session_file = os.path.join('data', 'captcha_session.json')
                    with open(captcha_session_file, 'w') as f:
                        json.dump(captcha_data, f)
                    
                    logger.info("CAPTCHA session saved - waiting for user input")
                    return "manual_required"
                else:
                    logger.error("Failed to save CAPTCHA image")
                    return False
            
            # No CAPTCHA found
            return True
            
        except Exception as e:
            logger.error(f"Error in CAPTCHA handling: {str(e)}")
            return False

    def _save_captcha_image(self, captcha_element, driver):
        """Save CAPTCHA image for user to solve manually"""
        try:
            # Create captcha directory if it doesn't exist
            captcha_dir = os.path.join('static', 'captcha')
            os.makedirs(captcha_dir, exist_ok=True)
            
            # Generate unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            captcha_filename = f"captcha_{timestamp}.png"
            captcha_path = os.path.join(captcha_dir, captcha_filename)
            
            # Take screenshot of CAPTCHA element
            captcha_screenshot = captcha_element.screenshot_as_png
            
            # Save the image
            with open(captcha_path, 'wb') as f:
                f.write(captcha_screenshot)
            
            logger.info(f"CAPTCHA image saved: {captcha_path}")
            return captcha_filename
            
        except Exception as e:
            logger.error(f"Error saving CAPTCHA image: {str(e)}")
            return None
    
    def _submit_and_parse_results_with_timeout(self, driver, captcha_solution=None, timeout=20):
        """Submit form with strict timeout protection"""
        try:
            # If CAPTCHA solution provided, fill it in
            if captcha_solution:
                logger.info("Filling CAPTCHA solution...")
                captcha_input_selectors = [
                    "//input[contains(@name,'captcha')]",
                    "//input[contains(@id,'captcha')]",
                    "//input[contains(@placeholder,'captcha')]"
                ]
                
                captcha_input = None
                for selector in captcha_input_selectors:
                    try:
                        captcha_input = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, selector))
                        )
                        break
                    except:
                        continue
                
                if captcha_input:
                    captcha_input.clear()
                    captcha_input.send_keys(captcha_solution)
                    logger.info("CAPTCHA solution entered")
                else:
                    logger.error("Could not find CAPTCHA input field")
                    return None
            
            # Find submit button with timeout
            submit_selectors = [
                "//input[@type='submit']",
                "//button[@type='submit']", 
                "//input[@value='Search']",
                "//button[contains(text(),'Search')]"
            ]
            
            submit_button = None
            for selector in submit_selectors:
                try:
                    submit_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    break
                except:
                    continue
            
            if not submit_button:
                logger.error("Submit button not found")
                return None
            
            # Click submit with timeout protection
            logger.info("Clicking submit button...")
            submit_button.click()
            
            # Wait for response with STRICT timeout
            logger.info(f"Waiting for response (max {timeout} seconds)...")
            
            try:
                # Wait for ANY change in the page
                WebDriverWait(driver, timeout).until(
                    EC.any_of(
                        # Page content changes
                        EC.presence_of_element_located((By.TAG_NAME, "table")),
                        # Error messages appear
                        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "No records found"),
                        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Invalid"),
                        # CAPTCHA appears
                        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "captcha"),
                        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "CAPTCHA"),
                        # URL changes
                        EC.url_changes(driver.current_url)
                    )
                )
            except TimeoutException:
                logger.warning(f"TIMEOUT: No response after {timeout} seconds")
                return "timeout"
            
            # Quick checks for different response types
            page_source = driver.page_source.lower()
            
            # Check for CAPTCHA errors
            captcha_errors = ["invalid captcha", "wrong captcha", "incorrect captcha", "captcha mismatch"]
            if any(error in page_source for error in captcha_errors):
                logger.warning("CAPTCHA error detected")
                return "captcha_error"
            
            # Check for new CAPTCHA requirement
            if any(indicator in page_source for indicator in ["captcha", "enter captcha", "security code"]):
                logger.info("New CAPTCHA detected after submission")
                # Save new CAPTCHA and return requirement
                self._handle_captcha(driver)
                return "captcha_required"
            
            # Check for no results
            no_data_indicators = ["no records found", "no data found", "case not found", "invalid case"]
            if any(indicator in page_source for indicator in no_data_indicators):
                logger.info("No case data found")
                return None
            
            # Try to parse results
            logger.info("Parsing case details...")
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            case_data = self._parse_case_details(soup, driver.current_url)
            
            if case_data:
                logger.info("Case data parsed successfully")
            else:
                logger.warning("No meaningful data found in response")
                
            return case_data
            
        except Exception as e:
            logger.error(f"Error in submit and parse with timeout: {str(e)}")
            return None
    
    def _submit_and_parse_results(self, driver, captcha_solution=None):
        """Legacy method - redirect to timeout version"""
        return self._submit_and_parse_results_with_timeout(driver, captcha_solution)
    
    def _parse_case_details(self, soup, current_url):
        """Parse case details from the HTML response with enhanced parsing"""
        case_data = {
            'parties_petitioner': '',
            'parties_respondent': '',
            'filing_date': '',
            'next_hearing_date': '',
            'case_status': '',
            'judge_name': '',
            'order_pdf_links': [],
            'case_history': [],
            'scraped_at': datetime.now().isoformat(),
            'source_url': current_url
        }
        
        try:
            # Enhanced field mapping with more variations
            field_mappings = {
                'parties_petitioner': [
                    'petitioner', 'appellant', 'applicant', 'plaintiff',
                    'petitioner(s)', 'appellant(s)', 'applicant(s)'
                ],
                'parties_respondent': [
                    'respondent', 'defendant', 'opposite party',
                    'respondent(s)', 'defendant(s)'
                ],
                'filing_date': [
                    'filing date', 'date of filing', 'filed on', 'date filed',
                    'registration date', 'date of registration'
                ],
                'next_hearing_date': [
                    'next date', 'next hearing', 'next listing', 'next date of hearing',
                    'next hearing date', 'date of next hearing'
                ],
                'case_status': [
                    'status', 'case status', 'current status', 'present status'
                ],
                'judge_name': [
                    'judge', 'bench', 'coram', 'before', 'hon\'ble',
                    'justice', 'chief justice'
                ]
            }
            
            # Find all tables and divs on the page
            containers = soup.find_all(['table', 'div', 'span'])
            
            for container in containers:
                # Look for case information in table rows
                if container.name == 'table':
                    rows = container.find_all('tr')
                    
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 2:
                            label = cells[0].get_text(strip=True).lower()
                            value = cells[1].get_text(strip=True)
                            
                            # Map fields using enhanced mappings
                            for field, keywords in field_mappings.items():
                                if any(keyword in label for keyword in keywords):
                                    if value and value != '-' and value.lower() != 'not available':
                                        case_data[field] = value
                                    break
                
                # Look for case information in divs with specific classes or patterns
                elif container.name in ['div', 'span']:
                    text_content = container.get_text(strip=True)
                    if ':' in text_content:
                        parts = text_content.split(':', 1)
                        if len(parts) == 2:
                            label = parts[0].strip().lower()
                            value = parts[1].strip()
                            
                            # Map fields using enhanced mappings
                            for field, keywords in field_mappings.items():
                                if any(keyword in label for keyword in keywords):
                                    if value and value != '-' and value.lower() != 'not available':
                                        case_data[field] = value
                                    break
            
            # Extract PDF links
            case_data['order_pdf_links'] = self._extract_pdf_links(soup)
            
            # Extract case history/chronology if available
            case_data['case_history'] = self._extract_case_history(soup)
            
            # Clean up empty fields
            for key, value in case_data.items():
                if isinstance(value, str) and (not value.strip() or value.strip() == '-'):
                    case_data[key] = 'Not available'
            
            # Validate that we found at least some data
            data_found = any(
                case_data[key] != 'Not available' 
                for key in ['parties_petitioner', 'parties_respondent', 'filing_date', 'case_status']
            )
            
            if data_found:
                logger.info("Case details parsed successfully")
                return case_data
            else:
                logger.warning("No meaningful case data found")
                return None
            
        except Exception as e:
            logger.error(f"Error parsing case details: {str(e)}")
            return case_data
    
    def _extract_pdf_links(self, soup):
        """Extract PDF document links with enhanced detection"""
        pdf_links = []
        
        try:
            # Look for PDF links with multiple patterns
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link['href']
                link_text = link.get_text(strip=True)
                
                # Enhanced PDF detection
                is_pdf = (
                    href.lower().endswith('.pdf') or
                    'pdf' in href.lower() or
                    'order' in link_text.lower() or
                    'judgment' in link_text.lower() or
                    'judgement' in link_text.lower() or
                    'notice' in link_text.lower() or
                    'document' in link_text.lower() or
                    'download' in link_text.lower()
                )
                
                if is_pdf and href != '#':
                    # Convert relative URLs to absolute
                    if href.startswith('http'):
                        full_url = href
                    else:
                        full_url = urljoin(self.base_url, href)
                    
                    pdf_links.append({
                        'url': full_url,
                        'text': link_text or 'Court Document',
                        'type': self._classify_document(link_text)
                    })
        
        except Exception as e:
            logger.error(f"Error extracting PDF links: {str(e)}")
        
        return pdf_links
    
    def _classify_document(self, text):
        """Classify document type based on link text"""
        text_lower = text.lower()
        
        if 'order' in text_lower:
            return 'Order'
        elif 'judgment' in text_lower or 'judgement' in text_lower:
            return 'Judgment'
        elif 'notice' in text_lower:
            return 'Notice'
        elif 'petition' in text_lower:
            return 'Petition'
        elif 'application' in text_lower:
            return 'Application'
        else:
            return 'Document'
    
    def _extract_case_history(self, soup):
        """Extract case hearing history if available"""
        history = []
        
        try:
            # Look for hearing history tables with enhanced detection
            tables = soup.find_all('table')
            
            for table in tables:
                # Check if this table contains hearing dates
                header_row = table.find('tr')
                if header_row:
                    header_text = header_row.get_text().lower()
                    
                    # Enhanced history table detection
                    history_indicators = [
                        'date', 'hearing', 'proceeding', 'order', 'next date',
                        'listing', 'cause list', 'history', 'chronology'
                    ]
                    
                    if any(keyword in header_text for keyword in history_indicators):
                        rows = table.find_all('tr')[1:]  # Skip header
                        
                        for row in rows:
                            cells = row.find_all(['td', 'th'])
                            if len(cells) >= 2:
                                date = cells[0].get_text(strip=True)
                                proceedings = cells[1].get_text(strip=True)
                                
                                if date and proceedings and date != '-' and proceedings != '-':
                                    history.append({
                                        'date': date,
                                        'proceedings': proceedings[:500]  # Limit length
                                    })
        
        except Exception as e:
            logger.error(f"Error extracting case history: {str(e)}")
        
        return history[:15]  # Limit to last 15 entries
    
    def get_case_types(self):
        """Get available case types from the court website with enhanced fallback"""
        urls_to_try = [self.search_url] + self.alternative_urls
        
        for url in urls_to_try:
            driver = None
            try:
                logger.info(f"Attempting to fetch case types from: {url}")
                
                driver = self.setup_driver()
                driver.get(url)
                
                # Wait for case type dropdown to load with multiple selectors
                case_type_selectors = [
                    (By.NAME, "case_type"),
                    (By.ID, "case_type"),
                    (By.CLASS_NAME, "case-type"),
                    (By.XPATH, "//select[contains(@name,'case')]")
                ]
                
                case_type_element = None
                for selector in case_type_selectors:
                    try:
                        case_type_element = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located(selector)
                        )
                        break
                    except:
                        continue
                
                if case_type_element:
                    case_type_select = Select(case_type_element)
                    options = []
                    
                    for option in case_type_select.options:
                        text = option.text.strip()
                        if text and text.lower() not in ["select", "", "choose", "select case type"]:
                            options.append(text)
                    
                    if options:
                        logger.info(f"Retrieved {len(options)} case types from court website")
                        return options
                
            except Exception as e:
                logger.error(f"Error fetching case types from {url}: {str(e)}")
                continue
            finally:
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
        
        # Enhanced fallback case types for Delhi High Court
        logger.info("Using enhanced fallback case types")
        return [
            "ARB.A. (Arbitration Appeal)",
            "BAIL APPLN. (Bail Application)",
            "C.M.(MAIN) (Civil Miscellaneous Main)",
            "C.M.(M) (Civil Miscellaneous)",
            "C.O. (Company Original)",
            "C.R. (Civil Revision)",
            "CRL.A. (Criminal Appeal)",
            "CRL.M.C. (Criminal Miscellaneous)",
            "CRL.REV.P. (Criminal Revision Petition)",
            "CS(COMM) (Commercial Suit)",
            "CS(OS) (Original Suit)",
            "FAO (First Appeal from Order)",
            "LPA (Letters Patent Appeal)",
            "MAT.APP. (Matrimonial Appeal)",
            "RFA (Regular First Appeal)",
            "W.A. (Writ Appeal)",
            "W.P.(C) (Writ Petition Civil)",
            "W.P.(CRL) (Writ Petition Criminal)"
        ]
    
    def test_connection(self):
        """Test connection to court website with multiple URLs"""
        urls_to_test = [
            self.base_url,
            self.search_url,
        ] + self.alternative_urls
        
        for url in urls_to_test:
            try:
                logger.info(f"Testing connection to: {url}")
                response = self.session.get(url, timeout=15)
                
                if response.status_code == 200:
                    logger.info(f"Successfully connected to {url}")
                    return True, f"Connected to {url}"
                else:
                    logger.warning(f"HTTP {response.status_code} from {url}")
                    
            except Exception as e:
                logger.warning(f"Connection failed to {url}: {str(e)}")
                continue
        
        return False, "All connection attempts failed - court website may be unavailable"
