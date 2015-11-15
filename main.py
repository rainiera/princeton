import os
import sys
import subprocess
import json
import logging
import requests
import indicoio
from clarifai.client import ClarifaiApi
from binascii import a2b_base64
from uuid import uuid4
from flask import Flask, render_template, request, redirect, session, Response, url_for, flash, get_flashed_messages

from config import config
from models.d3_injectors import generate_emotion_data

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
    msft_url = "https://api.projectoxford.ai/emotion/v1.0/recognize"
    headers = {'Ocp-Apim-Subscription-Key': config['MSFT_EMOTION_KEY'],
               'Content-Type': 'application/json'}
    msft_req = requests.post(url=msft_url, data=json.dumps({'url': resource}), headers=headers)
    print msft_req.json()
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
    queries = ['What\'s on your mind?', 'What\'s wrong?', 'Vent it out.',
               'What are you so happy about?', 'What happened this time...']
    emotional_query = queries[0]
    return render_template('results.html',
                           resource=resource,
                           chart1_data=chart1_data,
                           chart2_data=chart2_data,
                           emotional_query=emotional_query)

@app.route('/reset')
def reset():
    """Clears the dictionaries and removes the resource from the data store... lol
    """
    session['msft'] = {}
    session['indico'] = {}
    session['clarifai'] = []
    subprocess.call("rm ./models/mount/{}.png".format(session['uuid']),
                    shell=True)
    session['uuid'] = {}
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
