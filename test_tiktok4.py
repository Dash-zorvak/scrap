from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    print('Navigating to @alcaldiasa...')
    page.goto('https://www.tiktok.com/@alcaldiasa', timeout=30000)

    # Wait a long time
    print('Waiting 15 seconds...')
    time.sleep(15)

    # Get the main content
    main = page.locator('main').inner_html()
    print(f'Main HTML length: {len(main)}')

    # Look for any video elements
    video_divs = page.locator('[class*="Video"]').count()
    print(f'Video divs: {video_divs}')

    # Check for any links with video
    all_links = page.locator('a').count()
    print(f'Total links: {all_links}')

    # Get all hrefs
    links = page.locator('a').all()
    video_hrefs = [l.get_attribute('href') for l in links if l.get_attribute('href') and '/video/' in l.get_attribute('href')]
    print(f'Links with /video/: {len(video_hrefs)}')

    input('Press Enter...')
    browser.close()