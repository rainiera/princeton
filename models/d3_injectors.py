__author__ = 'rainierababao'

def generate_emotion_data(emotions):
    data = []
    for emotion, percentage in emotions.iteritems():
        data.append([str(emotion), percentage])
    return data

