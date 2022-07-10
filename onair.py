import configparser
import glob
import ruamel.yaml as yaml
import urllib.request as urllib2
import re
import time
import os
import argparse
from io import BytesIO
import requests
from pydub import AudioSegment
from pydub.silence import detect_silence, detect_nonsilent
from pydub.utils import which

AudioSegment.converter = which("ffmpeg")

# parse commandline args
parser = argparse.ArgumentParser()
parser.add_argument('-o', '--only', nargs='+', help='only check these stations', default=[])
parser.add_argument('-e', '--exclude', nargs='+', help='exclude these stations', default=[])
parser.add_argument('-s', '--check-silence', action='store_true', help='check for silence')
args = parser.parse_args()


if args.check_silence:
    testmode = "silence"
else:
    testmode = "stream"


config = configparser.ConfigParser()
config.read(glob.glob(os.path.dirname(os.path.abspath(__file__)) + '/config.ini'))

stations = glob.glob(config['DEFAULT']['stations_dir'] + "/*.md")

if len(args.only) > 0:
    stations = [station for station in stations if os.path.basename(station).split('.')[0] in args.only]
if len(args.exclude) > 0:
    stations = [station for station in stations if os.path.basename(station).split('.')[0] not in args.exclude]

def onair(url, mode="stream"):
    if mode=="stream":
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
    elif mode=="silence":
        if onair(url,mode="stream"):
            # record from stream and check for silence

            starttime = time.time()
            recording = BytesIO()

            audio_source = 'https://fm.chunt.org/stream'
            sound = ''

            r = requests.get(url, stream=True)

            # record from stream
            for block in r.iter_content(1024):
                recording.write(block)
                if time.time() > (starttime + 1):
                    recording.seek(0)
                    break

            try:
                sound = AudioSegment.from_file(recording, "mp3")
            except:
                try:
                    sound = AudioSegment.from_file(recording, format="mp4")
                except:
                    sound = AudioSegment.from_file(recording)

            silence_check = detect_silence(sound, min_silence_len=900, silence_thresh=-30)

            silence_list = [len(range(silence[0], silence[1])) > 900 for silence in silence_check]

            # if all detected silences ar elonger than 900 miliseconds
            if len(silence_list) > 0 and all(silence_list):
                return False
            else:
                return True
        else:
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
