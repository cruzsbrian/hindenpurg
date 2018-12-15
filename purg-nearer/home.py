#!/usr/bin/env python3

from flask import (
        Blueprint, flash, g, redirect, render_template, request, url_for
        )
from werkzeug.exceptions import abort

from . import queuedPlayer

bp = Blueprint('home', __name__)

player = queuedPlayer.Player()

@bp.route('/', methods=('GET', 'POST'))
def index():
    if request.method == 'POST':
        new_url = request.form['url']

        print(new_url)
        player.addSong(new_url)

        # post-redirect-get
        return redirect(url_for('home.index'))

    return render_template('index.html',
            paused=player.paused, queue=player.queue)

@bp.route('/pause', methods=('GET', 'POST'))
def pause():
    if request.method == 'POST':
        print('pause')
        player.pause()

    return redirect(url_for('home.index'))

@bp.route('/play', methods=('GET', 'POST'))
def play():
    if request.method == 'POST':
        print('play')
        player.play()

    return redirect(url_for('home.index'))

@bp.route('/skip', methods=('GET', 'POST'))
def skip():
    if request.method == 'POST':
        print('skip')
        player.skip()

    return redirect(url_for('home.index'))
