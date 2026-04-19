"""Apply to jobs on iCIMS."""
from src.appliers.base_applier import BaseApplier
from src.utils import human_delay

class ICIMSApplier(BaseApplier):
    """Handles iCIMS job applications."""
    
    async def apply(self, job_url: str, resume_path: str) -> bool:
        """Apply to an iCIMS job."""
        
        print(f"📋 Applying via iCIMS: {job_url}")
        
        try:
            await self.page.goto(job_url, wait_until='networkidle')
            human_delay(2, 4)
            
            # Click Apply Now button
            apply_btn = self.page.locator('a:has-text("Apply Now"), a:has-text("Apply"), button:has-text("Apply")')
            if await apply_btn.first.is_visible():
                await apply_btn.first.click()
                human_delay(2, 4)
            
            # Fill basic info
            await self.fill_text_field('input[name*="firstName"], input[id*="firstName"]', self.applicant['first_name'])
            await self.fill_text_field('input[name*="lastName"], input[id*="lastName"]', self.applicant['last_name'])
            await self.fill_text_field('input[name*="email"], input[id*="email"], input[type="email"]', self.applicant['email'])
            await self.fill_text_field('input[name*="phone"], input[id*="phone"]', self.applicant['phone'])
            
            # Address fields
            await self.fill_text_field('input[name*="address"], input[id*="address"]', self.applicant['address']['street'])
            await self.fill_text_field('input[name*="city"], input[id*="city"]', self.applicant['address']['city'])
            await self.fill_text_field('input[name*="state"], input[id*="state"]', self.applicant['address']['state'])
            await self.fill_text_field('input[name*="zip"], input[id*="zip"], input[name*="postal"]', self.applicant['address']['zip'])
            
            # Upload resume
            resume_input = 'input[type="file"]'
            await self.upload_resume(resume_input, resume_path)
            human_delay(2, 4)
            
            # LinkedIn
            await self.fill_text_field('input[name*="linkedin"], input[id*="linkedin"]', self.applicant['linkedin_url'])
            
            # Handle EEO
            await self._handle_eeo()
            
            # Handle custom questions
            await self._handle_custom_questions()
            
            return True
            
        except Exception as e:
            print(f"❌ iCIMS application error: {e}")
            return False
    
    async def _handle_eeo(self):
        """Handle iCIMS EEO sections."""
        
        dropdowns = await self.page.locator('select').all()
        
        for dropdown in dropdowns:
            try:
                name = await dropdown.get_attribute('name') or ""
                id_attr = await dropdown.get_attribute('id') or ""
                identifier = (name + id_attr).lower()
                
                if 'gender' in identifier:
                    await dropdown.select_option(label=self.eeo['gender'])
                elif 'race' in identifier or 'ethnic' in identifier
