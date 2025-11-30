import os
import sys

def clean_null_bytes(filepath):
    with open(filepath, 'rb') as f:
        content = f.read()
    cleaned = content.replace(b'\0', b'')
    with open(filepath, 'wb') as f:
        f.write(cleaned)

if __name__ == '__main__':
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                clean_null_bytes(filepath)
                print(f"Cleaned {filepath}")