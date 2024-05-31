from flask import Flask, render_template, redirect, url_for, request, session, Response
# import bcrypt
from flask_bcrypt import Bcrypt
import jwt   # Import the PyJWT library
import time#
from base64 import b64encode, b64decode#
import cv2#
import numpy as np
import os#
from moviepy.editor import ImageClip, AudioFileClip
import moviepy.audio.fx.all as afx
from moviepy.video.fx.fadein import fadein
from moviepy.video.fx.fadeout import fadeout
from moviepy.editor import concatenate_videoclips
import psycopg2

app = Flask(__name__)
app.secret_key = "!@#$%^adsfmnv"
# db = mysql.connector.connect(
#     host="localhost",
#     user="root",
#     password="abc",
#     database="ISIS_DB"
# )
bcrypt = Bcrypt()
def database():
    con = psycopg2.connect("postgresql://aditya_vadali:1oEY9pfM6DkgKyE3sbj1Pg@iss-project-9050.8nk.gcp-asia-southeast1.cockroachlabs.cloud:26257/defaultdb?sslmode=require&sslrootcert=root.crt")
    return con

# def database():
#         # Decode the base64 certificate
#     cert_decoded = b64decode(os.environ['ROOT_CERT_BASE64'])
    
#     # Define the path to save the certificate
#     cert_path = '/opt/render/.postgresql/root.crt'
#     os.makedirs(os.path.dirname(cert_path), exist_ok=True)
    
#     # Write the certificate to the file
#     with open(cert_path, 'wb') as cert_file:
#         cert_file.write(cert_decoded)
    
#     # Set up the connection string with the path to the certificate
#     conn = psycopg2.connect(
#         "host=iss-project-9050.8nk.gcp-asia-southeast1.cockroachlabs.cloud "
#         "port=26257 dbname=defaultdb user=aditya_vadali "
#         "password=1oEY9pfM6DkgKyE3sbj1Pg sslmode=verify-full&sslrootcert=root.crt"
#         f"sslrootcert={cert_path}"
#     )
#     return conn


filelister = []
cursor = database().cursor()
# cursor = database().cursor()

# salt_hash = bcrypt.gensalt()

