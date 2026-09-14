set -e
SDK=/opt/apps/picobusinesssuite/SDK/clientso/64
mkdir -p $SDK
cp /stub/PXREARobotSDK.h $SDK/
g++ -std=c++17 -fPIC -shared -I$SDK /stub/pxrea_stub.cpp -o $SDK/libPXREARobotSDK.so -pthread
ls -l $SDK
