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

        # Создаем тестовые данные если база пустая
        if self.is_database_empty(cursor):
            self.create_test_data(cursor)
        
        # Создаем таблицу для статистики автопостов
        self.create_autopost_table(cursor)
        
        conn.commit()
        
    except Exception as e:
        finally:
            if 'conn' in locals():
                conn.close()
    
    def create_autopost_table(self, cursor):
        """Создание таблицы для статистики автопостов"""
        cursor.execute('''
CREATE TABLE IF NOT EXISTS autopost_statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_type TEXT NOT NULL,
    sent_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
        ''')
    
    def create_tables(self, cursor):