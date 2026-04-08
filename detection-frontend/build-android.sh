#!/bin/bash

echo "=============================="
echo "Building React App"
echo "=============================="

npm run build

echo "=============================="
echo "Copying to Android"
echo "=============================="

npx cap copy android

echo "=============================="
echo "Building Android APK (Debug)"
echo "=============================="

cd android || exit

chmod +x gradlew
./gradlew assembleDebug

echo "=============================="
echo "Copying APK to Project Root"
echo "=============================="

cd ..

cp android/app/build/outputs/apk/debug/app-debug.apk ./app-debug.apk

echo "=============================="
echo "Build Completed"
echo "APK Location: ./app-debug.apk"
echo "=============================="