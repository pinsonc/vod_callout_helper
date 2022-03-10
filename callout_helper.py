#!/usr/bin/env python3

import argparse
from io import StringIO
import os
import queue
import sounddevice as sd
import vosk
import sys
import tkinter as tk
from PIL import ImageTk, Image
import threading
import config

BUNGIE = config.bungie_callouts
CUSTOM = config.custom_callouts

class calloutsGUI(tk.Frame):

    def __init__(self, parent, topCall, midCall, botCall, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.root = parent
        self.topCall = topCall
        self.midCall = midCall
        self.botCall = botCall
        self.callset = "Default"
        self.stopThread=False
        self.build_gui()

    def build_gui(self):
        self.root.title('Callouts History')
        self.root.geometry('200x600')
        self.grid(column=1, row=3)
        image1 = ImageTk.PhotoImage(Image.open(self.topCall))
        label1 = tk.Label(image=image1)
        label1.photo = image1
        label1.grid(row=1, column=1)

        image2 = ImageTk.PhotoImage(Image.open(self.midCall))
        label2 = tk.Label(image=image2)
        label2.photo = image2
        label2.grid(row=2, column=1)

        image3 = ImageTk.PhotoImage(Image.open(self.botCall))
        label3 = tk.Label(image=image3)
        label3.photo = image3
        label3.grid(row=3, column=1)

        tk.Button(self.root, text="Clear", command=self.clear_gui).grid(row=4,column=1, sticky='w')
        tk.Button(self.root, text=self.callset, command=self.switch_callset).grid(row=4,column=1)
        tk.Button(self.root, text="Quit", command=self.close_gui).grid(row=4,column=1, sticky='e')

    def update_gui(self, filename):
        image1 = ImageTk.PhotoImage(Image.open(self.midCall))
        label1 = tk.Label(image=image1)
        label1.photo = image1
        label1.grid(row=1, column=1)
        self.topCall = self.midCall

        image2 = ImageTk.PhotoImage(Image.open(self.botCall))
        label2 = tk.Label(image=image2)
        label2.photo = image2
        label2.grid(row=2, column=1)
        self.midCall = self.botCall

        image3 = ImageTk.PhotoImage(Image.open(filename))
        label3 = tk.Label(image=image3)
        label3.photo = image3
        label3.grid(row=3, column=1)
        self.botCall = filename

    def switch_callset(self):
        self.callset = "Custom" if self.callset == "Default" else "Default"
        tk.Button(self.root, text=self.callset, command=self.switch_callset).grid(row=4,column=1)

    def close_gui(self):
        self.root.destroy()
        self.stopThread = True
    
    def clear_gui(self):
        image1 = ImageTk.PhotoImage(Image.open('img/blank.png'))
        label1 = tk.Label(image=image1)
        label1.photo = image1
        label1.grid(row=1, column=1)
        self.topCall = 'img/blank.png'

        image2 = ImageTk.PhotoImage(Image.open('img/blank.png'))
        label2 = tk.Label(image=image2)
        label2.photo = image2
        label2.grid(row=2, column=1)
        self.midCall = 'img/blank.png'

        image3 = ImageTk.PhotoImage(Image.open('img/blank.png'))
        label3 = tk.Label(image=image3)
        label3.photo = image3
        label3.grid(row=3, column=1)
        self.botCall = 'img/blank.png'
        

q = queue.Queue()

def int_or_str(text):
    """Helper function for argument parsing."""
    try:
        return int(text)
    except ValueError:
        return text

def callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    if status:
        print(status, file=sys.stderr)
    q.put(bytes(indata))

def parse_stream(mainGUI):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        '-l', '--list-devices', action='store_true',
        help='show list of audio devices and exit')
    args, remaining = parser.parse_known_args()
    if args.list_devices:
        print(sd.query_devices())
        parser.exit(0)
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[parser])
    parser.add_argument(
        '-f', '--filename', type=str, metavar='FILENAME',
        help='audio file to store recording to')
    parser.add_argument(
        '-m', '--model', type=str, metavar='MODEL_PATH',
        help='Path to the model')
    parser.add_argument(
        '-d', '--device', type=int_or_str,
        help='input device (numeric ID or substring)')
    parser.add_argument(
        '-r', '--samplerate', type=int, help='sampling rate')
    args = parser.parse_args(remaining)

    try:
        if args.model is None:
            args.model = "model"
        if not os.path.exists(args.model):
            print ("Please download a model for your language from https://alphacephei.com/vosk/models")
            print ("and unpack as 'model' in the current folder.")
            parser.exit(0)
        if args.samplerate is None:
            device_info = sd.query_devices(args.device, 'input')
            # soundfile expects an int, sounddevice provides a float:
            args.samplerate = int(device_info['default_samplerate'])

        model = vosk.Model(args.model)

        if args.filename:
            dump_fn = open(args.filename, "wb")
        else:
            dump_fn = None

        with sd.RawInputStream(samplerate=args.samplerate, blocksize = 8000, device=args.device, dtype='int16',
                                channels=1, callback=callback):
                print('#' * 80)
                print('Press Ctrl+C to stop the recording')
                print('#' * 80)

                rec = vosk.KaldiRecognizer(model, args.samplerate)
                while not mainGUI.stopThread:
                    data = q.get()
                    if rec.AcceptWaveform(data):
                        recog=rec.Result()
                        name = []
                        place = []
                        if mainGUI.callset == "Default":
                            for call in BUNGIE:
                                if call in recog:
                                    name.append(call)
                                    place.append(recog.find(call))
                        else:
                            for call in CUSTOM:
                                if call in recog:
                                    name.append(BUNGIE[CUSTOM.index(call)])
                                    place.append(recog.find(call))
                        if len(name) > 0:
                            place, name = zip(*sorted(zip(place, name)))
                            for entry in name:
                                mainGUI.update_gui("img/" + entry.replace(" ","_") + ".png")
                    else:
                        print(rec.PartialResult())
                    if dump_fn is not None:
                        dump_fn.write(data)

    except KeyboardInterrupt:
        print('\nDone')
        parser.exit(0)
    except Exception as e:
        parser.exit(type(e).__name__ + ': ' + str(e))

def main():
    root = tk.Tk()
    mainGUI = calloutsGUI(root, topCall='img/blank.png', midCall='img/blank.png', botCall='img/blank.png')

    t1 = threading.Thread(target=parse_stream, args=[mainGUI])
    t1.start()

    root.mainloop()
    t1.join()

main()