from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import pickle
import uuid
import boto3
from botocore.exceptions import ClientError


# ML MODEL LOADING

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "campaign_model.pkl")
model = pickle.load(open(MODEL_PATH, "rb"))


# FLASK APP

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

EMAIL_REGEX = r'^[^@\s]+@[^@\s]+\.[^@\s]+$'


# AWS CONFIGURATION

REGION = 'us-east-1'
dynamodb = boto3.resource('dynamodb', region_name=REGION)
sns = boto3.client('sns', region_name=REGION)

# Replace with your SNS topic ARN if you want notifications
SNS_TOPIC_ARN = 'arn:aws:sns:us-east-1:xxxxxxxxxxxx:campaign_topic'

# DynamoDB Tables
users_table = dynamodb.Table('Users')
admin_table = dynamodb.Table('AdminUsers')
campaigns_table = dynamodb.Table('Campaigns')
activity_table = dynamodb.Table('UserActivity')
user_campaigns_table = dynamodb.Table('UserCampaigns')
products_table = dynamodb.Table('Products')  # New table for products


# SEGMENTS

HTML_TO_INT = {
    "engaged": 0,
    "frequent_visitor": 1,
    "loyal": 2,
    "new_users": 3
}
SEGMENT_MAP = {v: k for k, v in HTML_TO_INT.items()}


# AWS SNS NOTIFICATION

def send_notification(subject, message):
    try:
        sns.publish(TopicArn=SNS_TOPIC_ARN, Subject=subject, Message=message)
    except ClientError as e:
        print(f"Error sending SNS notification: {e}")


# HELPER FUNCTIONS

