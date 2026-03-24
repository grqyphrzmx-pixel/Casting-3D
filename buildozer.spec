[app]
title = 2D3D铸造模型
package.name = casting3dapp
package.domain = org.yourname
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.1
# 只保留最基础的依赖，先跑通
requirements = python3,kivy==2.2.0
orientation = portrait

[app:source.exclude_dirs]
__pycache__
build
dist

[osx]
python_version = 3
kivy_version = 2.2.0

[android]
api = 31
ndk = 25b
archs = arm64-v8a
accept_sdk_license = True
permissions = READ_EXTERNAL_STORAGE
warn_on_unsupported_platform = False
copy_libs = 1

[buildozer]
log_level = 2
warn_on_root = 1
