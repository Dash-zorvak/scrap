from playwright.sync_api import sync_playwright

# Without cookies - just check if profile exists
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    print('Navigating to @alcaldiasa...')
    page.goto('https://www.tiktok.com/@alcaldiasa', timeout=30000)
    page.wait_for_timeout(8000)

    print(f'URL: {page.url}')
    print(f'Title: {page.title()}')

    # Check body
    body = page.locator('body').inner_text()
    if 'Couldn\'t find this account' in body:
        print('ERROR: Account not found')
    elif 'For You' in body or 'Following' in body:
        print('SUCCESS: Profile loaded')

        # Count videos
        videos = page.locator('a[href*="/video/"]').count()
        print(f'Videos found: {videos}')

        # Check SIGI
        sigi = page.evaluate("""() => {
            const el = document.getElementById('__UNIVERSAL_DATA_FOR_VIEW__');
            return el ? JSON.parse(el.textContent) : null;
        }""")
        if sigi:
            print(f'SIGI keys: {list(sigi.keys())}')

    browser.close()