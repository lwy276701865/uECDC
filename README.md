We implemented in Python and c++ a **unbalanced Efficient Collaborative Data Cleaning (uECDC)** protocol, a functionality that allows two parties to *filter out badly classified,misclassified data* . In our setup, these parties are:
​
* a *server* having a large database
* a *client* who would like to *privately* query the database.
​
## How to run
Our implemention is based on [PSI](https://github.com/bit-ml/Private-Set-Intersection) and [OKVS](https://github.com/ShallMate/OKVS),which is extracted from [VOLE-PSI](https://github.com/Visa-Research/volepsi).This project only supports Linux systems.<br>
You should make sure that your cmake and gcc versions support the C++20 standard.Our benchmark machine have cmake 3.27.0 and gcc 11.4.0<br>
 Below is a demonstration of how to run this project on Ubuntu systems.
### 1. Install Python library
```shell
pip install -r requirements.txt
```
### 2. Build and Install libOTe
```shell
git clone https://github.com/ridiculousfish/libdivide.git
cd libdivide
cmake .
make -j
sudo make install
git clone --recursive https://github.com/osu-crypto/libOTe.git
cd libOTE
mkdir -p out/build/linux
cmake -S . -B out/build/linux -DCMAKE_BUILD_TYPE=Release -DFETCH_AUTO=ON -DENABLE_RELIC=ON -DENABLE_ALL_OT=ON -DCOPROTO_ENABLE_BOOST=ON -DENABLE_SILENT_VOLE=ON -DENABLE_SSE=ON -DENABLE_PIC=ON
cmake --build out/build/linux 
su (enter your password)
cmake --install out/build/linux 
```
### 3. Compile rrokvs into a dynamic library
```shell
cd rrokvs
cmake -B build -S . -Dpybind11_DIR="path to your python dist-packages"/pybind11/share/cmake/pybind11
cmake --build build
sudo cp ./rrokvs.cpython-38-x86_64-linux-gnu.so "path to your python dist-packages"
```
### 4. Run Project
```shell
python3 set_gen.py
python3 server_offline.py
python3 server_online.py
python3 client_online.py
```
### 5.Example of running results
Here is a screenshot showing the running results of the project.
<br>
![](/picture/server_offline.png "server_offline")
<br>
![](/picture/server_online.png "server_online")
<br>
![](/picture/client_online.png "client_online")