import os
import sys
import subprocess
import json
import random
import operator
import logging
import requests
import indicoio
from chatterbot import ChatBot

from uuid import uuid4
from binascii import a2b_base64
from clarifai.client import ClarifaiApi
from flask import (Flask, render_template, request, redirect, session, Response,
                   url_for, flash, get_flashed_messages, g)

from config import config
from models.d3_injectors import generate_emotion_data, pretty_print

app = Flask(__name__)
app.secret_key = config['APP_SECRET_KEY']
app.config['SECRET_KEY'] = config['APP_SECRET_KEY']
SECRET_KEY = config['APP_SECRET_KEY']

# So it logs Flask errors to stdout - nice for Heroku logs and CI if used
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.ERROR)

# Indico set-up
indicoio.config.api_key = config['INDICO_KEY']

# Clarifai set-up
os.environ['CLARIFAI_APP_ID'] = config['CLARIFAI_ID']
os.environ['CLARIFAI_APP_SECRET'] = config['CLARIFAI_SECRET']

@app.before_first_request
def setup_session_dicts():
    """An untrained instance of ChatterBot starts off with no knowledge of how to communicate.
    Each time a user enters a statement, the library saves the text that they entered and the
    text that the statement was in response to. As ChatterBot receives more input the number
    of responses that it can reply and the accuracy of each response in relation to the input
    statement increase. The program selects the closest matching response by searching for the
    closest matching known statement that matches the input, it then returns the most likely
    response to that statement based on how frequently each response is issued by the people
    the bot communicates with.
    """
    session['msft'] = {}
    session['indico'] = {}
    session['clarifai'] = []
    session['uuid'] = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/img_handler', methods=['POST'])
def img_handler():
    """
    - Grabs the binary data from the WebRTC still grab attached to POST
    - WebRTC is intuitive--unicode or ASCII byte-encodings not-so-much.
      Manipulates the unicode that Python gets from the POST request form dictionary
      and turns it into the appropriate ASCII byte-encoding, which is then base-64-decoded,
      and then piped into a random UUID-named .png file.
    - As a hack, I used sshfs to mount the public_html directory of my UT Austin CS account address
      into my working dir, and sent the new .png files into that folder, chmodding per upload.
    - This renders the image into a resource that's easily accessible by APIs.
      (Although this obviously won't scale, I only have 2 GB as an undergrad.)
    - Finally, sends the URL via POST to the Microsoft Emotions API
    - tl;dr I changed an image data-uri to a publicly available URL so it'd play better with some
      ML libraries that didn't have native Python clients, but did have RESTful APIs.
    """
    data = request.form.get('stillIn')
    data = data[22:].encode('latin-1')
    binary_data = a2b_base64(data)
    session['uuid'] = str(uuid4())
    fn = session['uuid'] + ".png"
    with open('./models/mount/{}'.format(fn), 'wb') as fd:
        fd.write(binary_data)
    subprocess.call("chmod 755 ./models/mount/{}".format(fn),
                    shell=True)
    resource = "http://cs.utexas.edu/~rainier/{}".format(fn)
    print json.dumps({'url': resource})

    # msft request
    try:
        msft_url = "https://api.projectoxford.ai/emotion/v1.0/recognize"
        headers = {'Ocp-Apim-Subscription-Key': config['MSFT_EMOTION_KEY'],
                   'Content-Type': 'application/json'}
        msft_req = requests.post(url=msft_url, data=json.dumps({'url': resource}), headers=headers)
        print "msft {}".format(msft_req.json())
    except:
        flash('No face was detected!')
        return redirect('/', messages=get_flashed_messages())
    session['msft'] = msft_parse(msft_req.json())

    # indicoio request
    session['indico'] = indicoio.fer(resource)

    # clarifai request
    clarifai_api = ClarifaiApi()
    clarifai_req = clarifai_api.tag_image_urls(resource)
    session['clarifai'] = clarifai_parse(clarifai_req)

    return redirect('/results')

