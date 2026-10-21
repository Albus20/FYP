"""Interactive Windows-friendly entry point. Key remains in process memory only."""
import getpass
import os
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parent
os.chdir(root)
print('HK/SG AI collection: 2015-2025. Resume by running this again.')
print('1 = journals first (fast); 2 = official conference catalogs; 3 = conference HK/SG matching (larger download); 4 = generate patent SQL; 5 = original broad AI sample')
choice=input('Choose 1/2/3/4/5 [1]: ').strip() or '1'
if choice=='4':
    sys.exit(subprocess.call([sys.executable,'patents.py']))
mode={'1':'journals','2':'catalog','3':'pool','5':'all-ai'}.get(choice)
if not mode:raise SystemExit('Invalid choice')
if mode!='catalog' and not os.getenv('OPENALEX_API_KEY'):
    print('Get your free key: https://openalex.org/settings/api')
    os.environ['OPENALEX_API_KEY']=getpass.getpass('Paste API key (hidden): ').strip()
sys.exit(subprocess.call([sys.executable,'collect.py',mode]))
