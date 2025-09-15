@@ .. @@
         # Товары
         cursor.execute('''
 CREATE TABLE IF NOT EXISTS products (
     id INTEGER PRIMARY KEY AUTOINCREMENT,
     name TEXT NOT NULL,
     description TEXT,
     price REAL NOT NULL,
     category_id INTEGER,
     subcategory_id INTEGER,
     brand TEXT,
     image_url TEXT,
     stock INTEGER DEFAULT 0,
     views INTEGER DEFAULT 0,
     sales_count INTEGER DEFAULT 0,
     is_active INTEGER DEFAULT 1,
     cost_price REAL DEFAULT 0,
     original_price REAL,
     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
     FOREIGN KEY (category_id) REFERENCES categories (id),
     FOREIGN KEY (subcategory_id) REFERENCES subcategories (id)
 )
         ''')