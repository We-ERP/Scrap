from selenium import webdriver
from selenium.webdriver.common.by import By
import pandas as pd
import time

print("🚀 جاري تشغيل متصفح Microsoft Edge الدولي الشامل...")
options = webdriver.EdgeOptions()
options.add_argument("--lang=ar-EG")
driver = webdriver.Edge(options=options)

all_scraped_data = []

try:
    # --- الخطوة 1: الدخول للصفحة الرئيسية وسحب جميع الأقسام ديناميكياً ---
    print("🏠 جاري فتح الصفحة الرئيسية للاستكشاف وسحب الأقسام...")
    driver.get("https://www.rayashop.com/ar/")
    time.sleep(6)
    
    # قراءة القائمة الرئيسية
    category_elements = driver.find_elements(By.CSS_SELECTOR, "ul.CategoryList li a")
    categories_map = {}
    
    for elem in category_elements:
        href = elem.get_attribute("href")
        name = elem.text.strip()
        if href and name and "/ar/" in href:
            categories_map[href] = name

    print(f"🎯 تم استكشاف {len(categories_map)} قسم رئيسي بنجاح.")

    # --- الخطوة 2: اللف على كل الأقسام وصفحاتها بالكامل دون حد أقصى ---
    for cat_url, cat_name in categories_map.items():
        print(f"\n📂 بدء سحب [ قسم: {cat_name} ]")
        
        page_num = 1
        seen_urls_in_this_category = set() # لحماية الكود من التكرار الدائري
        
        while True:
            page_url = f"{cat_url}?p={page_num}"
            print(f"   📄 جاري فحص الصفحة رقم ({page_num}) -> {page_url}")
            
            driver.get(page_url)
            time.sleep(5)
            
            # سكرول ذكي لضمان تحميل المنتجات والصور بالكامل
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            # العثور على كروت المنتجات <article>
            cards = driver.find_elements(By.TAG_NAME, "article")
            
            # شرط التوقف 1: لو الصفحة فاضية تماماً مفيهاش كروت
            if not cards:
                print(f"   ⏹️ وصلنا لنهاية صفحات قسم ({cat_name}).")
                break
                
            new_products_count = 0

            # اللف على كروت المنتجات في الصفحة الحالية
            for card in cards:
                try:
                    # 1. اسم المنتج والرابط
                    img_element = card.find_element(By.CLASS_NAME, "ProductCard__Thumb")
                    product_name = img_element.get_attribute("alt")
                    
                    link_element = card.find_element(By.TAG_NAME, "a")
                    product_link = link_element.get_attribute("href")
                    
                    # حماية ذكية: منع التكرار
                    if product_link in seen_urls_in_this_category:
                        continue
                        
                    # 🌟 استخراج اسم البراند ذكياً (أول كلمة من اسم المنتج)
                    brand_name = "N/A"
                    if product_name and product_name != "N/A":
                        brand_name = product_name.split()[0] # لقط أول كلمة مثل (SAMSUNG, Kenwood, كينوود)
                        
                    # 2. صائد السعر المطور
                    exact_price = "N/A"
                    try:
                        price_elem = card.find_element(By.CSS_SELECTOR, "span[class*='text-primary']")
                        exact_price = price_elem.text.strip()
                    except:
                        try:
                            details_text = card.find_element(By.CLASS_NAME, "ProductCard__Details").text.strip()
                            lines = [l.strip() for l in details_text.split('\n') if l.strip()]
                            for line in lines:
                                if "جنيه" in line or "EGP" in line or any(char.isdigit() for char in line):
                                    exact_price = line
                                    break
                        except:
                            exact_price = "N/A"

                    # 3. سحب لينكات الصور المتعددة
                    image_urls = []
                    try:
                        images = card.find_elements(By.TAG_NAME, "img")
                        for img in images:
                            src = img.get_attribute("src")
                            if src and "product" in src and src not in image_urls:
                                image_urls.append(src)
                    except:
                        pass

                    # بناء قاموس البيانات مع إضافة العمود الجديد "البراند"
                    product_data = {
                        "التصنيف الرئيسي للموقع": cat_name,
                        "البراند (الماركة)": brand_name,
                        "اسم المنتج": product_name,
                        "السعر بالظبط": exact_price,
                        "رابط المنتج": product_link
                    }
                    
                    # توزيع الصور في أعمدة منفصلة
                    for img_idx, img_url in enumerate(image_urls, 1):
                        product_data[f"صورة {img_idx}"] = img_url
                    
                    seen_urls_in_this_category.add(product_link)
                    all_scraped_data.append(product_data)
                    new_products_count += 1
                    
                except Exception:
                    continue
            
            print(f"   ✨ الصفحة ({page_num}) طلعت {len(cards)} منتج (منهم {new_products_count} جديد).")
            
            # شرط التوقف 2: لو القسم بدأ يكرر نفسه
            if new_products_count == 0:
                print(f"   ⏹️ تم استخراج جميع منتجات قسم ({cat_name}) بالكامل.")
                break
                
            page_num += 1

    # --- الخطوة 3: تصدير البيانات النهائية للشيت العملاق الجديد ---
    if all_scraped_data:
        df = pd.DataFrame(all_scraped_data)
        
        output_file = "Raya_Full_Store_With_Brands.xlsx"
        df.to_excel(output_file, index=False)
        
        print("\n=======================================================")
        print(" 🎉 مبروك يا فنان! تم تحديث السكريبت وإضافة البراند بنجاح ساحق 📊")
        print(f" 📦 إجمالي المنتجات المستخرجة: {len(all_scraped_data)}")
        print(f" 💾 الشيت الجديد جاهز على الديسكتوب باسم: {output_file}")
        print("=======================================================")
    else:
        print("\n❌ لم يتم تجميع أي بيانات، تأكد من استقرار الموقع والإنترنت.")

except Exception as main_error:
    print(f"❌ حدث خطأ عام في السكريبت: {main_error}")

finally:
    driver.quit()