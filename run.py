"""
Startscript: pytest zuerst, dann Streamlit.
Ausführen: python run.py
"""
import subprocess
import sys

print("=" * 60)
print("PSV App — Startup Check")
print("=" * 60)

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short", "-m", "not slow"],
)

if result.returncode != 0:
    print("\n❌ Tests fehlgeschlagen — App wird nicht gestartet.")
    print("   Fehler oben beheben, dann nochmal: python run.py")
    sys.exit(1)

print("\n✅ Alle Tests OK — starte App...\n")
print("=" * 60)

subprocess.run(
    [sys.executable, "-m", "streamlit", "run", "app.py",
     "--logger.level=debug"],
)
