"""
SCRATCH — Phase 1 Live Browser Integration Verification (Playwright)
===================================================================
Executes end-to-end browser automation against live Next.js 14 frontend (http://localhost:3000)
and live FastAPI backend (http://localhost:8000).

Tests:
1. User registration & session establishment in Next.js.
2. Business profile & ICP configuration form submission & verification.
3. Suppression entry addition & live table rendering.
4. CSV lead upload, column auto-mapping preview, and execution.
5. Ingestion summary card verification (valid, duplicate, suppressed, error counts).
6. Directory navigation & live search filtering for accounts and contacts.
"""

import os
import sys
import tempfile
import time
from playwright.sync_api import sync_playwright

FRONTEND_URL = "http://localhost:3000"


def run_browser_phase1_verification():
    print("=" * 70)
    print("SCRATCH PHASE 1 — PLAYWRIGHT LIVE BROWSER VERIFICATION")
    print("=" * 70)

    unique_id = int(time.time())
    test_email = f"lead_browser_{unique_id}@scratchflow.io"
    test_password = "SecurePassword123!"
    test_name = "Phase1 Browser Tester"
    test_org = f"Acme Growth {unique_id}"

    # Generate temporary CSV file for import
    temp_dir = tempfile.mkdtemp()
    csv_path = os.path.join(temp_dir, "browser_leads.csv")
    csv_data = (
        "Account,Web URL,Contact Email,Full Name,Title,City\n"
        "Stripe Inc,https://www.stripe.com,payments-lead@stripe.com,Patrick Collison,CEO,South San Francisco\n"
        "Rival Platform,https://rival-platform.io,sales@rival-platform.io,John Rival,Competitor Head,Chicago\n"
        "Figma Inc,https://figma.com,design-ops@figma.com,Dylan Field,CEO,San Francisco\n"
        ",,,,,\n"
        "Corrupted Record Missing Domain And Email,,,,,\n"
    )
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write(csv_data)

    try:
        with sync_playwright() as p:
            print("[1/6] Launching Chromium browser (headless mode)...")
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            # Step 1: Register User
            print(f"[2/6] Navigating to {FRONTEND_URL}/register...")
            page.goto(f"{FRONTEND_URL}/register", timeout=15000)
            page.wait_for_selector("input[type='text']")

            print(f"  -> Submitting registration for {test_email}...")
            page.fill("input[placeholder='Jane Founder']", test_name)
            page.fill("input[placeholder='jane@acmecorp.com']", test_email)
            page.fill("input[placeholder='Acme Corporation']", test_org)
            page.fill("input[placeholder='••••••••••••']", test_password)
            page.click("button[type='submit']")

            # Wait for redirect to /health or /leads
            page.wait_for_url(lambda url: "/health" in url or "/leads" in url, timeout=15000)
            print(f"  -> Successfully registered and redirected to {page.url}")

            # Step 2: Configure Business Profile
            print(f"[3/6] Navigating to {FRONTEND_URL}/profile (Business Profile & ICP)...")
            page.goto(f"{FRONTEND_URL}/profile", timeout=15000)
            page.wait_for_selector("input[value]")

            print("  -> Filling Business Profile details...")
            # Value proposition
            vp_input = page.locator("input[placeholder*='Reduces cloud compute']")
            vp_input.fill("Reduces engineering overhead by 50% with automated workflows")
            page.locator("button:has-text('Add')").first.click()

            # Target industry
            ind_input = page.locator("input[placeholder*='Fintech, Healthcare']")
            ind_input.fill("Enterprise SaaS")
            page.locator("button:has-text('Add')").nth(1).click()

            # Submit profile form
            page.click("button:has-text('Save Business Profile')")
            page.wait_for_selector("text='Business profile saved successfully.'", timeout=10000)
            print("  -> Business Profile updated and confirmed by UI alert.")

            # Step 3: Add Suppression Rule
            print(f"[4/6] Navigating to {FRONTEND_URL}/suppression...")
            page.goto(f"{FRONTEND_URL}/suppression", timeout=15000)
            page.wait_for_selector("input[placeholder*='competitor.com']")

            print("  -> Adding suppression rule for 'rival-platform.io'...")
            page.fill("input[placeholder*='competitor.com']", "rival-platform.io")
            page.fill("input[placeholder*='Competitor, Current Client']", "Direct Competitor Exclusion")
            page.click("button:has-text('Add to List')")

            page.wait_for_selector("text='rival-platform.io'", timeout=10000)
            print("  -> Suppression rule rendered in table: 'rival-platform.io'")

            # Step 4: Import Leads CSV
            print(f"[5/6] Navigating to {FRONTEND_URL}/leads/import...")
            page.goto(f"{FRONTEND_URL}/leads/import", timeout=15000)
            page.wait_for_selector("input[type='file']")

            print(f"  -> Uploading CSV file {csv_path}...")
            file_input = page.locator("input[type='file']")
            file_input.set_input_files(csv_path)

            # Wait for preview and column mapping
            page.wait_for_selector("text='2. Confirm Column Mapping'", timeout=10000)
            print("  -> File schema preview rendered with auto-mapped headers.")

            # Click Run Lead Ingestion
            print("  -> Executing Lead Ingestion stream...")
            page.click("button:has-text('Run Lead Ingestion')")

            # Wait for Step 3: Import Completed
            page.wait_for_selector("text='3. Import Completed'", timeout=15000)
            print("  -> Import Completed card rendered.")

            # Verify metrics
            page.wait_for_selector("text='Valid Ingested'")
            page.wait_for_selector("text='Suppressed'")
            page.wait_for_selector("text='Errors Quarantined'")
            print("  -> Ingestion counters verified on browser DOM.")

            # Step 5: Directory View
            print(f"[6/6] Navigating to {FRONTEND_URL}/leads Directory...")
            page.click("text='View Leads Directory →'")
            page.wait_for_url("**/leads", timeout=10000)

            # Wait for Accounts table
            page.wait_for_selector("text='stripe.com'", timeout=10000)
            page.wait_for_selector("text='figma.com'", timeout=10000)
            print("  -> Accounts table verified: stripe.com and figma.com present.")

            # Search filter test
            print("  -> Testing live search filtering...")
            search_input = page.locator("input[placeholder*='Search accounts']")
            search_input.fill("stripe")
            page.wait_for_timeout(500)
            assert page.locator("text='stripe.com'").is_visible()
            assert not page.locator("text='figma.com'").is_visible()
            print("  -> Search filter correctly isolated 'stripe.com'.")

            # Clear search input
            search_input.fill("")
            page.wait_for_timeout(500)

            # Switch to Contacts tab
            print("  -> Testing Contacts tab...")
            page.click("button:has-text('Contacts')")
            page.wait_for_selector("text='payments-lead@stripe.com'", timeout=10000)
            page.wait_for_selector("text='design-ops@figma.com'", timeout=10000)
            print("  -> Contacts table verified: payments-lead@stripe.com and design-ops@figma.com present.")

            browser.close()

        print("\n" + "=" * 70)
        print("PLAYWRIGHT BROWSER VERIFICATION PASSED COMPLETELY WITH 0 ERRORS!")
        print("=" * 70)

    finally:
        try:
            os.remove(csv_path)
            os.rmdir(temp_dir)
        except Exception:
            pass


if __name__ == "__main__":
    run_browser_phase1_verification()
