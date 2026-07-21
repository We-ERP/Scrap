import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import pandas as pd
import time
import requests

# رابط الـ Web App بتاعك
GOOGLE_WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzKWdWi9qc4e7I5xF8tvDciSZ4Fh1DygtOvRocRbwaFi19AJ3wXMKekrrDcSE4w2wCL/exec"

print("🚀 جاري تشغيل متصفح Chrome في الوضع الخفي المحسن...")
options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080") 
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
options.add_argument("--lang=ar-EG")
options.page_load_strategy = 'eager' 

# إيقاف الصور لتوفير الذاكرة والسرعة
prefs = {"profile.managed_default_content_settings.images": 2}
options.add_experimental_option("prefs", prefs)

driver = webdriver.Chrome(options=options)
driver.set_page_load_timeout(120) 

all_scraped_data = []

# الأقسام التلاتة المطلوبة
TARGET_CATEGORIES = {
    "health": {"url": "https://www.rayashop.com/ar/health-and-beauty", "name": "الصحة والجمال"},
    "small_app": {"url": "https://www.rayashop.com/ar/small-appliances", "name": "أجهزة صغيرة"},
    "kitchen": {"url": "https://www.rayashop.com/ar/home-appliances/kitchen-appliances", "name": "أجهزة المطبخ"}
}

try:
    product_tasks = []
    
    for cat_key, cat_info in TARGET_CATEGORIES.items():
        cat_url = cat_info["url"]
        cat_name = cat_info["name"]
        print(f"\n📂 جاري تجميع روابط المنتجات من [ قسم: {cat_name} ]")
        
        seen_urls_in_category = set()
        page_num = 1
        
        while page_num <= 10:  # حد أقصى آمن لصفحات كل قسم
            page_url = f"{cat_url}?p={page_num}"
            print(f"   📄 فحص الصفحة رقم ({page_num}) -> {page_url}")
            
            try:
                driver.get(page_url)
                time.sleep(3) 
            except Exception as e:
                print(f"   ⚠️ خطأ في فتح الصفحة: {e}")
                break 
            
            # محاكاة التنزيل لأسفل الصفحة لتحميل كل المنتجات الكسلانة (Lazy load)
            last_height = driver.execute_script("return document.body.scrollHeight")
            for _ in range(5):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            
            # استخراج الروابط بدقة من عناصر المنتجات
            links = driver.execute_script("""
                var urls = [];
                var items = document.querySelectorAll('.product-item-info a.product-item-link, .product-item a.product-item-photo, .products.list.items a');
                for (var i = 0; i < items.length; i++) {
                    if (items[i].href) urls.push(items[i].href);
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
            
            print(f"   ✨ تم لقط {new_links_found} رابط جديد في الصفحة {page_num}.")
            
            # لو الصفحة مفيهاش منتجات جديدة، نوقف وننقل للقسم اللي بعده
            if new_links_found == 0:
                print(f"   ⏹️ انتهت صفحات قسم ({cat_name}).")
                break
            page_num += 1

    print(f"\n🔥 إجمالي الروابط المجتمعة لكل الأقسام: {len(product_tasks)} منتج.")

    # --- سحب تفاصيل كل منتج ---
    for index, (p_url, fallback_cat) in enumerate(product_tasks, 1):
        print(f"   🔄 قشط المنتج ({index}/{len(product_tasks)}) -> {p_url}")
        try:
            driver.get(p_url)
            time.sleep(1.2)
        except:
            continue 
        
        try:
            # اسم المنتج
            try:
                product_name = driver.find_element(By.TAG_NAME, "h1").text.strip()
            except:
                product_name = "N/A"
                
            # البراند
            try:
                brand_element = driver.find_element(By.CSS_SELECTOR, ".product-brand-name, a[href*='/ar/brands/']")
                brand_name = brand_element.text.strip()
            except:
                brand_name = "N/A"
                
            # السعر المعدل بدقة لتجنب النقص
            exact_price = "N/A"
            price_selectors = [
                ".product-info-price .price", 
                "[data-price-type='finalPrice'] .price", 
                ".special-price .price", 
                ".price-box .price"
            ]
            for selector in price_selectors:
                try:
                    price_element = driver.find_element(By.CSS_SELECTOR, selector)
                    val = price_element.text.replace("جنيه", "").replace("EGP", "").replace(",", "").strip()
                    if val:
                        exact_price = val
                        break
                except:
                    continue
                
            # الكاتيجوري التفصيلي من المسار
            product_category = fallback_cat
            try:
                breadcrumbs = driver.find_elements(By.CSS_SELECTOR, ".breadcrumbs li")
                cat_names = [c.text.strip() for c in breadcrumbs if c.text.strip() and c.text.strip() not in ["الرئيسية", "Home", "/"]]
                if len(cat_names) > 1:
                    product_category = " > ".join(cat_names[1:-1]) if len(cat_names) > 2 else cat_names[0]
            except:
                pass

            product_data = {
                "كاتيجوري": product_category,
                "اسم المنتج": product_name,
                "كود المنتج": "N/A",
                "اسم البراند": brand_name,
                "سعر المنتج": exact_price,
                "لينك المنتج": p_url
            }
            
            all_scraped_data.append(product_data)
        except Exception:
            continue

    # --- إرسال الداتا لجوجل شيت دفعة واحدة ---
    if all_scraped_data:
        df = pd.DataFrame(all_scraped_data)
        cleaned_data = df.fillna("").to_dict(orient="records")
        payload = {"products": cleaned_data}
        try:
            response = requests.post(GOOGLE_WEBAPP_URL, json=payload, timeout=180)
            print("✅ تم رفع كافة البيانات وتحديث الشيت بنجاح تام!")
        except Exception as http_err:
            print(f"❌ خطأ في الإرسال: {http_err}")

except Exception as main_error:
    print(f"❌ خطأ عام: {main_error}")
finally:
    driver.quit()