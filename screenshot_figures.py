import os
import time
from playwright.sync_api import sync_playwright

def generate_screenshots():
    folder = "patent-figures"
    out_png = os.path.join(folder, "png")
    out_jpg = os.path.join(folder, "jpg")
    
    os.makedirs(out_png, exist_ok=True)
    os.makedirs(out_jpg, exist_ok=True)
    
    html_files = [f for f in os.listdir(folder) if f.endswith(".html")]
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # device_scale_factor=8 renders the SVG diagrams at 800% (8K resolution equivalent)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            device_scale_factor=8
        )
        page = context.new_page()
        
        for html_file in html_files:
            base_name = html_file.replace('.html', '')
            abs_path = "file:///" + os.path.abspath(os.path.join(folder, html_file)).replace('\\', '/')
            print(f"Processing {html_file}...")
            
            page.goto(abs_path)
            
            # Wait for mermaid to finish rendering (if applicable)
            page.wait_for_timeout(2000)
            
            # Target the container or the whole page. Full page guarantees white background.
            # But maybe we want just the element bounding box:
            element = None
            if page.locator(".mermaid").is_visible():
                element = page.locator(".mermaid")
            elif page.locator(".html-table-wrapper").is_visible():
                element = page.locator(".html-table-wrapper")
                
            png_path = os.path.join(out_png, f"{base_name}.png")
            jpg_path = os.path.join(out_jpg, f"{base_name}.jpg")
            
            if element:
                element.screenshot(path=png_path)
                element.screenshot(path=jpg_path, type="jpeg", quality=95)
            else:
                page.screenshot(path=png_path, full_page=True)
                page.screenshot(path=jpg_path, type="jpeg", quality=95, full_page=True)
                
        browser.close()
    print("Done! Check patent-figures/png/ and patent-figures/jpg/")

if __name__ == "__main__":
    generate_screenshots()
