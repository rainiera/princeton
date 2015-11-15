import json


def generate_emotion_data(emotions):
    data = []
    # for emotion in sorted(emotions.iterkeys(), reverse=True):
    for emotion in emotions.iterkeys():
        data.append([str(emotion).lower(), emotions[emotion]])
    return data

def pretty_print(obj):
    return json.dumps(obj, sort_keys=True, indent=4, separators=(',', ': '))