def utf8_to_image(utf8_string):
    if utf8_string.startswith("data:image/jpeg;base64,"):
        utf8_string = utf8_string[len("data:image/jpeg;base64,"):]
    image_data = b64decode(utf8_string)
    nparr = np.frombuffer(image_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img

# Update the generate_jwt_token function
def generate_jwt_token(username):
    payload = {'username': username}
    secret_key = '@#23$%^'
    expiration_time = 36000  # Set your desired expiration time in seconds
    token = jwt.encode({'exp': time.time() + expiration_time, **payload}, secret_key, algorithm='HS256')

    # Store token and user details in the session
    session['jwt_token'] = token
    session['user_details'] = {'username': username}

    return {'username': username, 'token': token}

def verify_jwt_token(token):
    secret_key = '@#23$%^'  # Replace with the same key used for encoding
    try:
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Token has expired
    except jwt.InvalidTokenError:
        return None  # Invalid token
    
# Add a protected route that requires a valid JWT token
def find_user_details(user_id):
    cursor.execute("SELECT * FROM accounts WHERE username = %s", (user_id,))
    user_data = cursor.fetchone()
    if user_data:
        return {'username': user_data[1], 'email': user_data[2], 'password': user_data[3]}
    return None

def preview(data, name, transition_name, duration, res):
    global filelister
    filelister = []
    token = session.get('jwt_token')
    if not token:
        return redirect(url_for('login'))
    username = session['user_details']['username']
    img_dur = int(duration)
    utf8_images = []
    for row in data:
        remo = row.read()
        utf8image = b64encode(remo).decode("utf-8")
        filelister.append(b64encode(remo))
        utf8_images.append(utf8image)
    print(res)
    width, height = map(int, res.split())
    print(f"width:{width} || height:{height}")
    images = [utf8_to_image(utf8_str) for utf8_str in utf8_images if utf8_str]

    max_width = width
    max_height = height

    resized_images = [cv2.resize(img, (max_width, max_height)) for img in images]
    resized_images_rgb = [cv2.cvtColor(img, cv2.COLOR_BGR2RGB) for img in resized_images]

    clips = []
    for img in resized_images_rgb:
        clip = ImageClip(img).set_duration(img_dur)
        clips.append(clip)
    
    # Apply fadein transition between consecutive clips´
    transitioned_clips = []
    if transition_name == 'fadein': 
        for i in range(len(clips)):
            if i != 0:
                transitioned_clip = fadein(clips[i], duration=1)  # Apply fadein effect
            else:
                transitioned_clip = clips[i]
            transitioned_clips.append(transitioned_clip)

    elif transition_name == 'crossfade':
        for i in range(len(clips)):
            transitioned_clip = clips[i].crossfadein(1)
            transitioned_clips.append(transitioned_clip)
    elif transition_name == 'fadeout':
        for i in range(len(clips)):
            if i != 0:
                transitioned_clip = fadeout(clips[i], duration=1)  # Apply fadein effect
            else:
                transitioned_clip = clips[i]
            transitioned_clips.append(transitioned_clip)
    else:
        return Response("dobbindi", 200)
    # Concatenate the clips into a single video clip
    final_clip = concatenate_videoclips(transitioned_clips, method="compose")

    # Set fps attribute for the final clip
    final_clip.fps = 24  # Adjust fps as needed

    # Set audio clip
    audioclip = AudioFileClip(f"{name}")
    audioclip = afx.audio_loop(audioclip, duration=(len(filelister)*img_dur))
    final_clip.audio = audioclip

    output_path = os.path.join("static", "output_video.mp4")
    final_clip.write_videofile(output_path, codec='libx264')

    return Response("success", 200)


@app.route('/', methods=['GET', 'POST'])
@app.route('/welcome', methods=['GET', 'POST'])
def welcome():
    token = session.get('jwt_token')
    if not token:
        return redirect(url_for('login'))
    user_data = None
    if token:
        payload = verify_jwt_token(token)
        if payload:
            # Token is valid, get user details from payload
            username = payload['username']
            user_data = find_user_details(username)
        else :
            return render_template('login.html')
    else :
        return render_template('login.html')
    if username == 'admin':
        cursor.execute("SELECT * FROM accounts")
        data = cursor.fetchall()
        return render_template('admin.html', accounts=data)
    return render_template('confirmation.html', data=user_data, token=token)


@app.route('/home', methods=['GET', 'POST'])
def home():
    token = session.get('jwt_token')
    if not token:
        return redirect(url_for('login'))
    return render_template('home.html')


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    token = session.get('jwt_token')
    if not token:
        return redirect(url_for('login'))

    username = session['user_details']['username']
    if username != 'admin':
        return redirect(url_for('home'))

    cursor.execute("SELECT * FROM accounts")
    data = cursor.fetchall()
    print(data)
    return render_template('admin.html', accounts=data)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    token = session.get('jwt_token')
    
    if not token:
        return redirect(url_for('login'))
    if request.method == 'POST':
        username = session['user_details']['username']
        files = request.files.getlist('files[]')
        for file in files:
            # con=database()
            con=database()
            cursor = con.cursor()
            img = file.read()
            query = "INSERT INTO images (username, image) VALUES (%s, %s)"
            cursor.execute(query, (username, img))
            con.commit()
        return render_template('home.html')
    return render_template('home.html')


@app.route('/preview', methods=['GET', 'POST'])
def getpreview():
    return render_template('preview.html', files=filelister)

@app.route('/login', methods=['GET', 'POST'])
def login():
    token = session.get('jwt_token')
    if token:
        return redirect(url_for('welcome'))
    if(request.method == 'POST'):
        username = request.form.get("name")
        password = request.form.get("password")
        cursor = database().cursor()
        query = f"SELECT * FROM accounts WHERE Username='{username}'"
        cursor.execute(query)
        data = cursor.fetchone()
        print(data)
        print(password)
        print(data[2])
        if data and bcrypt.check_password_hash(data[2], password):
            token = generate_jwt_token(username)
            session['user_details'] = {'username': username}
            if session['user_details']['username'] == admin:
                return redirect(url_for('admin'))
            else:
                return redirect(url_for('welcome'))
        else:
           return render_template('login.html', err = "Invalid username or password")
    return render_template('login.html')

# Update the signup function to generate a new salt for each password
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    token = session.get('jwt_token')
    if token:
        return redirect(url_for('welcome'))
    msg = ''
    if request.method == 'POST':
        username = request.form['name']
        email = request.form['email']
        password = request.form['password']
        # conn=database()
        conn = database()
        cursor = conn.cursor()
        # Check if the username already exists
        cursor.execute("SELECT * FROM accounts WHERE username = %s", (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            msg += "Username already exists. Please choose a different username."
            return render_template('Signup.html', msg=msg)
        
        # Generate a new salt for each password hash operation
        hash_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # Insert the new user if the username is unique
        cursor.execute("INSERT INTO accounts (username, email, password) VALUES (%s, %s, %s)",
                       (username, email, hash_password))
        conn.commit()
        # Fetch the user details after insertion
        cursor.execute("SELECT * FROM accounts WHERE username = %s", (username,))
        data1 = cursor.fetchone()
        user_data = {'username': data1[1], 'email': data1[3], 'password': data1[2]}

        # Generate JWT token for the user information
        token = generate_jwt_token(username)
        return render_template('confirmation.html', data=user_data)  # Pass the parsed data to the template
    session.pop('_flashes', None)
    return render_template('Signup.html')


@app.route('/UploadedImages', methods=['GET', 'POST'])
def DisplayUploadedImages():
    token = session.get('jwt_token')
    if not token:
        return render_template('login.html', err = "Invalid username or password")
    if token:
        username = session['user_details']['username']
        query = f"SELECT image FROM images WHERE username='{username}'"
        cursor.execute(query)
        data = cursor.fetchall()
        image_list = []
        for row in data:
            utf8image = b64encode(row[0]).decode("utf-8")  # Accessing the first column of the row
            image_list.append(utf8image)
        return render_template("uploaded_images.html", image_list=image_list)
# @app.route('/', methods=['GET', 'POST'])

@app.route('/getfiles', methods=['GET', 'POST'])
def Defgetfiles():
    files = request.files.getlist('files')
    namer =  request.form.get('nam')
    duration = request.form.get('dur')
    transition_name = request.form.get('transit')
    resolution = request.form.get('res')
    preview(files, namer, transition_name, duration, resolution)
    return Response("success", 200)

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('jwt_token', None)
    session.pop('user_details', None)
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True, port=5002)
