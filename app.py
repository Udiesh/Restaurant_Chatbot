from flask import Flask, request, jsonify, session
import json
import random
import torch
from transformers import BertTokenizer, BertForSequenceClassification
import uuid
import os
import requests

# Check if running on Render.com (production) or locally
IS_PRODUCTION = os.environ.get('RENDER', False)

# Load BERT model + tokenizer + label encoder
if IS_PRODUCTION:
    # In production, load from Hugging Face
    model_name = "YourHuggingFaceUsername/sarovar-bert-intent"  # Replace with your username
    tokenizer = BertTokenizer.from_pretrained(model_name)
    model = BertForSequenceClassification.from_pretrained(model_name)
    
    # Download label encoder from Hugging Face if not exists
    if not os.path.exists("label_encoder.pt"):
        label_encoder_url = f"https://huggingface.co/{model_name}/resolve/main/label_encoder.pt"
        response = requests.get(label_encoder_url)
        with open("label_encoder.pt", "wb") as f:
            f.write(response.content)
    
    label_encoder = torch.load("label_encoder.pt")
else:
    # In development, load from local files
    tokenizer = BertTokenizer.from_pretrained("bert_intent_model")
    model = BertForSequenceClassification.from_pretrained("bert_intent_model")
    label_encoder = torch.load("label_encoder.pt")

# Load intent data
with open('full.json') as file:
    data = json.load(file)

app = Flask(__name__)
app.secret_key = 'sarovar_south_spice_secret_key'  # Required for session

# Store feedback ratings
conversation_ratings = {}

# Predict intent using BERT with confidence threshold
def predict_intent_bert(sentence):
    inputs = tokenizer(sentence, return_tensors="pt", truncation=True, padding=True)
    with torch.no_grad():
        outputs = model(**inputs)
    predicted_label = torch.argmax(outputs.logits).item()
    confidence = torch.softmax(outputs.logits, dim=-1)[0][predicted_label].item()
    if confidence > 0.7:  # Confidence threshold
        return label_encoder.inverse_transform([predicted_label])[0]
    else:
        return "fallback"  # Return fallback if confidence is low

# Pick a response from the intent with context awareness
def get_response(intent_tag, session_id):
    if intent_tag == "fallback":
        return "Sorry, I didn't get that. Can you rephrase?"
    
    # Special handling for booking a table with session memory
    if intent_tag == "book_table":
        # Check if user already has a booking
        bookings = session.get('bookings', {})
        if session_id in bookings:
            previous_booking = bookings[session_id]
            return f"I see you already have a booking with ID: {previous_booking}. Would you like to book another table or modify your existing reservation?"
        
        # No existing booking, create a new one
        for intent in data['intents']:
            if intent['tag'] == intent_tag:
                response = random.choice(intent['responses'])
                if '{{booking_id}}' in response:
                    booking_id = str(uuid.uuid4())[:8]
                    response = response.replace('{{booking_id}}', booking_id)
                    
                    # Store the booking ID in session
                    if 'bookings' not in session:
                        session['bookings'] = {}
                    session['bookings'][session_id] = booking_id
                    session.modified = True
                    
                return response
    
    # Handle when user wants to book another table
    if "book another table" in request.json.get('message', '').lower():
        for intent in data['intents']:
            if intent['tag'] == "book_table":
                response = random.choice(intent['responses'])
                if '{{booking_id}}' in response:
                    booking_id = str(uuid.uuid4())[:8]
                    response = response.replace('{{booking_id}}', booking_id)
                    
                    # Update or create the booking ID in session
                    if 'bookings' not in session:
                        session['bookings'] = {}
                    session['bookings'][session_id] = booking_id
                    session.modified = True
                    
                return response
    
    # Handle when user wants to modify existing booking
    if "modify existing booking" in request.json.get('message', '').lower():
        bookings = session.get('bookings', {})
        if session_id in bookings:
            previous_booking = bookings[session_id]
            return f"To modify your reservation with booking ID: {previous_booking}, please call us at (123) 456-7890 or visit our website. What other information can I help you with?"
    
    # Normal response handling for other intents
    for intent in data['intents']:
        if intent['tag'] == intent_tag:
            response = random.choice(intent['responses'])
            if '{{booking_id}}' in response:
                booking_id = str(uuid.uuid4())[:8]
                response = response.replace('{{booking_id}}', booking_id)
            return response
    
    return "Sorry, I didn't get that. Can you rephrase?"

# Homepage
@app.route('/')
def home():
    return app.send_static_file('index.html')

# Chat route
@app.route('/chat', methods=['POST'])
def chat():
    message = request.json['message']
    
    # Get or create a unique session ID for this user
    session_id = session.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
    
    intent_tag = predict_intent_bert(message)
    response = get_response(intent_tag, session_id)
    
    return jsonify({
        'response': response,
        'intent': intent_tag  # Sending intent to frontend can be useful
    })

# Feedback rating route
@app.route('/rate', methods=['POST'])
def rate_conversation():
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({'status': 'error', 'message': 'No active session'}), 400
    
    rating = request.json.get('rating')
    feedback = request.json.get('feedback', '')
    
    if not rating or not isinstance(rating, int) or rating < 1 or rating > 5:
        return jsonify({'status': 'error', 'message': 'Invalid rating'}), 400
    
    # Store the rating
    conversation_ratings[session_id] = {
        'rating': rating,
        'feedback': feedback,
        'timestamp': random.randint(1000000000, 9999999999)  # Simple timestamp substitute
    }
    
    return jsonify({
        'status': 'success',
        'message': 'Thank you for your feedback!'
    })

if __name__ == '__main__':
    app.run(debug=True)
