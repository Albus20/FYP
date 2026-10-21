"""Interactive Windows-friendly entry point. Key remains in process memory only."""
import getpass
from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parent
os.chdir(root)
print('HK/SG AI collection: 2015-2025. Resume by running this again.')
print('1 = journals first (fast); 2 = official conference catalogs; 3 = conference HK/SG matching (larger download); 4 = generate patent SQL; 5 = original broad AI sample')
print('API key input is hidden; paste it and press Enter. Logs are saved under logs/.')
choice=input('Choose 1/2/3/4/5 [1]: ').strip() or '1'
if choice=='4':
    sys.exit(subprocess.call([sys.executable,'patents.py']))
mode={'1':'journals','2':'catalog','3':'pool','5':'all-ai'}.get(choice)
if not mode:raise SystemExit('Invalid choice')
if mode!='catalog' and not os.getenv('OPENALEX_API_KEY'):
    print('Get your free key: https://openalex.org/settings/api')
    os.environ['OPENALEX_API_KEY']=getpass.getpass('Paste API key (hidden): ').strip()
if mode != 'catalog' and not os.getenv('OPENALEX_API_KEY'):
    raise SystemExit('API key is empty. Copy your key, paste it and press Enter.')
year = input('Trial year [2024]; enter all for 2015-2025: ').strip().lower() or '2024'
command = [sys.executable, '-u', 'collect.py', mode]
if year != 'all':
    if not year.isdigit() or not 2015 <= int(year) <= 2025:
        raise SystemExit('Choose a year from 2015 to 2025, or all.')
    command += ['--start', year, '--end', year]
(root / 'logs').mkdir(exist_ok=True)
log_path = root / 'logs' / (datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + mode + '.log')
print('Running', mode, year, '; log:', log_path, flush=True)
key = os.getenv('OPENALEX_API_KEY')
with log_path.open('w', encoding='utf-8') as log:
    log.write(f'Mode: {mode}; years: {year}; Python: {sys.version.split()[0]}\n')
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, encoding='utf-8', errors='replace', env=env) as process:
        try:
            for line in process.stdout:
                safe = line.replace(key, '[REDACTED]') if key else line
                print(safe, end='', flush=True)
                log.write(safe)
                log.flush()
            code = process.wait()
        except KeyboardInterrupt:
            process.wait()
            code = 130
print('Finished.' if code == 0 else 'Stopped. Send the log file for diagnosis; rerun to resume.')
sys.exit(code)
