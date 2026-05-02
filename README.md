## Install Gdal
```bash
sudo apt-get update
sudo apt-get install mesa-utils
sudo apt-get install libegl-mesa0
sudo apt-get install libasound2t64
sudo apt-get install gdal-bin libgdal-dev
```

## Install Requirements For Linux
```bash
pip isntall -r final-require.txt
```

## Build Docker
```bash
sudo docker build -t aqua .
sudo docker run --name aqua_container -p 8000:8000 aqua
```

## Run the server 
```bash
python3 manage.py runserver 0.0.0.0:8000
```
# Install card for telegram
 pip install playwright 
 playwright install chromium
