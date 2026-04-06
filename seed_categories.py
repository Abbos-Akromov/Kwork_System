import os
import sys
import django

sys.path.append(r'd:\Kwork')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from Client.models import Category
from django.utils.text import slugify

print("Kategoriyalarni tekshirmoqdamiz...")

default_categories = [
    {'name': 'Web Dasturlash', 'icon': 'fa-code'},
    {'name': 'Grafik Dizayn', 'icon': 'fa-pen-nib'},
    {'name': 'SEO & Marketing', 'icon': 'fa-bullhorn'},
    {'name': 'Tarjimonlik', 'icon': 'fa-language'},
    {'name': 'Video & Animatsiya', 'icon': 'fa-video'},
    {'name': 'Ma\'lumotlar Bazasi', 'icon': 'fa-database'},
    {'name': 'Mobil Dasturlash', 'icon': 'fa-mobile-screen'},
    {'name': 'Bot Yaratish', 'icon': 'fa-robot'},
]

count = 0
for cat in default_categories:
    obj, created = Category.objects.get_or_create(
        name=cat['name'],
        defaults={
            'slug': slugify(cat['name']),
            'icon': cat['icon'],
            'is_active': True,
            'description': f"{cat['name']} yo'nalishidagi mutaxassislar xizmatlari"
        }
    )
    if created:
        count += 1
        print(f"Baza qaydiga qo'shildi: {obj.name}")

if count > 0:
    print(f"Muaffaqiyatli! {count} ta yangi kategoriya yaratildi.")
else:
    print("Katalogda allaqachon kategoriyalar bor, ulardan foydalaniladi.")

print("Hammasi tayyor!")
