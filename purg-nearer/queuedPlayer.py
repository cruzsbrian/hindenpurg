#!/usr/bin/env python3

import os
import threading
import subprocess

import gi
gi.require_version('Gst', '1.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gst, Gtk, GObject

import youtube_dl


PREDOWNLOAD_BUFFER = 5


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
    def __init__(self, c, t, l, i):
        self.code = c
        self.title = t
        self.length = l
        self.id = i


class Downloader:
    def __init__(self, newSongCallback):
        self.downloadQueue = []
        self.downloadThread = threading.Thread(target=self.downloadAll)

        self.newSongCallback = newSongCallback

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

    def addSong(self, song):
        self.downloadQueue.append(song)

        if not self.downloadThread.isAlive():
            self.downloadThread = threading.Thread(target=self.downloadAll)
            self.downloadThread.start()

    def downloadAll(self):
        while len(self.downloadQueue) > 0:
            song = self.downloadQueue.pop()

            # set the right output filename
            self.ydlOpts['outtmpl'] = getSongPath(song)

            # make a downloader with those options
            ydl = youtube_dl.YoutubeDL(self.ydlOpts)

            ydl.download([song.code])

            self.newSongCallback()


class Player:
    def __init__(self):
        self.resetAudio()

        self.downloader = Downloader(self.newSongDownloaded)

        self.queue = []
        self.paused = False

        self.nextSongId = 0

    # everything involved with actually playing the audio
    def resetAudio(self):
        Gst.init(None)

        self.player = Gst.ElementFactory.make('playbin', 'player')
        self.player.connect('about-to-finish', self.next)

        self.audioThread = threading.Thread(target=Gtk.main)
        self.audioThread.start()

    def next(self, player=None):
        if len(self.queue) > 0:
            # delete old song
            subprocess.call(['rm', getSongPath(self.queue[0])])

            if len(self.queue) > PREDOWNLOAD_BUFFER:
                self.downloader.addSong(self.queue[PREDOWNLOAD_BUFFER].code)

            # remove song from queue
            self.queue.pop(0)

            # play next song
            if not self.paused:
                self.play()

        else:
            # for some reason if the songs ever stop the thing needs to be reset
            # before the next one
            self.resetAudio()

    def play(self):
        if len(self.queue) > 0:
            if songExists(self.queue[0]):
                uri = 'file://' + getSongPath(self.queue[0])
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

    def newSongDownloaded(self):
        if not self.paused:
            self.play()

    def addSong(self, code):
        # each downloaded file gets a unique id so that repeat songs work
        # there are PREDOWNLOAD_BUFFER files at a time, so we need
        # PREDOWNLOAD_BUFFER ids
        song_id = self.nextSongId

        self.nextSongId += 1
        if self.nextSongId == PREDOWNLOAD_BUFFER:
            self.nextSongId = 0

        # will become song = lookUpSong(code)
        song = Song(code, code, 0, song_id)

        if len(self.queue) < PREDOWNLOAD_BUFFER:
            self.downloader.addSong(song)

        self.queue.append(song)


def getSongPath(song):
    filename = 'tmp/' + str(song.code) + '-' + str(song.id) + '.mp3'
    return os.path.realpath(filename)

def songExists(song):
    return os.path.isfile(getSongPath(song))


if __name__ == '__main__':
    p = Player()

    while True:
        nextUrl = input('YouTube code: ')
        p.addSong(nextUrl)
