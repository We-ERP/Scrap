from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import pandas as pd
import time
import requests

# رابط الـ Web App الخاص بك
GOOGLE_WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzKWdWi9qc4e7I5xF8tvDciSZ4Fh1DygtOvRocRbwaFi19AJ3wXMKekrrDcSE4w2wCL/exec"

print("🚀 جاري تشغيل متصفح Chrome في الوضع الخفي (Headless) على سيرفر جيت هب...")
options = Options()
options.add_argument("--headless=new") # تشغيل خفي بدون واجهة رسومية
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--lang=ar-EG") # تثبيت اللغة العربية
driver = webdriver.Chrome(options=options)

all_scraped_data = []

try:
    # --- الخطوة 1: الدخول للصفحة الرئيسية وسحب جميع الأقسام ديناميكياً ---
    print("🏠 جاري فتح الصفحة الرئيسية للاستكشاف وسحب الأقسام...")
    driver.get("https://www.rayashop.com/ar/")
    time.sleep(6)
    
    category_elements = driver.find_elements(By.CSS_SELECTOR, "ul.CategoryList li a")
    categories_map = {}
    
    for elem in category_elements:
        href = elem.get_attribute("href")
        name = elem.text.strip()
        if href and name and "/ar/" in href:
            categories_map[href] = name

    print(f"🎯 تم استكشاف {len(categories_map)} قسم رئيسي بنجاح.")

    # --- الخطوة 2: تجميع روابط جميع المنتجات من كل الصفحات أولاً ---
    product_tasks = []
    
    for cat_url, cat_name in categories_map.items():
        print(f"\n📂 جاري تجميع روابط المنتجات من [ قسم: {cat_name} ]")
        page_num = 1
        seen_urls_in_category = set()
        
        while True:
            page_url = f"{cat_url}?p={page_num}"
            print(f"   📄 فحص صفحة الروابط رقم ({page_num}) -> {page_url}")
            driver.get(page_url)
            time.sleep(4)
            
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)
            
            cards = driver.find_elements(By.TAG_NAME, "article")
            if not cards:
                print(f"   ⏹️ لا توجد صفحات روابط أخرى في هذا القسم.")
                break
                
            new_links_found = 0
            for card in cards:
                try:
                    link_elem = card.find_element(By.TAG_NAME, "a")
                    p_link = link_elem.get_attribute("href")
                    if p_link and p_link not in seen_urls_in_category:
                        seen_urls_in_category.add(p_link)
                        product_tasks.append((p_link, cat_name))
                        new_links_found += 1
                except:
                    continue
            
            print(f"   ✨ تم لقط {new_links_found} رابط منتج جديد من هذه الصفحة.")
            if new_links_found == 0:
                print(f"   ⏹️ تم جمع كافة الروابط المتاحة لقسم ({cat_name}).")
                break
                
            page_num += 1

    print(f"\n🔥 إجمالي الروابط التي تم جمعها للموقع بالكامل: {len(product_tasks)} منتج.")

    # --- الخطوة 3: الدخول لصفحة كل منتج وسحب البيانات العميقة بالملي ---
    for index, (p_url, fallback_cat) in enumerate(product_tasks, 1):
        print(f"   🔄 جاري قشط المنتج رقم ({index}/{len(product_tasks)}) -> {p_url}")
        driver.get(p_url)
        time.sleep(3.5)
        
        try:
            try:
                product_name = driver.find_element(By.TAG_NAME, "h1").text.strip()
            except:
                product_name = "N/A"
                
            try:
                brand_element = driver.find_element(By.CSS_SELECTOR, "a[href*='/ar/brands/']")
                brand_name = brand_element.text.strip()
            except:
                brand_name = "N/A"
                
            try:
                price_element = driver.find_element(By.CSS_SELECTOR, "span.text-primary-500.text-xl")
                exact_price = price_element.text.replace("جنيه", "").replace("EGP", "").strip()
            except:
                exact_price = "N/A"
                
            product_category = fallback_cat
            try:
                breadcrumbs = driver.find_elements(By.CSS_SELECTOR, "nav a, .breadcrumb a, div a[href*='/ar/']")
                cat_names = [c.text.strip() for c in breadcrumbs if c.text.strip() and c.text.strip() not in ["الرئيسية", "Home"]]
                if cat_names:
                    product_category = " > ".join(cat_names)
            except:
                pass

            image_urls = []
            try:
                img_tags = driver.find_elements(By.CSS_SELECTOR, ".swiper-slide img, .product-container img, img[class*='Product']")
                for img in img_tags:
                    src = img.get_attribute("src")
                    if src and "product" in src and src not in image_urls:
                        image_urls.append(src)
            except:
                pass

            product_data = {
                "تصنيف المنتج": product_category,
                "اسم براند المنتج": brand_name,
                "اسم المنتج": product_name,
                "السعر بالظبط": exact_price,
                "رابط المنتج": p_url
            }
            
            for img_idx, img_url in enumerate(image_urls, 1):
                product_data[f"صورة {img_idx}"] = img_url
                
            all_scraped_data.append(product_data)
            
        except Exception:
            continue

    # --- الخطوة 4: إرسال البيانات أوتوماتيكياً لجوجل شيت ---
    if all_scraped_data:
        df = pd.DataFrame(all_scraped_data)
        print("🌐 جاري نقل البيانات أوتوماتيكياً إلى Google Sheet عبر الـ Web App...")
        
        cleaned_data = df.fillna("").to_dict(orient="records")
        payload = {"products": cleaned_data}
        
        try:
            response = requests.post(GOOGLE_WEBAPP_URL, json=payload, timeout=90)
            if response.status_code == 200:
                print("✅ تم تحديث شيت جوجل السحابي بنجاح مذهل!")
            else:
                print(f"⚠️ الـ Web App رد بكود مختلف: {response.status_code}")
        except Exception as http_err:
            print(f"❌ حدث خطأ أثناء الاتصال بجوجل شيت: {http_err}")
    else:
        print("\n❌ لم يتم تجميع بيانات.")

except Exception as main_error:
    print(f"❌ حدث خطأ عام: {main_error}")

finally:
    driver.quit()