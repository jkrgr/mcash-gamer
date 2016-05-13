import random
import logging
import json
from time import sleep
from flask import Flask
from flask import request
import flask
from flask_sqlalchemy import SQLAlchemy
import mcash_merchant_api as mcash
import json



############################
###    Initialize app    ###


app = Flask(__name__)
app.debug = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://krgr:heiheihei@krgr.mysql.pythonanywhere-services.com/krgr$default'
db = SQLAlchemy(app)


# Games with price per hour in NOK:
games = [
    {'id': 'SCII',  'price': 10.00, 'name':'Starcraft II'},
    {'id': 'CSGO',  'price': 10.00, 'name':'Counter Strike: GO'},
    {'id': 'HS',    'price': 10.00, 'name':'Hearthstone'},
    {'id': 'LOL',   'price': 12.00, 'name':'League of Legends'},
    {'id': 'DOTA2', 'price': 15.00, 'name':'Dota 2'}
]



############################
###   Helper functions   ###


def get_game(id):
    for g in games:
        if g.get('id') == id:
            return g


def get_price(id):
    return get_game(id).get('price')

def get_game_server(game, pw, hours, players):
    # Add code for game server integration here! In the meanwhile, I'll
    # generate a random IP...
    return '.'.join('%s'%random.randint(0, 255) for i in range(4))


def generate_random_string(length=6):
    _int_b64_cs = '-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz'
    return ''.join(random.choice(_int_b64_cs) for _ in range(length))



############################
###       Models         ###


class Game(db.Model):
    def __init__(self, game, players, hours, pw):
        self.game = game
        self.players = players
        self.hours = hours
        self.pw = pw
        self.transactions = ''
        self.paid_by = ''
        self.total_amount = float(hours) * get_price(game)

    id = db.Column(db.String(16), primary_key=True, default=generate_random_string)
    game = db.Column(db.String(80))
    players = db.Column(db.Integer)
    hours = db.Column(db.Integer)
    pw = db.Column(db.String(80))
    total_amount = db.Column(db.Float, default=0.0)
    paid_amount = db.Column(db.Float, default=0.0)
    paid_by = db.Column(db.String(260), default='')
    transactions = db.Column(db.String(120), default='')
    ip = db.Column(db.String(16), default='')


class Shortlink(db.Model):
    def __init__(self, shortlink_id, callback_uri):
        self.shortlink_id = shortlink_id
        self.callback_uri = callback_uri
        id = db.Column(db.String(16), primary_key=True, default=generate_random_string)
    id = db.Column(db.Integer, primary_key=True)
    shortlink_id = db.Column(db.String(16))
    callback_uri = db.Column(db.String(64))
    is_active = db.Column(db.Boolean, default=True)


############################
###      Handlers        ###


@app.route('/', methods=['GET', 'POST'])
def main():
    if request.method == "POST":
        game = request.form.get('game')
        players = request.form.get('players')
        hours = int(request.form.get('hours'))
        pw  = request.form.get('pw')
        g = Game(game, players, hours, pw)

        db.session.add(g)
        db.session.commit()


        return flask.redirect(flask.url_for('game', game_id=g.id))
    return flask.render_template('index.html', games=games)


@app.route('/game/<game_id>', methods=['GET'])
def game(game_id):
    g = db.session.query(Game).get(game_id)
    if not g:
        return flask.redirect(flask.url_for('main'))

    if g.total_amount - g.paid_amount < 1:
        if not g.ip:
            ip = get_game_server(g.game, g.pw, g.hours, g.players)
            g.ip = ip
            db.session.add(g)
            db.session.commit()

    s = db.session.query(Shortlink).filter(Shortlink.is_active == True).first()
    return flask.render_template('game.html', game=g, shortlink=s)


@app.route('/game/<game_id>/status', methods=['GET'])
def game_status(game_id):
    g = db.session.query(Game).get(game_id)
    if not g:
        return ''

    status = 'ok' if g.total_amount - g.paid_amount < 1 else 'pending'
    return json.dumps({'status': status, 'paid_amount': g.paid_amount})

from flask import Response

@app.route('/scan_callback', methods=['POST'])
def scan_callback():

    logging.info('\n\n\n' + str(request.data))
    data = json.loads(request.data).get('object')
    token, game_id = data.get('id'), data.get('argstring')
    g = db.session.query(Game).get(game_id)

    if g.total_amount - g.paid_amount < 1:
        return Response('{"text":"Spillet er allerede betalt for!"}', mimetype='application/json')
    else:
        pos_tid = generate_random_string()

        res = mcash.create_payment_request(
            token,
            "%.2f" % (g.total_amount/g.players),
            "Leie av server for spill %s" % g.game,
            game_id,
            pos_tid
        )
        logging.error(res)
        logging.error(res.text)
    return ''


@app.route('/pay_callback', methods=['POST'])
def pay_callback():
    data = json.loads(request.data).get('object')
    logging.error(str(data))
    if data.get('status').lower() == 'auth':
        game_id = data.get('pos_id')
        tid = data.get('tid')
        g = db.session.query(Game).get(game_id)
        if g.transactions is None:
            g.transactions = ''
        if g.paid_by is None:
            g.paid_by = ''

        if tid not in g.transactions:
            name = data.get('permissions').get('user_info').get('name').split(',')[0]
            logging.error('\nname:')
            logging.error(name)
            g.paid_by += ", %s" % name
            g.paid_amount += float(data.get('amount'))
            g.transactions += ", %s" % data.get('tid')
            db.session.add(g)
            db.session.commit()
    else:
        pass
    return ''


@app.route('/get_shortlinks')
def get_shortlinks():
    ss = db.session.query(Shortlink).all()
    res = "<pre> id | shortlink_id | callback_uri | is_active\n\n" + '\n'.join(["%s | %s | %s | %s" % (s.id, s.shortlink_id, s.callback_uri, s.is_active) for s in ss]) + "</pre>"
    return res


@app.route('/create_shortlink')
def create_shortlink():
    """ You only need to call this once """
    current_callback_uri = flask.url_for('scan_callback', _external=True)
    shortlinks = db.session.query(Shortlink).filter(Shortlink.is_active == True)
    res = []
    for s in shortlinks:
        r = mcash.get_shortlink(s.shortlink_id)
        sid, uri = r.data.get('object').get('id'), r.data.get('object').get('callback_uri')
        if sid and uri:
            res.append("%s %s" % (sid, uri))
        else:
            s.is_active = False
            db.session.add(s)

    if res:
        format_string = "<pre>Scan callback uri for this instance: %s\n\nActive shortlinks:\n\n%s</pre>"
        return format_string % (current_callback_uri, '\n'.join(res))
    else:
        # No active shortlinks exist, create a new one (with up to five retries)
        for i in range(5):
            r = mcash.create_shortlink(current_callback_uri)
            if r.status_code/100 == 5:
                sleep(i+2)
                logging.error("Unable to create shortlink, got status code %s" % r.status_code)
            elif r.status_code/100 == 4:
                logging.error("Unable to create shortlink:\n%s" % r.json())
            else:
                d = r.json()
                s = Shortlink(d.get('id'), current_callback_uri)
                db.session.add(s)
                break

    db.session.commit()

    return str(s)


