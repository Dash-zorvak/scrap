from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    print('Navigating to @alcaldiasa...')
    page.goto('https://www.tiktok.com/@alcaldiasa', timeout=30000)

    # Wait for initial load
    page.wait_for_timeout(5000)

    print('Scrolling...')
    for i in range(5):
        page.evaluate('window.scrollBy(0, 1000)')
        page.wait_for_timeout(1500)

    # Now check for videos
    videos = page.locator('a[href*="/video/"]').count()
    print(f'Videos found after scrolling: {videos}')

    # Get video links
    video_links = page.locator('a[href*="/video/"]').all()
    for v in video_links[:5]:
        print(f'  - {v.get_attribute("href")}')

    input('Press Enter to close...')
    browser.close()