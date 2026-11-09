import re, shutil, os, sys
from datetime import datetime

f = 'bot.py'
if not os.path.exists(f):
    print('❌ bot.py not found'); sys.exit(1)

shutil.copy(f, f + '.bak_remove_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
src = open(f).read()
orig_len = len(src)

# ═══ 1. Remove the OLD corrupt /jiomass block ═══
# Look for the block starting with the old JIO_MASS_STATE comment
# and ending before the next major section (next @bot.on or /pool)
patterns = [
    # Old block: "# ▸ JIO MASS HITTER" through next "# ══" section
    r'\n# ═+\n#  ▸ JIO MASS HITTER.*?(?=\n# ═+\n#  ▸ (?!JIO MASS))',
    # Old JIO_MASS_STATE dict (only the state, not the whole block)
    r'\nJIO_MASS_STATE: dict = \{\}.*?(?=\n# ═+\n#  ▸ )',
]

removed = 0
for pat in patterns:
    new_src = re.sub(pat, '\n', src, flags=re.DOTALL)
    if new_src != src:
        removed += 1
        src = new_src
        print(f'   ✅ Removed block via pattern #{removed}')

# ═══ 2. Remove any dangling JIO_MASS_STATE / JIO_ACTIVE references ═══
for var in ['JIO_MASS_STATE', 'JIO_ACTIVE', 'JIO_MASS_WORKERS',
            '_jio_pick_proxy', '_jio_hit_once', '_jio_classify',
            '_jiomass_start', '_jiomass_worker', 'jiomass_cmd',
            'jiomass_file_handler', 'cb_jiomass_stop_extra',
            'cb_jiomass_pause_extra']:
    # remove function defs
    src = re.sub(rf'\n(async def {var}\(.*?\n(?=@bot\.on|\nasync def |\ndef |\n# ═))', '\n', src, flags=re.DOTALL)
    src = re.sub(rf'\ndef {var}\(.*?\n(?=@bot\.on|\nasync def |\ndef |\n# ═)', '\n', src, flags=re.DOTALL)

# ═══ 3. Remove orphan @bot.on blocks that reference removed handlers ═══
src = re.sub(
    r'\n@bot\.on\(events\.(?:NewMessage|CallbackQuery)\([^)]*jiomass[^)]*\)\)\s*\nasync def [^(]+\(event[^)]*\):\s*\n(?:    .*\n|\n)*?(?=@bot\.on|\n# ═|\Z)',
    '\n', src, flags=re.IGNORECASE
)

# ═══ 4. Fix any lines that reference JIO_MASS_STATE (safety) ═══
orphan_lines = []
new_lines = []
for i, line in enumerate(src.split('\n'), 1):
    if 'JIO_MASS_STATE' in line and 'def ' not in line and '=' not in line.split('#')[0]:
        # comment it out — safer than delete
        new_lines.append('# REMOVED: ' + line)
        orphan_lines.append(i)
    else:
        new_lines.append(line)
src = '\n'.join(new_lines)

open(f, 'w').write(src)
print(f'✅ Cleaned bot.py (removed {removed} blocks, {len(orphan_lines)} orphan lines)')
print(f'   Size: {orig_len} → {len(src)} bytes')
print(f'   Syntax:')
