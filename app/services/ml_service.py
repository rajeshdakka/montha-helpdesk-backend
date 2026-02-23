import pickle

model = pickle.load(open("model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))

def predict_priority(issue):
    text_vector = vectorizer.transform([issue])
    prediction = model.predict(text_vector)[0]
    prob = model.predict_proba(text_vector)
    confidence = float(max(prob[0]))

    return prediction, confidence