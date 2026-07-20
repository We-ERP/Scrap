import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import pandas as pd
import time
import requests
from selenium.common.exceptions import TimeoutException, WebDriverException

# رابط الـ Web App بتاعك
GOOGLE_WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzKWdWi9qc4e7I5xF8tvDciSZ4Fh1DygtOvRocRbwaFi19AJ3wXMKekrrDcSE4w2wCL/exec"

# قراءة القسم المطلوب من بيئة التشغيل (عشان نربطه بواجهة الـ HTML)
TARGET_CATEGORY_KEY = os.getenv("TARGET_CATEGORY", "all")

print("🚀 جاري تشغيل متصفح Chrome في الوضع الخفي الشامل...")
options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080") 
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
options.add_argument("--lang=ar-EG")
options.page_load_strategy = 'eager' 

driver = webdriver.Chrome(options=options)
driver.set_page_load_timeout(120) 
driver.set_script_timeout(120)

all_scraped_data = []

# الأقسام المحددة اللي طلبتها
TARGET_CATEGORIES = {
    "health": {"url": "https://www.rayashop.com/ar/health-and-beauty", "name": "الصحة والجمال"},
    "small_app": {"url": "https://www.rayashop.com/ar/small-appliances", "name": "أجهزة صغيرة"},
    "kitchen": {"url": "https://www.rayashop.com/ar/home-appliances/kitchen-appliances", "name": "أجهزة المطبخ"}
}

try:
    product_tasks = []
    
    for cat_key, cat_info in TARGET_CATEGORIES.items():
        if TARGET_CATEGORY_KEY != "all" and TARGET_CATEGORY_KEY != cat_key:
            continue # لو مختار قسم معين من الواجهة، هيتجاهل الباقي
            
        cat_url = cat_info["url"]
        cat_name = cat_info["name"]
        print(f"\n📂 جاري تجميع روابط المنتجات من [ قسم: {cat_name} ]")
        
        seen_urls_in_category = set()
        page_num = 1
        
        while True:
            page_url = f"{cat_url}?p={page_num}"
            print(f"   📄 فحص الصفحة رقم ({page_num}) -> {page_url}")
            
            try:
                driver.get(page_url)
                time.sleep(5) 
            except Exception as e:
                print(f"   ⚠️ حدث خطأ أثناء فتح الصفحة: {e}")
                break 
            
            print("   ⬇️ جاري النزول لآخر الصفحة والضغط على (تحميل المزيد)...")
            last_height = driver.execute_script("return document.body.scrollHeight")
            
            while True:
                # سكرول لآخر الصفحة
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                # البحث عن زرار تحميل المزيد والضغط عليه
                try:
                    load_more_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'تحميل المزيد') or contains(@class, 'load-more')]")
                    if load_more_btn.is_displayed():
                        driver.execute_script("arguments[0].click();", load_more_btn)
                        print("      🔘 تم الضغط على زرار تحميل المزيد...")
                        time.sleep(4) # انتظار تحميل المنتجات الجديدة
                except:
                    pass # الزرار مش موجود أو اختفى
                
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    time.sleep(3) # تأكيد أخير
                    if driver.execute_script("return document.body.scrollHeight") == last_height:
                        break # وصلنا للنهاية الفعلية
                last_height = new_height
            
            # استخراج الروابط بشكل دقيق
            links = driver.execute_script("""
                var urls = [];
                var items = document.querySelectorAll('.product-item-info a.product-item-link, .ProductsGrid a');
                for (var i = 0; i < items.length; i++) {
                    urls.push(items[i].href);
                }
                return urls;
            """)
            
            new_links_found = 0
            for p_link in links:
                if p_link and "/ar/" in p_link:
                    clean_p_link = p_link.split('?')[0]
                    if clean_p_link not in seen_urls_in_category:
                        seen_urls_in_category.add(clean_p_link)
                        product_tasks.append((clean_p_link, cat_name))
                        new_links_found += 1
            
            print(f"   ✨ تم لقط {new_links_found} رابط منتج جديد.")
            
            if new_links_found == 0:
                print(f"   ⏹️ تم جمع كافة الروابط المتاحة لقسم ({cat_name}).")
                break
            page_num += 1

    print(f"\n🔥 إجمالي الروابط التي تم جمعها: {len(product_tasks)} منتج.")

    # --- الدخول لصفحة كل منتج وسحب البيانات ---
    for index, (p_url, fallback_cat) in enumerate(product_tasks, 1):
        print(f"   🔄 جاري قشط المنتج رقم ({index}/{len(product_tasks)}) -> {p_url}")
        try:
            driver.get(p_url)
            time.sleep(2)
        except:
            continue 
        
        try:
            try:
                product_name = driver.find_element(By.TAG_NAME, "h1").text.strip()
            except:
                product_name = "N/A"
                
            try:
                brand_element = driver.find_element(By.CSS_SELECTOR, ".product-brand-name, a[href*='/ar/brands/']")
                brand_name = brand_element.text.strip()
            except:
                brand_name = "N/A"
                
            try:
                price_element = driver.find_element(By.CSS_SELECTOR, "[data-price-type='finalPrice'] .price")
                exact_price = price_element.text.replace("جنيه", "").replace("EGP", "").strip()
            except:
                exact_price = "N/A"
                
            # التعديل الجوهري لمنع تداخل الداتا في حقل الكاتيجوري
            product_category = fallback_cat
            try:
                breadcrumbs = driver.find_elements(By.CSS_SELECTOR, ".breadcrumbs li a")
                cat_names = [c.text.strip() for c in breadcrumbs if c.text.strip() and c.text.strip() not in ["الرئيسية", "Home"]]
                if cat_names:
                    product_category = " > ".join(cat_names)
            except:
                pass

            image_urls = []
            try:
                img_tags = driver.find_elements(By.CSS_SELECTOR, ".product.media img, .gallery-placeholder img")
                for img in img_tags:
                    src = img.get_attribute("src")
                    if src and src not in image_urls:
                        image_urls.append(src)
            except:
                pass

            product_data = {
                "كاتيجوري": product_category,
                "اسم المنتج": product_name,
                "كود المنتج": "N/A", # تم إزالته مؤقتاً لتجنب أخطاء التقسيم العشوائي للاسم
                "اسم البراند": brand_name,
                "سعر المنتج": exact_price,
                "لينك المنتج": p_url
            }
            
            for img_idx, img_url in enumerate(image_urls[:3], 1): # سحب أول 3 صور فقط لتخفيف الضغط
                product_data[f"صورة {img_idx}"] = img_url
                
            all_scraped_data.append(product_data)
        except Exception:
            continue

    # --- إرسال البيانات لجوجل شيت ---
    if all_scraped_data:
        df = pd.DataFrame(all_scraped_data)
        cleaned_data = df.fillna("").to_dict(orient="records")
        payload = {"products": cleaned_data}
        try:
            response = requests.post(GOOGLE_WEBAPP_URL, json=payload, timeout=180)
            print("✅ تم تحديث شيت جوجل السحابي بنجاح مذهل!")
        except Exception as http_err:
            print(f"❌ خطأ الاتصال: {http_err}")

except Exception as main_error:
    print(f"❌ خطأ عام: {main_error}")
finally:
    driver.quit()