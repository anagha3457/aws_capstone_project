
from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import pickle

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "campaign_model.pkl")

model = pickle.load(open(MODEL_PATH, "rb"))


app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

EMAIL_REGEX = r'^[^@\s]+@[^@\s]+\.[^@\s]+$'

# In-memory database (dictionary)
users = []
admin_users = {}
campaign = {} 
campaigns = [] #all campaigns
user_activity = {} #user behavioir data
user_campaigns = {} #campaign data per user

SEGMENT_MAP = {
    0: "Engaged",
    1: "Frequent Visitor",
    2: "Loyal",
    3: "New"
}

HTML_TO_INT = {
    "engaged": 0,
    "frequent_visitor": 1,
    "loyal": 2,
    "new_users": 3
}

def get_user_features(user_id):
    activity = user_activity.get(user_id, {
        "offers_opened": 0,
        "offers_clicked": 0,
        "purchases": 0,
        "last_open_days": 999,
        "total_visits": 1
    })

    return [[
        activity["offers_opened"],
        activity["offers_clicked"],
        activity["purchases"],
        activity["last_open_days"],
        activity["total_visits"]
    ]]


@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('home'))
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # check if user already exists
        for user in users:
            if user['username'] == username:
                return "User already exists!"

        user_id = len(users) + 1  # auto-increment ID

        user = {
            "user_id": user_id,
            "username": username,
            "password": password
        }

        users.append(user)

        # 🔹 ML INITIALIZATION (THIS WAS MISSING)
        user_activity[user_id] = {
            "offers_opened": 0,
            "offers_clicked": 0,
            "purchases": 0,
            "last_open_days": 0,
            "total_visits": 1
        }

        user_campaigns[user_id] = []

        session['user_id'] = user_id
        session['username'] = username

        return redirect(url_for('home'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        for user in users:
            if user['username'] == username and user['password'] == password:
                session['user_id'] = user['user_id']
                session['username'] = user['username']

                # Initialize user activity for ML 
                user_activity.setdefault(user['user_id'], {
                    "offers_opened": 0,
                    "offers_clicked": 0,
                    "purchases": 0,
                    "last_open_days": 1,
                    "total_visits": 1
                })

                return redirect(url_for('home'))
            
        return "Invalid credentials!"
    
    return render_template('login.html')


@app.route('/home')
def home():
    if 'user_id' in session:
        user_id = session['user_id']

        # Ensure user_activity exists
        if user_id not in user_activity:
            user_activity[user_id] = {
                "offers_opened": 0,
                "offers_clicked": 0,
                "purchases": 0,
                "last_open_days": 0,
                "total_visits": 1
            }

        # Track visit
        user_activity[user_id]["total_visits"] += 1
        user_activity[user_id]["last_open_days"] = 0


        #Get campaigns for this user
        user_campaign_list = user_campaigns.get(user_id, [])

        #Track offers shown (opened)
        if user_campaign_list:
            user_activity[user_id]["offers_opened"] += len(user_campaign_list)

        # 🔍 Optional: debug print (VERY useful)
        print(f" User {user_id} activity:", user_activity[user_id])
        print(f" Campaigns shown:", [c["name"] for c in user_campaign_list])

        return render_template(
            'home.html',
            username=session['username'],
            products=products,
            campaigns=user_campaign_list
        )

    return redirect(url_for('login'))

@app.route('/campaign/<int:campaign_id>')
def campaign_click(campaign_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Increment offer click count
    if user_id in user_activity:
        user_activity[user_id]["offers_clicked"] += 1

    print(f" Campaign {campaign_id} clicked by user {user_id}")
    print(" Updated activity:", user_activity[user_id])

    # Optional: redirect user somewhere meaningful
    return redirect(url_for('home'))



products = {
    1: {
        "id": 1,
        "name": "Boat Headphones",
        "price": 2500,
        "description": "Wireless headphones with deep bass and long battery life",
        "category": "Electronics",
        "tags": ["audio", "headphones", "wireless"],
        "target_audience": ["students", "working"],
        "image": "product1.jpg",
        "views": 0,
        "purchases": 0
    },
    2: {
        "id": 2,
        "name": "Smart Watch",
        "price": 2000,
        "description": "Fitness smartwatch with heart rate monitoring",
        "category": "Wearables",
        "tags": ["fitness", "watch", "health"],
        "target_audience": ["working"],
        "image": "product2.jpg",
        "views": 0,
        "purchases": 0
    },
    3: {
        "id": 3,
        "name": "JBL Bluetooth Speaker",
        "price": 3000,
        "description": "Portable Bluetooth speaker with powerful sound and deep bass",
        "category": "Electronics",
        "tags": ["audio", "speaker", "bluetooth", "portable"],
        "target_audience": ["students", "working"],
        "image": "product3.jpg",
        "views": 0,
        "purchases": 0
    },
    4: {
        "id": 4,
        "name": "Dell Laptop",
        "price": 55000,
        "description": "High-performance Dell laptop suitable for work, study, and programming",
        "category": "Computers",
        "tags": ["laptop", "dell", "computer", "work"],
        "target_audience": ["students", "working"],
        "image": "product4.jpg",
        "views": 0,
        "purchases": 0
    },
    5: {
        "id": 5,
        "name": "Dell Bluetooth Mouse",
        "price": 1500,
        "description": "Wireless Bluetooth mouse with smooth tracking and ergonomic design",
        "category": "Computer Accessories",
        "tags": ["mouse", "bluetooth", "dell", "accessories"],
        "target_audience": ["students", "working"],
        "image": "product5.jpg",
        "views": 0,
        "purchases": 0
    },
    6: {
        "id": 6,
        "name": "Classmate Pens",
        "price": 100,
        "description": "Hardcover writing journal for notes, planning, and daily journaling",
        "category": "Stationery",
        "tags": ["journal", "writing", "notes", "planner"],
        "target_audience": ["students", "working"],
        "image": "product6.jpg",
        "views": 0,
        "purchases": 0
    },
    7: {
        "id": 7,
        "name": "Writing Journal",
        "price": 300,
        "description": "Smooth writing pens ideal for exams, notes, and everyday use",
        "category": "Stationery",
        "tags": ["pens", "writing", "classmate", "stationery"],
        "target_audience": ["students"],
        "image": "product7.jpg",
        "views": 0,
        "purchases": 0
    },
    8: {
        "id": 8,
        "name": "Camel Water Colours",
        "price": 250,
        "description": "Water colour set perfect for painting, sketching, and art projects",
        "category": "Art Supplies",
        "tags": ["art", "painting", "watercolours", "camel"],
        "target_audience": ["students", "artists"],
        "image": "product8.jpg",
        "views": 0,
        "purchases": 0
    },
    9: {
        "id": 9,
        "name": "Laptop Bag",
        "price": 700,
        "description": "Durable and stylish laptop bag with padded compartments",
        "category": "Accessories",
        "tags": ["laptop", "bag", "travel", "office"],
        "target_audience": ["students", "working"],
        "image": "product9.jpg",
        "views": 0,
        "purchases": 0
    }
}


@app.route('/product/<int:product_id>')
def product(product_id):
    product = products.get(product_id)
    if not product:
        return "Product not found", 404
    return render_template('product.html', product=product)


@app.route('/buy/<int:product_id>', methods=['POST'])
def buy_product(product_id):
    product = products.get(product_id)
    user_id = session.get('user_id')

    if product:
        product["purchases"] += 1
        if user_id in user_activity:
            user_activity[user_id]["purchases"] += 1

        flash("Item purchased successfully.")

    return redirect(url_for('product', product_id=product_id))


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

# Admin Routes
@app.route('/admin/signup', methods=['GET', 'POST'])
def admin_signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username in admin_users:
            return "Admin already exists!"
        
        admin_users[username] = password
        return redirect(url_for('admin_login'))
    return render_template('admin_signup.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username in admin_users and admin_users[username] == password:
            session['admin'] = username
            return redirect(url_for('admin_dashboard'))
        return "Invalid admin credentials!"
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin' in session:
        return render_template('admin_dashboard.html', username=session['admin'], campaigns=campaigns)
    return redirect(url_for('admin_login'))


@app.route('/launch-campaign', methods=['GET','POST'])
def launch_campaign_submit():
    if request.method == 'POST':
        html_segment = request.form['segment']  # keep as string from HTML

        # Convert HTML string to ML integer
        selected_segment = HTML_TO_INT[html_segment]

        campaign = {
            "id": len(campaign) + 1,  # unique auto-increment ID
            "name": request.form['name'],
            "type": request.form['type'],
            "subject": request.form['subject'],
            "offer": request.form['offer'],
            # "segment": int(request.form['segment']),
            "segment": selected_segment, 
            "start_time": request.form['start_time'],
            "end_time": request.form['end_time'],
            "status": "Scheduled"
        }

        campaigns.append(campaign)

        # selected_segment = campaign["segment"]

        # ML LOGIC STARTS HERE
        for user_id in user_activity.keys():
            features = get_user_features(user_id)

            prediction = model.predict(features)

            print("User:", user_id)
            print("Features:", features)
            print("Prediction:", prediction)

            send_campaign = prediction[0][0]
            customer_profile = prediction[0][1]

            # if send_campaign == 1 and customer_profile == selected_segment:
            #     user_campaigns.setdefault(user_id, []).append(campaign)
            if customer_profile == selected_segment:
                if send_campaign == 1 or user_activity[user_id]["total_visits"] >= 2:
                    user_campaigns.setdefault(user_id, []).append(campaign)

        return redirect(url_for('admin_dashboard'))

    return render_template('launch_campaign.html')

@app.route('/admin-dashboard')
def admin_dashboard_status():
    return render_template('admin_dashboard.html', campaigns=campaigns)


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)

