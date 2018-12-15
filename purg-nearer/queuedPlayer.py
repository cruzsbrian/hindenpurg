#!/usr/bin/env python3

import os
import threading
import subprocess

import gi
gi.require_version('Gst', '1.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gst, Gtk, GObject

import youtube_dl


# intercepts the logs from youtube_dl, only lets warning and error through
class DownloadLogCatcher:
    def debug(self, msg):
        pass

    def warning(self, msg):
        print(msg)

    def error(self, msg):
        print(msg)


# data structure for song queue
class Song:
    def __init__(c, t, l):
        self.code = c
        self.title = t
        self.length = l


# handles playing the songs in the right order and automatically progressing
# from one to the next
class Player():
    def __init__(self):
        self.songId = 0
        self.resetAudio()

        self.queue = []
        self.paused = False

    # everything involved with actually playing the audio
    def resetAudio(self):
        Gst.init(None)

        self.player = Gst.ElementFactory.make('playbin', 'player')
        self.player.connect('about-to-finish', self.next)

        self.audioThread = threading.Thread(target=Gtk.main)
        self.audioThread.start()

    # advance to next song. player argument is passed by gst in the callback
    def next(self, player=None):
        if self.getSongPath():
            # delete old song
            subprocess.call(['rm', 'tmp/' + str(self.songId) + '.mp3'])

            self.songId += 1

            if not self.paused:
                self.play()
        else:
            # for some reason if the songs ever stop the thing needs to be reset
            # before the next one
            self.resetAudio()

    # updates the uri of the player to the current song (does not advance the
    # song)
    def play(self):
        songPath = self.getSongPath()

        if songPath:
            uri = 'file://' + songPath
            self.player.set_property('uri', uri)
            self.player.set_state(Gst.State.PLAYING)

        self.paused = False

    def skip(self):
        # setting to NULL before setting back to playing will make it go to the
        # next song. Otherwise it just keeps playing the current song
        self.player.set_state(Gst.State.NULL)
        self.next()

    def pause(self):
        self.player.set_state(Gst.State.PAUSED)
        self.paused = True

    # returns the full path of the current song, None if it doesn't exist
    def getSongPath(self):
        filename = 'tmp/' + str(self.songId) + '.mp3'
        if os.path.isfile(filename):
            return os.path.realpath(filename)


# handles downloading and playing songs
class DownloadPlayer:
    def __init__(self):
        self.songId = 0
        self.downloadQueue = []

        # options for youtube downloader
        self.ydlOpts = {
            'format': 'bestaudio/best',
            'logger': DownloadLogCatcher(),     # so debug msgs aren't printed
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
        }

        self.downloadThread = threading.Thread(target=self.downloadAll)

        self.player = Player()

    def addSong(self, url):
        self.downloadQueue.append(url)

        # make a new downloadThread if the old one finished
        if not self.downloadThread.isAlive():
            self.downloadThread = threading.Thread(target=self.downloadAll)
            self.downloadThread.start()

    def skip(self):
        self.player.skip()

    def pause(self):
        self.player.pause()

    def play(self):
        self.player.play()

    def isPaused(self):
        return self.player.paused

    def getQueue(self):
        return self.player.queue

    def downloadAll(self):
        while len(self.downloadQueue) > 0:
            # set the right output filename
            self.ydlOpts['outtmpl'] = 'tmp/' + str(self.songId) + '.mp3'
            self.songId += 1

            # make a downloader with those options
            ydl = youtube_dl.YoutubeDL(self.ydlOpts)

            url = self.downloadQueue.pop()
            ydl.download([url])

            # start the player in case it had run out of songs
            if not self.player.paused:
                self.player.play()


if __name__ == '__main__':
    d = DownloadPlayer()

    while True:
        nextUrl = input('YouTube url: ')
        d.addSong(nextUrl)
