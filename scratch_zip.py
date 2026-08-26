import zipfile
import os

def zipdir(path, ziph):
    for root, dirs, files in os.walk(path):
        if 'venv' in root or '.git' in root or '__pycache__' in root:
            continue
        for file in files:
            if file.endswith('.pyc'):
                continue
            ziph.write(os.path.join(root, file), 
                       os.path.relpath(os.path.join(root, file), 
                                       os.path.join(path, '..')))

if __name__ == '__main__':
    zipf = zipfile.ZipFile('C:/Users/njoku/low_mc_sniper_bot_export.zip', 'w', zipfile.ZIP_DEFLATED)
    zipdir('.', zipf)
    zipf.close()
    print("Done")
