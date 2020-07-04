python -m piptools compile ./requirements.txt --output-file ./requirements_compiled.txt 
python -m pip install -r ./requirements_compiled.txt --platform win32 --target ./3rdparty_windows --python-version 37 --no-compile --no-deps
python -m pip install -r ./requirements_compiled.txt --platform macosx_10_13_x86_64 --target ./3rdparty_macos --python-version 37 --no-compile --no-deps
del requirements_compiled.txt 
