"""Apply to jobs on Greenhouse."""
from src.appliers.base_applier import BaseApplier
from src.utils import human_delay

class GreenhouseApplier(BaseApplier):
    """Handles Greenhouse job applications."""
    
    async def apply(self, job_url: str, resume_path: str) -> bool:
        """Apply to a Greenhouse job."""
        
        print(f"🌱 Applying via Greenhouse: {job_url}")
        
        try:
            # Navigate to job page
            await self.page.goto(job_url, wait_until='networkidle')
            human_delay(2, 4)
            
            # Click Apply button if on job description page
            apply_button = self.page.locator('a:has-text("Apply"), button:has-text("Apply")')
            if await apply_button.first.is_visible():
                await apply_button.first.click()
                human_delay(2, 3)
            
            # Fill basic info
            await self.fill_text_field('input[name="first_name"]', self.applicant['first_name'])
            await self.fill_text_field('input[name="last_name"]', self.applicant['last_name'])
            await self.fill_text_field('input[name="email"]', self.applicant['email'])
            await self.fill_text_field('input[name="phone"]', self.applicant['phone'])
            
            # LinkedIn (optional)
            await self.fill_text_field('input[name*="linkedin"]', self.applicant['linkedin_url'])
            
            # Upload resume
            resume_input = 'input[type="file"][name*="resume"], input[type="file"][data-field="resume"]'
            await self.upload_resume(resume_input, resume_path)
            
            # Handle custom questions
            await self._handle_custom_questions()
            
            # Handle EEO section if present
            await self._handle_eeo_section()
            
            return True
            
        except Exception as e:
            print(f"❌ Greenhouse application error: {e}")
            return False
    
    async def _handle_custom_questions(self):
        """Handle custom text fields and dropdowns."""
        
        # Find all required fields
        fields = await self.page.locator('.field.required, [data-required="true"]').all()
        
        for field in fields:
            try:
                # Get the label/question
                label_el = field.locator('label').first
                label_text = await label_el.text_content() if await label_el.count() > 0 else ""
                
                # Check for textarea
                textarea = field.locator('textarea')
                if await textarea.count() > 0 and await textarea.first.is_visible():
                    current_value = await textarea.first.input_value()
                    if not current_value:
                        response = await self.handle_required_textarea(label_text)
                        await textarea.first.fill(response)
                
                # Check for select dropdown
                select = field.locator('select')
                if await select.count() > 0 and await select.first.is_visible():
                    # Determine appropriate response
                    label_lower = label_text.lower()
                    
                    if "sponsor" in label_lower or "visa" in label_lower or "authorization" in label_lower:
                        await self.select_dropdown_option('select', self.eeo['require_sponsorship'])
                    elif "gender" in label_lower:
                        await self.select_dropdown_option('select', self.eeo['gender'])
                    elif "veteran" in label_lower:
                        await self.select_dropdown_option('select', self.eeo['veteran_status'])
                    elif "disability" in label_lower:
                        await self.select_dropdown_option('select', self.eeo['disability_status'])
                    elif "hear" in label_lower or "source" in label_lower:
                        await self.select_dropdown_option('select', self.eeo['how_did_you_hear'])
                    else:
                        # Default: pick first option or "prefer not to answer"
                        await self.select_dropdown_option('select', "Prefer not to answer")
                
            except Exception:
                continue
    
    async def _handle_eeo_section(self):
        """Handle Equal Employment Opportunity section."""
        
        # Common EEO dropdowns
        eeo_mappings = {
            'gender': self.eeo['gender'],
            'race': self.eeo['race_ethnicity'],
            'ethnicity': self.eeo['race_ethnicity'],
            'veteran': self.eeo['veteran_status'],
            'disability': self.eeo['disability_status'],
        }
        
        for keyword, response in eeo_mappings.items():
            selects = await self.page.locator(f'select[name*="{keyword}"], select[id*="{keyword}"]').all()
            for select in selects:
                try:
                    if await select.is_visible():
                        await select.select_option(label=response)
                        human_delay(0.3, 0.6)
                except Exception:
                    continue
    
    async def submit(self) -> bool:
        """Click the submit button."""
        try:
            submit_btn = self.page.locator('button[type="submit"], input[type="submit"], button:has-text("Submit")')
            await submit_btn.first.click()
            human_delay(2, 4)
            
            # Check for success message
            success = await self.page.locator('text=/thank|success|received|submitted/i').first.is_visible()
            return success
            
        except Exception as e:
            print(f"❌ Submit error: {e}")
            return False