def get_user_features(user_id):
    response = activity_table.get_item(Key={'user_id': user_id})
    activity = response.get('Item', {
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


# ROUTES


@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('home'))
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')


# USER SIGNUP

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if user exists
        response = users_table.scan(
            FilterExpression="username = :u",
            ExpressionAttributeValues={":u": username}
        )
        if response['Items']:
            return "User already exists!"

        user_id = str(uuid.uuid4())

        users_table.put_item(Item={
            'user_id': user_id,
            'username': username,
            'password': password
        })

        # Initialize ML activity
        activity_table.put_item(Item={
            'user_id': user_id,
            'offers_opened': 0,
            'offers_clicked': 0,
            'purchases': 0,
            'last_open_days': 0,
            'total_visits': 1
        })

        # Initialize campaigns for this user
        user_campaigns_table.put_item(Item={'user_id': user_id, 'campaign_ids': []})

        session['user_id'] = user_id
        session['username'] = username

        send_notification("New User Signup", f"User {username} signed up.")

        return redirect(url_for('home'))

    return render_template('signup.html')


# USER LOGIN

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        response = users_table.scan(
            FilterExpression="username = :u",
            ExpressionAttributeValues={":u": username}
        )
        user_list = response.get('Items', [])

        if user_list and user_list[0]['password'] == password:
            user = user_list[0]
            session['user_id'] = user['user_id']
            session['username'] = user['username']

            # Ensure activity exists
            activity_table.update_item(
                Key={'user_id': user['user_id']},
                UpdateExpression="SET total_visits = if_not_exists(total_visits, :start) + :inc, last_open_days = :zero",
                ExpressionAttributeValues={':inc': 1, ':start': 0, ':zero': 0}
            )

            send_notification("User Login", f"User {username} logged in.")

            return redirect(url_for('home'))

        return "Invalid credentials!"

    return render_template('login.html')


# USER HOME

@app.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Track visits
    activity_table.update_item(
        Key={'user_id': user_id},
        UpdateExpression="SET total_visits = if_not_exists(total_visits, :start) + :inc, last_open_days = :zero",
        ExpressionAttributeValues={':inc': 1, ':start': 0, ':zero': 0}
    )

    # Get campaigns for this user
    response = user_campaigns_table.get_item(Key={'user_id': user_id})
    campaign_ids = response.get('Item', {}).get('campaign_ids', [])

    campaigns_list = []
    for cid in campaign_ids:
        res = campaigns_table.get_item(Key={'campaign_id': cid})
        if 'Item' in res:
             item = res['Item']
        campaigns_list.append({
            "id": item.get("campaign_id"),
            "name": item.get("name"),
            "offer": item.get("offer"),
            "start_time": item.get("start_time"),
            "end_time": item.get("end_time")
        }) #Track offers_opened (ML feature parity with local)
        
        if campaigns_list:
            activity_table.update_item(
                Key={'user_id': user_id},
                UpdateExpression="SET offers_opened = if_not_exists(offers_opened, :zero) + :inc",
                ExpressionAttributeValues={
                    ':inc': len(campaigns_list),
                    ':zero': 0
        }
    )
    # Get products
    products = products_table.scan().get('Items', [])

    return render_template('home.html', username=session['username'], campaigns=campaigns_list, products=products)

# ------------------------
# PRODUCT ROUTES
# ------------------------
@app.route('/products')
def products_list():
    products = products_table.scan().get('Items', [])
    return render_template('products.html', products=products)

@app.route('/product/<product_id>')
def product_detail(product_id):
    res = products_table.get_item(Key={'product_id': product_id})
    product = res.get('Item')
    if not product:
        return "Product not found", 404
    return render_template('product.html', product=product)

@app.route('/buy/<product_id>', methods=['POST'])
def buy_product(product_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    # Increment product purchases
    res = products_table.get_item(Key={'product_id': product_id})
    product = res.get('Item')
    if product:
        product['purchases'] = product.get('purchases', 0) + 1
        products_table.put_item(Item=product)

    # Increment user purchase count in UserActivity
    activity_table.update_item(
        Key={'user_id': user_id},
        UpdateExpression="SET purchases = if_not_exists(purchases, :zero) + :inc",
        ExpressionAttributeValues={':inc': 1, ':zero': 0}
    )

    flash("Purchase successful!")
    return redirect(url_for('product_detail', product_id=product_id))

# ------------------------
# CAMPAIGN CLICK
# ------------------------
@app.route('/campaign/<campaign_id>')
def campaign_click(campaign_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Increment offers_clicked
    activity_table.update_item(
        Key={'user_id': user_id},
        UpdateExpression="SET offers_clicked = if_not_exists(offers_clicked, :zero) + :inc",
        ExpressionAttributeValues={':inc': 1, ':zero': 0}
    )

    return redirect(url_for('home'))


# ADMIN SIGNUP/LOGIN

@app.route('/admin/signup', methods=['GET', 'POST'])
def admin_signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        response = admin_table.get_item(Key={'username': username})
        if 'Item' in response:
            return "Admin already exists!"

        admin_table.put_item(Item={'username': username, 'password': password})
        send_notification("Admin Signup", f"Admin {username} registered.")
        return redirect(url_for('admin_login'))

    return render_template('admin_signup.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        response = admin_table.get_item(Key={'username': username})
        if 'Item' in response and response['Item']['password'] == password:
            session['admin'] = username
            return redirect(url_for('admin_dashboard'))

        return "Invalid admin credentials!"

    return render_template('admin_login.html')

# ------------------------
# ADMIN DASHBOARD
# ------------------------
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    campaigns_list = []

    # Fetch all campaigns
    response = campaigns_table.scan()
    for item in response.get('Items', []):
        campaigns_list.append({
            "name": item.get("name"),
            "status": item.get("status"),
            "start_time": item.get("start_time"),
            "end_time": item.get("end_time")
        })

    return render_template('admin_dashboard.html', username=session['admin'], campaigns=campaigns_list)

# ------------------------
# LAUNCH CAMPAIGN
# ------------------------
@app.route('/launch-campaign', methods=['GET', 'POST'])
def launch_campaign_submit():
    if request.method == 'POST':
        html_segment = request.form['segment']
        selected_segment = HTML_TO_INT[html_segment]
        campaign_id = str(uuid.uuid4())

        campaign_item = {
            'campaign_id': campaign_id,
            'name': request.form['name'],
            'type': request.form['type'],
            'subject': request.form['subject'],
            'offer': request.form['offer'],
            'segment': selected_segment,
            'start_time': request.form['start_time'],
            'end_time': request.form['end_time'],
            'status': "Scheduled"
        }

        campaigns_table.put_item(Item=campaign_item)
        send_notification("New Campaign", f"Campaign '{campaign_item['name']}' launched.")

        # ML logic: assign campaigns to users
        for user_item in activity_table.scan()['Items']:
            user_id = user_item['user_id']
            features = get_user_features(user_id)
            prediction = model.predict(features)
            send_campaign, customer_profile = prediction[0]

            if customer_profile == selected_segment and (send_campaign == 1 or user_item['total_visits'] >= 2):
                # Update user_campaigns table
                res = user_campaigns_table.get_item(Key={'user_id': user_id})
                campaign_ids = res.get('Item', {}).get('campaign_ids', [])
                campaign_ids.append(campaign_id)
                user_campaigns_table.put_item(Item={'user_id': user_id, 'campaign_ids': campaign_ids})

        return redirect(url_for('admin_dashboard'))

    return render_template('launch_campaign.html')


# LOGOUT

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('user_id', None)
    session.pop('admin', None)
    return redirect(url_for('index'))


# RUN APP

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)