def msft_parse(json_obj):
    """Parses the Microsoft Emotions API data into an useful dictionary
    """
    try:
        if len(json_obj[0]['scores']) == 0:
            flash('No face was detected!')
            return redirect('/')
        return json_obj[0]['scores']
    except:
        flash('Check that the temporary datastore is accessible.')
        return redirect('/')

# def indico_parse(json_obj):
#     """Parses the Indicoio API data into an useful dictionary
#        Not needed.
#     """
#     pass

def clarifai_parse(json_obj):
    """Parses the Clarifai API data into an useful list
    """
    probabilities = json_obj['results'][0]['result']['tag']['probs']
    len_over_point_nine_five = len([prob for prob in probabilities if prob >= 0.95])
    len_over_point_nine_five = len_over_point_nine_five if len_over_point_nine_five > 3 else 4
    classes_of_interest = json_obj['results'][0]['result']['tag']['classes'][0:len_over_point_nine_five]
    return classes_of_interest

@app.route('/results')
def show_results():
    # inject resource into the template -> div style
    resource = "http://cs.utexas.edu/~rainier/{}.png".format(session['uuid'])
    # session dict is already in the template as well so no need to pass thru render_template
    chart1_data = generate_emotion_data(session['msft'])
    chart2_data = generate_emotion_data(session['indico'])
    # Base emotional query keys from indicoio as there are less of those
    queries = {'Angry': 'What happened?',
               'Sad': 'What\'s wrong?',
               'Neutral': 'What\'s on your mind?',
               'Surprise': 'What\'s up?',
               'Fear': 'Are you okay?',
               'Happy': 'Share your joy!'}
    primary_emotion_1 = max(session['msft'].iteritems(), key=operator.itemgetter(1))[0]
    print primary_emotion_1
    # Msft API is typically right on these accounts, Indicoio occasionally "overthinks"
    if primary_emotion_1 == 'neutral':
        primary_emotion = 'Neutral'
    elif primary_emotion_1 == 'happiness':
        primary_emotion = 'Happy'
    else:
        primary_emotion_2 = max(session['indico'].iteritems(), key=operator.itemgetter(1))[0]
        primary_emotion = random.choice([primary_emotion_2])
    print primary_emotion
    emotional_query = queries[primary_emotion]
    pretty = {'msft': pretty_print(session['msft']),
              'indico': pretty_print(session['indico']),
              'clarifai': pretty_print(session['clarifai'])}
    return render_template('results.html',
                           resource=resource,
                           chart1_data=chart1_data,
                           chart2_data=chart2_data,
                           emotional_query=emotional_query,
                           pretty=pretty)

# @app.route('/results', methods=['POST'])
# def chat():
#     """A fairly expensive chat interface that could be changed to polling or websockets
#     """
#     resource = "http://cs.utexas.edu/~rainier/{}.png".format(session['uuid'])
#     # session dict is already in the template as well so no need to pass thru render_template
#     chart1_data = generate_emotion_data(session['msft'])
#     chart2_data = generate_emotion_data(session['indico'])
#     pretty = {'msft': pretty_print(session['msft']),
#               'indico': pretty_print(session['indico']),
#               'clarifai': pretty_print(session['clarifai'])}
#     bot_response = g.chatbot.get_response(str(request.form['say']))
#     session['conversation'].append(bot_response)
#     messages = session['conversation']
#     return render_template('results.html',
#                            resource=resource,
#                            chart1_data=chart1_data,
#                            chart2_data=chart2_data,
#                            emotional_query="Let's keep chatting",
#                            pretty=pretty,
#                            messages=messages)

@app.route('/reset')
def reset():
    """Clears the dictionaries and removes the resource from the data store... lol
    """
    session['msft'] = {}
    session['indico'] = {}
    session['clarifai'] = []
    session['conversation'] = []
    subprocess.call("rm ./models/mount/{}.png".format(session['uuid']),
                    shell=True)
    session['uuid'] = {}
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
