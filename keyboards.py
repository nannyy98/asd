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
     
     for i in range(0, len(categories), 2):
         row = [f"{categories[i][3]} {categories[i][1]}"]
         if i + 1 < len(categories):
             row.append(f"{categories[i + 1][3]} {categories[i + 1][1]}")
         keyboard.append(row)
     
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
     
     for i in range(0, len(subcategories), 2):
         row = [f"{subcategories[i][2]} {subcategories[i][1]}"]
         if i + 1 < len(subcategories):
             row.append(f"{subcategories[i + 1][2]} {subcategories[i + 1][1]}")
         keyboard.append(row)
     
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