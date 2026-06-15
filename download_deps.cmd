python -m piptools compile ./requirements.txt --output-file ./requirements_compiled.txt 
python -m pip install -r ./requirements_compiled.txt --platform win_amd64 --target ./3rdparty_windows --python-version 313 --no-compile --no-deps
python -m pip install -r ./requirements_compiled.txt --platform macosx_14_0_universal2 --target ./3rdparty_macos --python-version 313 --no-compile --no-deps
del requirements_compiled.txt 
