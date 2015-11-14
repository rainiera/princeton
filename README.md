# Feelsbook.com
## A HackPrinceton 2015 hack

We take a still of your face, and pool emotional/topic predictions from the Microsoft, Indico, and Clarifai APIs
to spark a conversation with an AI. (with your news feed?)

Using Wikipedia as a training set and fictional news feed data as the test set, we sort the posts into the topics
you might find interest or delight in based on your emotions, with help from gensim.  

## Credz
Rainier - Web development, APIs, ML, and deployment  
Minah and Clarissa - This fun idea :), graphic design, creative direction, learned web development  

## APIs/services used  
- Microsoft Project Oxford  
- Indico  
- Clarifai  
- gensim  
- DigitalOcean  
- Flask (Python)  
- Bower for front-end dependencies (d3, bootstrap)  

## Technical challenges

### Data encoding troubles
- Grabs the binary data from the WebRTC still grab attached to POST  
- WebRTC was somewhat intuitive to use--unicode or ASCII byte-encodings not-so-much.
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

### Front-end
- One day I will get better at front-end!  

### Deployment
- One day I will get better at ops!  
