python3 -m piptools compile ./requirements.txt --output-file ./requirements_compiled.txt 
python3 -m pip install -r ./requirements_compiled.txt --platform win_amd64 --target ./3rdparty_windows --python-version 313 --no-compile --no-deps
python3 -m pip install -r ./requirements_compiled.txt --platform macosx_14_0_universal2 --target ./3rdparty_macos --python-version 313 --no-compile --no-deps
rm ./requirements_compiled.txt 
