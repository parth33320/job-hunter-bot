"""Apply to jobs on Workday - More complex due to account creation."""
from src.appliers.base_applier import BaseApplier
from src.utils import human_delay
from src.gmail_reader import get_latest_otp

class WorkdayApplier(BaseApplier):
    """Handles Workday job applications."""
    
    async def apply(self, job_url: str, resume_path: str) -> bool:
        """Apply to a Workday job."""
        
        print(f"💼 Applying via Workday: {job_url}")
        
        try:
            await self.page.goto(job_url, wait_until='networkidle')
            human_delay(3, 5)
            
            # Click Apply button
            apply_btn = self.page.locator('a[data-automation-id="jobPostingApplyButton"], button:has-text("Apply")')
            if await apply_btn.first.is_visible():
                await apply_btn.first.click()
                human_delay(2, 4)
            
            # Check if we need to create account or sign in
            create_account = self.page.locator('a:has-text("Create Account"), button:has-text("Create Account")')
            if await create_account.first.is_visible():
                await self._create_account()
            
            # Check for sign in option (if we already have account)
            sign_in = self.page.locator('a:has-text("Sign In"), button:has-text("Sign In")')
            if await sign_in.first.is_visible():
                await self._sign_in()
            
            # Fill application form
            await self._fill_application(resume_path)
            
            return True
            
        except Exception as e:
            print(f"❌ Workday application error: {e}")
            return False
    
    async def _create_account(self):
        """Create a new Workday account."""
        print("📝 Creating Workday account...")
        
        create_btn = self.page.locator('a:has-text("Create Account"), button:has-text("Create Account")')
        await create_btn.first.click()
        human_delay(2, 3)
        
        # Fill email
        await self.fill_text_field('input[data-automation-id="email"]', self.applicant['email'])
        
        # Generate and fill password (Workday requires specific format)
        password = "JobHunt2024!#"  # Meets most requirements
        await self.fill_text_field('input[data-automation-id="password"]', password)
        await self.fill_text_field('input[data-automation-id="verifyPassword"]', password)
        
        # Click create
        await self.click_button('button[data-automation-id="createAccountSubmitButton"]')
        human_delay(3, 5)
        
        # Wait for OTP email and enter it
        print("📧 Waiting for verification email...")
        otp = get_latest_otp(sender_filter="workday", max_wait_seconds=120)
        
        if otp:
            await self.fill_text_field('input[data-automation-id="verificationCode"]', otp)
            await self.click_button('button[data-automation-id="verifyButton"]')
            human_delay(2, 4)
        else:
            print("⚠️ Could not get OTP, may need manual intervention")
    
    async def _sign_in(self):
        """Sign in to existing Workday account."""
        print("🔑 Signing in to Workday...")
        
        sign_in_btn = self.page.locator('a:has-text("Sign In")')
        await sign_in_btn.first.click()
        human_delay(2, 3)
        
        await self.fill_text_field('input[data-automation-id="email"]', self.applicant['email'])
        await self.fill_text_field('input[data-automation-id="password"]', "JobHunt2024!#")
        await self.click_button('button[data-automation-id="signInSubmitButton"]')
        human_delay(3, 5)
    
    async def _fill_application(self, resume_path: str):
        """Fill out the Workday application form."""
        
        # Upload resume - Workday often auto-parses
        resume_input = 'input[data-automation-id="file-upload-input-ref"]'
        await self.upload_resume(resume_input, resume_path)
        human_delay(3, 5)  # Wait for parsing
        
        # Fill personal info (may be pre-filled from resume)
        await self.fill_text_field('input[data-automation-id="legalNameSection_firstName"]', self.applicant['first_name'])
        await self.fill_text_field('input[data-automation-id="legalNameSection_lastName"]', self.applicant['last_name'])
        await self.fill_text_field('input[data-automation-id="phone-number"]', self.applicant['phone'])
        
        # Address
        await self.fill_text_field('input[data-automation-id="addressSection_addressLine1"]', self.applicant['address']['street'])
        await self.fill_text_field('input[data-automation-id="addressSection_city"]', self.applicant['address']['city'])
        await self.fill_text_field('input[data-automation-id="addressSection_postalCode"]', self.applicant['address']['zip'])
        
        # Work History
        work = self.config['work_history'][0]
        await self.fill_text_field('input[data-automation-id="jobTitle"]', work['title'])
        await self.fill_text_field('input[data-automation-id="company"]', work['company'])
        await self.fill_text_field('input[data-automation-id="location"]', work['location'])
        
        # Education
        edu = self.config['education'][0]
        await self.fill_text_field('input[data-automation-id="school"]', edu['school'])
        await self.fill_text_field('input[data-automation-id="degree"]', f"{edu['degree']} in {edu['field']}")
        
        # EEO Questions
        await self._handle_eeo()
        
        # Click through pages (Workday has multi-step forms)
        while True:
            next_btn = self.page.locator('button[data-automation-id="bottom-navigation-next-button"]')
            if await next_btn.is_visible():
                await next_btn.click()
                human_delay(2, 4)
            else:
                break
    
    async def _handle_eeo(self):
        """Handle Workday EEO questions."""
        
        # Citizenship
        us_citizen = self.page.locator('text=/authorized to work/i').first
        if await us_citizen.is_visible():
            yes_radio = self.page.locator('input[type="radio"][value="Yes"]').first
            await yes_radio.click()
        
        # Sponsorship
        sponsorship = self.page.locator('text=/sponsorship/i').first
        if await sponsorship.is_visible():
            no_radio = self.page.locator('input[type="radio"][value="No"]').first
            await no_radio.click()
        
        # Previous employment
        prev_emp = self.page.locator('text=/previously employed/i').first
        if await prev_emp.is_visible():
            no_radio = self.page.locator('input[type="radio"][value="No"]').first
            await no_radio.click()
    
    async def submit(self) -> bool:
        """Submit the Workday application."""
        try:
            submit_btn = self.page.locator('button[data-automation-id="bottom-navigation-next-button"]:has-text("Submit")')
            await submit_btn.click()
            human_delay(3, 5)
            
            # Look for confirmation
            success = await self.page.locator('text=/submitted|thank you|received/i').first.is_visible()
            return success
            
        except Exception as e:
            print(f"❌ Workday submit error: {e}")
            return False
