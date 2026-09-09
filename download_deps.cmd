python -m piptools compile ./requirements.txt --output-file ./requirements_compiled.txt

python -m pip install -r ./requirements_compiled.txt --target ./3rdparty_windows --implementation cp --python-version 313 --abi cp313 --platform win_amd64 --only-binary=:all: --no-compile --no-deps

python -m pip install -r ./requirements_compiled.txt --target ./3rdparty_macos_x86_64 --implementation cp --python-version 313 --abi cp313 --platform macosx_10_13_x86_64 --only-binary=:all: --no-compile --no-deps
python -m pip install "psutil>=5.6.6" --target ./3rdparty_macos_x86_64 --implementation cp --python-version 313 --abi cp313 --platform macosx_10_13_x86_64 --only-binary=:all: --no-compile --no-deps

python -m pip install -r ./requirements_compiled.txt --target ./3rdparty_macos_arm64 --implementation cp --python-version 313 --abi cp313 --platform macosx_11_0_arm64 --only-binary=:all: --no-compile --no-deps
python -m pip install "psutil>=5.6.6" --target ./3rdparty_macos_arm64 --implementation cp --python-version 313 --abi cp313 --platform macosx_11_0_arm64 --only-binary=:all: --no-compile --no-deps

del requirements_compiled.txt
