import sys
import subprocess
import json
import logging
import requests
from binascii import a2b_base64
from uuid import uuid4
from flask import Flask, render_template, request, redirect, session, Response, url_for

from config import config


app = Flask(__name__)
app.secret_key = config['APP_SECRET_KEY']
app.config['SECRET_KEY'] = config['APP_SECRET_KEY']
SECRET_KEY = config['APP_SECRET_KEY']

# So it logs Flask errors to stdout - nice for Heroku logs and CI if used
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.ERROR)


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
    fn = str(uuid4()) + ".png"
    with open('./models/mount/{}'.format(fn), 'wb') as fd:
        fd.write(binary_data)
    subprocess.call("chmod 755 ./models/mount/{}".format(fn),
                    shell=True)
    resource = "http://cs.utexas.edu/~rainier/{}".format(fn)
    url = "https://api.projectoxford.ai/emotion/v1.0/recognize"
    headers = {'Ocp-Apim-Subscription-Key': config['MSFT_EMOTION_KEY'],
               'Content-Type': 'application/json'}
    print json.dumps({'url': resource})
    req = requests.post(url=url, data=json.dumps({'url': resource}), headers=headers)
    return str(req.json())

def test_img_handler_msft():
    """Tests the image handler
    """
    pass

def test_img_handler_indicoio():
    """Tests the image handler
    """
    pass

def test_img_handler_clarifai():
    """Tests the image handler
    """
    pass


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
