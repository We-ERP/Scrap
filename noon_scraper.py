import requests
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials
import json
import os

# إعدادات اتصال جوجل شيت
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds_json = os.environ.get("GOOGLE_CREDENTIALS")
creds_dict = json.loads(creds_json)
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
client = gspread.authorize(creds)

# ربط الشيت والتاب المحددة
SPREADSHEET_URL = "لينك_شيت_جوجل_بتاعك_هنا"
spreadsheet = client.open_by_url(SPREADSHEET_URL)

# اختيار أو إنشاء تاب باسم noon_scraper
try:
    sheet = spreadsheet.worksheet("noon_scraper")
except gspread.exceptions.WorksheetNotFound:
    sheet = spreadsheet.add_worksheet(title="noon_scraper", rows="1000", cols="10")

# مسح القديم وكتابة العناوين الجديدة
sheet.clear()
sheet.append_row(["القسم", "اسم المنتج", "السعر (جنيه)", "رابط المنتج"])

# أقسام نون المستهدفة بناءً على طلبك
CATEGORIES = {
    "لوازم الجمال والبرفيوم": "https://www.noon.com/egypt-ar/beauty/",
    "لوازم البيت والأجهزة المنزلية": "https://www.noon.com/egypt-ar/home-and-kitchen/"
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7"
}

all_products = []

for category_name, url in CATEGORIES.items():
    print(f"جاري سحب قسم: {category_name}...")
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"فشل الاتصال بالقسم: {category_name}")
            continue

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # استخراج المنتجات بناءً على الـ data-qa الظاهر في كود نون
        products = soup.find_all('div', {'data-qa': 'plp-product-box'})
        if not products:
            # طريقة احتياطية لو الـ attribute اتغير
            products = soup.select('div[class*="productBox"]')

        print(f"تم العثور على {len(products)} منتج في {category_name}")

        for product in products:
            # اسم المنتج
            title_tag = product.find('h2', {'data-qa': 'plp-product-box-name'})
            if not title_tag:
                title_tag = product.find('h2')
            title = title_tag.text.strip() if title_tag else "بدون اسم"

            # السعر
            price_tag = product.find('div', {'data-qa': 'div-price-now'})
            if not price_tag:
                price_tag = product.find('span', class_=lambda x: x and 'priceNow' in x)
            price = price_tag.text.strip() if price_tag else "غير متوفر"

            # الرابط
            link_tag = product.find('a', href=True)
            if link_tag:
                link = "https://www.noon.com" + link_tag['href'] if not link_tag['href'].startswith('http') else link_tag['href']
            else:
                link = ""

            all_products.append([category_name, title, price, link])

    except Exception as e:
        print(f"حدث خطأ أثناء سحب {category_name}: {e}")

# رفع البيانات دفعة واحدة للشيت
if all_products:
    sheet.append_rows(all_products)
    print("تم تحديث شيت جوجل بنجاح لقسم نون! 🚀")
else:
    print("لم يتم العثور على منتجات لإضافتها.")