@@ .. @@
 import signal
 import sys
 import threading
+from datetime import datetime
 from database import DatabaseManager
 from handlers import MessageHandler
 from notifications import NotificationManager