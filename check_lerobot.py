# check_lerobot.py
import lerobot
print("version:", getattr(lerobot, "__version__", "unknown"))
print("path:", lerobot.__file__)

import pkgutil, lerobot
print("\n--- top-level submodules ---")
for m in pkgutil.iter_modules(lerobot.__path__):
    print(m.name)