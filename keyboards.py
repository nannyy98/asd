@@ .. @@
 def create_main_keyboard():
     """Главная клавиатура"""
     return {
         'keyboard': [
             ['🛍 Каталог', '🛒 Корзина'],
             ['📋 Мои заказы', '👤 Профиль'],
             ['🔍 Поиск', 'ℹ️ Помощь'],
            ['🔙 Назад'],
            ['🏠 Главная']
         ],
         'resize_keyboard': True,
         'one_time_keyboard': False
     }
 
 def create_categories_keyboard(categories):
     """Клавиатура с категориями"""
     keyboard = []
     
    try:
        for i in range(0, len(categories), 2):
            row = []
            # Первая категория в ряду
            emoji = categories[i][3] if len(categories[i]) > 3 and categories[i][3] else '📦'
            name = categories[i][1] if len(categories[i]) > 1 else 'Категория'
            row.append(f"{emoji} {name}")
            
            # Вторая категория в ряду (если есть)
            if i + 1 < len(categories):
                emoji2 = categories[i + 1][3] if len(categories[i + 1]) > 3 and categories[i + 1][3] else '📦'
                name2 = categories[i + 1][1] if len(categories[i + 1]) > 1 else 'Категория'
                row.append(f"{emoji2} {name2}")
            
            keyboard.append(row)
    except Exception as e:
        print(f"DEBUG: Ошибка создания клавиатуры категорий: {e}")
        # Создаем простую клавиатуру
        for category in categories:
            try:
                name = category[1] if len(category) > 1 else 'Категория'
                keyboard.append([f"📦 {name}"])
            except:
                continue
     
-    keyboard.append(['🔙 Главная'])
+    keyboard.append(['🏠 Главная'])
     
     return {
         'keyboard': keyboard,
         'resize_keyboard': True,
         'one_time_keyboard': False
     }
 
 def create_subcategories_keyboard(subcategories):
     """Клавиатура с подкатегориями/брендами"""
     keyboard = []
     
    try:
        for i in range(0, len(subcategories), 2):
            row = []
            # Первая подкатегория в ряду
            emoji = subcategories[i][2] if len(subcategories[i]) > 2 and subcategories[i][2] else '🏷'
            name = subcategories[i][1] if len(subcategories[i]) > 1 else 'Подкатегория'
            row.append(f"{emoji} {name}")
            
            # Вторая подкатегория в ряду (если есть)
            if i + 1 < len(subcategories):
                emoji2 = subcategories[i + 1][2] if len(subcategories[i + 1]) > 2 and subcategories[i + 1][2] else '🏷'
                name2 = subcategories[i + 1][1] if len(subcategories[i + 1]) > 1 else 'Подкатегория'
                row.append(f"{emoji2} {name2}")
            
            keyboard.append(row)
    except Exception as e:
        print(f"DEBUG: Ошибка создания клавиатуры подкатегорий: {e}")
        # Создаем простую клавиатуру
        for subcategory in subcategories:
            try:
                name = subcategory[1] if len(subcategory) > 1 else 'Подкатегория'
                keyboard.append([f"🏷 {name}"])
            except:
                continue
     
-    keyboard.append(['🔙 К категориям', '🏠 Главная'])
+    keyboard.append(['🔙 Назад', '🏠 Главная'])
     
     return {
         'keyboard': keyboard,
         'resize_keyboard': True,
         'one_time_keyboard': False
     }
 def create_products_keyboard(products, show_back=True):
     """Клавиатура с товарами"""
     keyboard = []
     
     for product in products:
         keyboard.append([f"🛍 {product[1]} - ${product[3]:.2f}"])
     
     if show_back:
-        keyboard.append(['🔙 К категориям', '🏠 Главная'])
+        keyboard.append(['🔙 Назад', '🏠 Главная'])
     else:
         keyboard.append(['🏠 Главная'])
     
     return {
         'keyboard': keyboard,
         'resize_keyboard': True,
         'one_time_keyboard': False
     }