from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import pandas as pd
import time
import requests

# رابط الـ Web App بتاعك
GOOGLE_WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzKWdWi9qc4e7I5xF8tvDciSZ4Fh1DygtOvRocRbwaFi19AJ3wXMKekrrDcSE4w2wCL/exec"

print("🚀 جاري تشغيل متصفح Chrome في الوضع الخفي الشامل...")
options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080") 
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
options.add_argument("--lang=ar-EG")

driver = webdriver.Chrome(options=options)
# وضع حد أقصى لتحميل أي صفحة (30 ثانية) عشان السكريبت ميهنجش ويقفل
driver.set_page_load_timeout(30)

all_scraped_data = []

try:
    print("🏠 جاري فتح الصفحة الرئيسية للاستكشاف وسحب الأقسام...")
    driver.get("https://www.rayashop.com/ar/")
    time.sleep(8) 
    
    category_elements = driver.find_elements(By.CSS_SELECTOR, "ul.CategoryList li a")
    categories_map = {}
    
    for elem in category_elements:
        href = elem.get_attribute("href")
        name = elem.text.strip()
        if href and name and "/ar/" in href:
            categories_map[href] = name

    print(f"🎯 تم استكشاف {len(categories_map)} قسم رئيسي بنجاح.")

    product_tasks = []
    
    for cat_url, cat_name in categories_map.items():
        print(f"\n📂 جاري تجميع روابط المنتجات من [ قسم: {cat_name} ]")
        page_num = 1
        seen_urls_in_category = set()
        
        while True:
            # التعديل الجذري هنا: رجعنا لـ p= بدل page= لأن ده اللي موقع راية بيفهمه وبيقلب بيه
            sep = "&" if "?" in cat_url else "?"
            page_url = f"{cat_url}{sep}p={page_num}"
            print(f"   📄 فحص صفحة الروابط رقم ({page_num}) -> {page_url}")
            
            try:
                driver.get(page_url)
                time.sleep(6) # وقت إضافي لضمان تحميل الصفحة
            except Exception:
                print("   ⚠️ الصفحة دي تقيلة جداً، هنتخطاها...")
                break 
            
            # سكرول متدرج قوي جداً لضمان ظهور كل الكروت المخفية
            last_height = driver.execute_script("return document.body.scrollHeight")
            for _ in range(15): 
                driver.execute_script("window.scrollBy(0, 700);")
                time.sleep(1.5)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    time.sleep(2) 
                    new_height = driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        break
                last_height = new_height
            
            cards = driver.find_elements(By.TAG_NAME, "article")
            if not cards:
                time.sleep(4)
                cards = driver.find_elements(By.TAG_NAME, "article")
                if not cards:
                    print(f"   ⏹️ لا توجد كروت روابط أخرى في هذا القسم.")
                    break
                
            new_links_found = 0
            for card in cards:
                try:
                    a_tags = card.find_elements(By.TAG_NAME, "a")
                    for a in a_tags:
                        p_link = a.get_attribute("href")
                        if p_link and "rayashop.com" in p_link and p_link not in seen_urls_in_category:
                            seen_urls_in_category.add(p_link)
                            product_tasks.append((p_link, cat_name))
                            new_links_found += 1
                            break # لقينا الرابط، انقل ع الكارت اللي بعده
                except:
                    continue
            
            print(f"   ✨ تم لقط {new_links_found} رابط منتج جديد من هذه الصفحة.")
            
            # لو ملقاش روابط جديدة، معناه وصلنا لنهاية الترقيم الفعلي
            if new_links_found == 0:
                print(f"   ⏹️ تم جمع كافة الروابط المتاحة لقسم ({cat_name}).")
                break
                
            page_num += 1

    print(f"\n🔥 إجمالي الروابط التي تم جمعها للموقع بالكامل: {len(product_tasks)} منتج.")

    # --- الخطوة 3: الدخول لصفحة كل منتج وسحب البيانات ---
    for index, (p_url, fallback_cat) in enumerate(product_tasks, 1):
        print(f"   🔄 جاري قشط المنتج رقم ({index}/{len(product_tasks)}) -> {p_url}")
        
        try:
            driver.get(p_url)
            time.sleep(3)
        except Exception as e:
            print(f"   ⚠️ تجاوزنا المنتج ده بسبب بطء التحميل: {p_url}")
            continue 
        
        try:
            try:
                full_product_name = driver.find_element(By.TAG_NAME, "h1").text.strip()
                if " - " in full_product_name:
                    name_parts = full_product_name.rsplit(" - ", 1)
                    product_name = name_parts[0].strip()
                    product_code = name_parts[1].strip()
                elif "-" in full_product_name:
                    name_parts = full_product_name.rsplit("-", 1)
                    product_name = name_parts[0].strip()
                    product_code = name_parts[1].strip()
                else:
                    product_name = full_product_name
                    product_code = "N/A"
            except:
                product_name = "N/A"
                product_code = "N/A"
                
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
                "كاتيجوري": product_category,
                "اسم المنتج": product_name,
                "كود المنتج": product_code,
                "اسم البراند": brand_name,
                "سعر المنتج": exact_price,
                "لينك المنتج": p_url
            }
            
            for img_idx, img_url in enumerate(image_urls, 1):
                product_data[f"صورة {img_idx}"] = img_url
                
            all_scraped_data.append(product_data)
            
        except Exception:
            continue

    # --- الخطوة 4: إرسال البيانات لجوجل شيت ---
    if all_scraped_data:
        df = pd.DataFrame(all_scraped_data)
        print("🌐 جاري نقل البيانات أوتوماتيكياً إلى Google Sheet عبر الـ Web App...")
        
        cleaned_data = df.fillna("").to_dict(orient="records")
        payload = {"products": cleaned_data}
        
        try:
            response = requests.post(GOOGLE_WEBAPP_URL, json=payload, timeout=180)
            if response.status_code in [200, 302]:
                print("✅ تم تحديث شيت جوجل السحابي بنجاح مذهل!")
            else:
                print(f"⚠️ الـ Web App رد بكود مختلف: {response.status_code} - رسالة السيرفر: {response.text}")
        except Exception as http_err:
            print(f"❌ حدث خطأ أثناء الاتصال بجوجل شيت: {http_err}")
    else:
        print("\n❌ لم يتم تجميع بيانات، يرجى مراجعة حجم الشاشة الكلي وعناصر الصفحة.")

except Exception as main_error:
    print(f"❌ حدث خطأ عام: {main_error}")

finally:
    driver.quit()