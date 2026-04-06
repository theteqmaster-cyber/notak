import os
from core.database import insert_file, get_connection
# try inserting
res = insert_file("test/notes11.md", "hash1", "course1", "Notes", "hello")
print("Insert file returned:", res)
