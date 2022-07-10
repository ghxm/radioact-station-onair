import configparser
import glob
import ruamel.yaml as yaml
import urllib.request as urllib2
import re
import time
import os

config = configparser.ConfigParser()
config.read(glob.glob(os.path.dirname(os.path.abspath(__file__)) + '/config.ini'))

stations = glob.glob(config['DEFAULT']['stations_dir'] + "/*.md")

def onair(url, mode="code"):
    if mode=="code":
        try:
            req = urllib2.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            conn = urllib2.urlopen(req)
            try:
                conn.close()
            except:
                pass
            return True
        except:
            return False

def add_to_list(list, index, val):
    try:
        list[index] = val
    except:
        list.append(val)
    return(list)

for station in stations:
    print(time.time())
    print('File: ' + station)
    with open(station, "r+", encoding="utf8") as f:

        file_string = f.read()
        yaml_string = re.search(r'^stream_url:(?:.)+?\n(?=^[a-z])', file_string, flags=re.DOTALL|re.MULTILINE)

        if yaml_string is None:
            continue
        else:
            yaml_string = yaml_string[0]
        data = yaml.safe_load(yaml_string)

        if 'stream_url' in data.keys() and data.get('stream_url') is not None:
            for i, stream in enumerate(data['stream_url']):
                if onair(stream[1], mode = testmode):
                    list = add_to_list(stream, 2, 'online')
                else:
                    list = add_to_list(stream, 2, 'offline')
                data['stream_url'][i] = stream
            yaml_string_updated = yaml.safe_dump(data, allow_unicode=True)

        file_string = file_string.replace(yaml_string, yaml_string_updated)

    with open(station, "w", encoding="utf8") as f:

        f.write(file_string)

    time.sleep(config['DEFAULT'].getint('wait_between'))
