[app]

# (str) Title of your application
title = Kindle Optimizer

# (str) Package name
package.name = kindleoptimizer

# (str) Package domain (needed for android/ios packaging)
package.domain = org.allenvillarinasoto

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (leave empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas

# (str) Application versioning (method 1)
version = 0.1

# (list) Application requirements
requirements = python3, kivy, pillow

# (list) Supported orientations
orientation = portrait

#
# Android specific
#

fullscreen = 0

# (list) Permissions
android.permissions = READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE

# (int) Target Android API
android.api = 33

# (int) Minimum API your APK / AAB will support.
android.minapi = 21

# (str) Android SDK Build-Tools version to use (Locks down to prevent missing license errors)
android.build_tools_version = 33.0.0

# (str) Android NDK version to use
android.ndk = 25b

# (int) Android NDK API to use.
android.ndk_api = 21

# (list) The Android archs to build for
android.archs = arm64-v8a, armeabi-v7a

android.allow_backup = True
android.debug_artifact = apk

#
# Python for android (p4a) specific
#

p4a.setup_py = false


[buildozer]
log_level = 2
warn_on_root = 1
