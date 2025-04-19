from flask import Flask, request, jsonify, session
import json
import random
import uuid
import os
import re

app = Flask(__name__)
app.secret_key = 'sarovar_south_spice_secret_key'  # Required for session

# Enhanced intent recognition with context awareness and query understanding
def enhanced_intent_recognition(text, session_id=None):
    text = text.lower()
    scores = {
        "greeting": 0,
        "book_table": 0,
        "menu": 0,
        "hours": 0,
        "bye": 0,
        "contact": 0,
        "fallback": 0
    }
    
    # Direct keyword matching (existing approach)
    if any(word in text for word in ["hello", "hi", "hey", "greetings", "namaste", "vanakkam"]):
        scores["greeting"] += 10
    
    if any(word in text for word in ["book", "reservation", "table", "reserve"]):
        scores["book_table"] += 10
    
    if any(word in text for word in ["menu", "food", "eat", "order", "dish", "cuisine"]):
        scores["menu"] += 10
    
    if any(word in text for word in ["hour", "timing", "open", "close", "when", "schedule"]):
        scores["hours"] += 10
    
    if any(word in text for word in ["bye", "goodbye", "see you", "farewell", "thanks", "thank you"]):
        scores["bye"] += 10
    
    if any(word in text for word in ["contact", "phone", "email", "reach", "feedback", "call"]):
        scores["contact"] += 10
    
    # Handle ambiguous cases with contextual understanding
    
    # Time-related queries
    if re.search(r'(what|which) (time|day)', text) or "when" in text:
        if any(word in text for word in ["come", "visit", "best", "busy", "quiet"]):
            scores["hours"] += 8
        if any(word in text for word in ["book", "reserve", "table", "seat"]):
            scores["book_table"] += 8
    
    # Food-related queries without explicit menu keywords
    if any(word in text for word in ["recommend", "special", "signature", "popular", "best", "authentic"]):
        scores["menu"] += 8
    
    # Location and facilities queries
    if any(word in text for word in ["location", "address", "direction", "parking", "near", "where"]):
        scores["contact"] += 8
    
    # Group booking related queries
    if any(phrase in text for phrase in ["large group", "many people", "party", "celebration", "event", "accommodate"]):
        scores["book_table"] += 8
    
    # Dietary questions
    if any(word in text for word in ["vegetarian", "vegan", "allergy", "gluten", "spicy", "diet"]):
        scores["menu"] += 8
    
    # Evening/celebration related
    if any(word in text for word in ["tonight", "evening", "celebrate", "anniversary", "birthday", "date"]):
        if not any(word in text for word in ["menu", "food", "dish"]):
            scores["book_table"] += 6
    
    # Check for session context (if user previously booked)
    if session_id:
        bookings = session.get('bookings', {})
        if session_id in bookings and any(word in text for word in ["modify", "change", "cancel", "update"]):
            scores["book_table"] += 10
    
    # If all scores are low, increase fallback score
    if all(score < 5 for intent, score in scores.items() if intent != "fallback"):
        scores["fallback"] += 5
    
    # Return the intent with the highest score
    max_intent = max(scores, key=scores.get)
    max_score = scores[max_intent]
    
    # Only return an intent if the score is above a threshold
    if max_score > 4:
        return max_intent
    else:
        return "fallback"

# Load intent data with error handling
try:
    with open('full.json') as file:
        data = json.load(file)
except (FileNotFoundError, json.JSONDecodeError):
    # Create a simple fallback data structure if file is missing or invalid
    data = {
        "intents": [
            {
                "tag": "greeting",
                "responses": ["Hello! Welcome to Sarovar South Spice. How can I help you today?"]
            },
            {
                "tag": "book_table",
                "responses": ["I'd be happy to help you book a table. Your Booking ID is {{booking_id}}. What date and time would you prefer?"]
            },
            {
                "tag": "menu",
                "responses": ["Our menu features authentic South Indian dishes including dosas, idlis, and various curries. Would you like to know about any specific dish?"]
            },
            {
                "tag": "hours",
                "responses": ["We're open from 11:00 AM to 10:00 PM every day."]
            },
            {
                "tag": "contact",
                "responses": ["You can reach us at (123) 456-7890 or email us at info@sarovarsouthspice.com."]
            },
            {
                "tag": "bye",
                "responses": ["Thank you for chatting with us. Have a great day!"]
            },
            {
                "tag": "fallback",
                "responses": ["I'm sorry, I didn't understand that. Could you please rephrase?"]
            }
        ]
    }

# Store feedback ratings
conversation_ratings = {}

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
    
    intent_tag = enhanced_intent_recognition(message, session_id)
    response = get_response(intent_tag, session_id)
    
    return jsonify({
        'response': response,
        'intent': intent_tag
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

# Create a test route to help with debugging
@app.route('/test')
def test():
    return jsonify({
        'status': 'ok',
        'message': 'Test endpoint is working'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)), debug=False)
