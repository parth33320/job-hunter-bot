"""Base class for all ATS appliers."""
from abc import ABC, abstractmethod
from playwright.async_api import Page, Browser
from src.config import CONFIG
from src.utils import human_delay

class BaseApplier(ABC):
    """Base class that all ATS appliers inherit from."""
    
    def __init__(self, page: Page):
        self.page = page
        self.config = CONFIG
        self.applicant = CONFIG['applicant']
        self.eeo = CONFIG['eeo_responses']
    
    @abstractmethod
    async def apply(self, job_url: str, resume_path: str) -> bool:
        """Apply to a job. Returns True if successful."""
        pass
    
    async def fill_text_field(self, selector: str, value: str):
        """Fill a text field with human-like delay."""
        try:
            element = self.page.locator(selector).first
            if await element.is_visible():
                await element.fill(value)
                human_delay(0.3, 0.8)
                return True
        except Exception:
            pass
        return False
    
    async def click_button(self, selector: str):
        """Click a button with delay."""
        try:
            element = self.page.locator(selector).first
            if await element.is_visible():
                await element.click()
                human_delay(0.5, 1.5)
                return True
        except Exception:
            pass
        return False
    
    async def select_dropdown_option(self, selector: str, target_value: str):
        """Select dropdown option using fuzzy matching."""
        try:
            dropdown = self.page.locator(selector).first
            if not await dropdown.is_visible():
                return False
            
            # Get all options
            options = await dropdown.locator('option').all_text_contents()
            
            # Try exact match first
            for option in options:
                if target_value.lower() == option.lower():
                    await dropdown.select_option(label=option)
                    return True
            
            # Try partial match
            for option in options:
                if target_value.lower() in option.lower():
                    await dropdown.select_option(label=option)
                    return True
            
            # Fallback: select "Prefer not to answer" or first option
            for option in options:
                if "prefer not" in option.lower() or "decline" in option.lower():
                    await dropdown.select_option(label=option)
                    return True
            
            # Last resort: first non-empty option
            if len(options) > 1:
                await dropdown.select_option(index=1)
                return True
                
        except Exception:
            pass
        return False
    
    async def handle_required_textarea(self, label_text: str) -> str:
        """Generate appropriate response for required text fields."""
        label_lower = label_text.lower()
        
        if "portfolio" in label_lower or "website" in label_lower or "github" in label_lower:
            return "N/A"
        
        if "why" in label_lower and ("company" in label_lower or "work" in label_lower or "join" in label_lower):
            return ("I would like to use my client management, data analysis, and project management "
                    "skills to expand your business by improving client relationships and driving "
                    "operational efficiency.")
        
        if "salary" in label_lower or "compensation" in label_lower:
            return self.applicant['salary_expectation']
        
        if "cover letter" in label_lower:
            return "Please see my attached resume for my qualifications."
        
        # Default
        return "N/A"
    
    async def upload_resume(self, selector: str, resume_path: str):
        """Upload resume file."""
        try:
            await self.page.set_input_files(selector, resume_path)
            human_delay(1, 2)
            return True
        except Exception as e:
            print(f"❌ Failed to upload resume: {e}")
            return False
    
    async def take_screenshot(self, path: str):
        """Take screenshot of current page."""
        await self.page.screenshot(path=path, full_page=True)
        print(f"📸 Screenshot saved: {path}")
