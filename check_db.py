with open('core/database.py', 'r') as f:
    for line in f:
        if 'def insert_file' in line:
            break
    print(line.strip())
    for _ in range(20):
        print(next(f).strip())
