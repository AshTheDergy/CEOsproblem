from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests

app = Flask(__name__)


# Airtable API setup
AIRTABLE_BASE_ID = 'appxzMiyYY676OwWE'
STUDENT_TABLE = 'Students'  # ? Add this line
COMPANY_TABLE = 'Companies'

AIRTABLE_API_KEY = 'APIKEY'

# Headers for Airtable API request
HEADERS = {
    'Authorization': f'Bearer {AIRTABLE_API_KEY}',
    'Content-Type': 'application/json'
}

def get_companies():
    url = f'https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{COMPANY_TABLE}'
    res = requests.get(url, headers=HEADERS)
    if res.status_code == 200:
        return res.json().get('records', [])
    return []
def get_recommended_internships(limit=5):
    companies = get_companies()
    print("Companies fetched:", len(companies))
    hiring_companies = []
    for c in companies:
        status = c.get('fields', {}).get('Status') or c.get('fields', {}).get('status')
        print(f"Company: {c.get('fields', {}).get('Name')} - Status: {status}")
        if status and status.strip().lower() == 'hiring':
            hiring_companies.append(c)
    print("Hiring companies:", len(hiring_companies))
    return hiring_companies[:limit]


def get_students():
    url = f'https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{STUDENT_TABLE}'
    res = requests.get(url, headers=HEADERS)
    if res.status_code == 200:
        return res.json().get('records', [])
    return []

def create_student(name, email, password, phone):
    url = f'https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{STUDENT_TABLE}'
    data = {
        "fields": {
            "Name": name,
            "Email": email,
            "Password": password,
            "Phone number": phone
        }
    }
    res = requests.post(url, headers=HEADERS, json=data)
    return res.status_code == 200 or res.status_code == 201

def find_student_by_email(email):
    students = get_students()
    email = email.strip().lower()  # normalize input email
    print(email)
    for s in students:
        fields = s.get('fields', {})
        print(fields)
        student_email = fields.get('Email')
        if student_email and student_email.strip().lower() == email:
            return s
    return None


@app.route('/')
def index():
    username = session.get('username')
    recommendations = get_recommended_internships()
    return render_template('index.html', username=username, recommendations=recommendations)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        confirm = request.form['confirm']

        if password != confirm:
            flash("Passwords do not match")
            return redirect(url_for('register'))

        existing = find_student_by_email(email)
        if existing:
            flash("Email already registered")
            return redirect(url_for('register'))

        success = create_student(name, email.lower(), password, phone)
        if success:
            flash("Registration successful! Please log in.")
            return redirect(url_for('login'))
        else:
            flash("Registration failed.")
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        student = find_student_by_email(email)

        if not student:
            flash("Email not found.")
            return redirect(url_for('login'))

        stored_hash = student['fields'].get('Password')
        if stored_hash != password:
            flash("Incorrect password.")
            return redirect(url_for('login'))

        session['username'] = student['fields'].get('Name')
        session['email'] = email
        session['student_id'] = student['id']
        return redirect(url_for('index'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/listings')
def listings():
    username = session.get('username')
    companies = get_companies()  # or your actual function to get all listings

    search = request.args.get('search', '').lower()
    category = request.args.get('category', '')
    min_price = int(request.args.get('min_price', 100))
    max_price = int(request.args.get('max_price', 10000))

    filtered_companies = []

    for company in companies:
        fields = company.get('fields', {})
        name = fields.get('Name', '').lower()
        types = fields.get('Type of work', [])
        salary = fields.get('Base salary', 0)

        try:
            salary_val = int(salary)
        except:
            salary_val = 0

        if search and search not in name:
            continue
        if category and category not in types:
            continue
        if salary_val < min_price or salary_val > max_price:
            continue

        # Add status
        status = fields.get('Status') or fields.get('status') or 'Unknown'
        fields['status'] = status

        # Add location (assuming field is called 'Location')
        location = fields.get('Location', 'Unknown location')
        fields['location'] = location

        filtered_companies.append(company)



    return render_template('listings.html', username=username, companies=filtered_companies)

@app.route('/job/<job_id>')
def job_page(job_id):
    username = session.get('username')
    companies = get_companies()
    company = next((c for c in companies if c['id'] == job_id), None)
    if not company:
        return "Job not found", 404
    fields = company.get('fields', {})
    # Fix missing location or status with default values
    fields['location'] = fields.get('Location', 'Location not specified')
    fields['status'] = fields.get('Status', 'Status unknown')
    return render_template('job.html', username=username, company=company)

@app.route('/profile')
def profile():
    if 'student_id' not in session:
        return redirect(url_for('login'))

    students = get_students()
    student = next((s for s in students if s['id'] == session['student_id']), None)
    if not student:
        return redirect(url_for('logout'))

    fields = student.get('fields', {})

    saved_ids = fields.get('Saved Internships', [])
    companies = get_companies()
    saved_internships = [c for c in companies if c['id'] in saved_ids]

    # Pass username explicitly for your template:
    username = fields.get('Name', 'User')

    # Also pass other info you use in the template, like phone, cv_url, etc.
    phone = fields.get('Phone number')
    cv_url = fields.get('CV')
    if cv_url and isinstance(cv_url, list):
        cv_url = cv_url[0].get('url')
    else:
        cv_url = None  # or whatever field name you use
    description = fields.get('Description')
    education = fields.get('Education')
    profile_picture_url = fields.get('Profile picture')
    if profile_picture_url and isinstance(profile_picture_url, list):
        profile_picture_url = profile_picture_url[0].get('url')
    else:
        profile_picture_url = None

    return render_template(
        'profile.html',
        username=username,
        user=fields,
        saved_internships=saved_internships,
        phone=phone,
        cv_url=cv_url,
        description=description,
        education=education,
        profile_picture_url=profile_picture_url
    )


def upload_file_to_fileio(file):
    res = requests.post('https://file.io', files={'file': file})
    if res.status_code != 200:
        print("Upload failed:", res.text)  # see what happened
        return None
    try:
        data = res.json()
    except Exception as e:
        print("JSON decode failed:", e)
        print("Response text:", res.text)
        return None
    return data.get('link')  # or whatever key you expect


def update_student(student_id, updated_fields):
    url = f'https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{STUDENT_TABLE}/{student_id}'
    data = {
        "fields": updated_fields
    }
    res = requests.patch(url, headers=HEADERS, json=data)
    print(f"PATCH status: {res.status_code}, response: {res.text}")
    return res.status_code in [200, 201]



@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'student_id' not in session:
        flash("Not logged in!")
        return redirect(url_for('login'))

    student_id = session['student_id']
    updated_fields = {}

    # Get form fields
    phone = request.form.get('phone')
    description = request.form.get('description')
    education = request.form.get('education')

    if phone:
        updated_fields['Phone number'] = phone
    if description is not None:
        updated_fields['Description'] = description
    if education is not None:
        updated_fields['Education'] = education

    # Fix: Use 'profile_picture' to match the input field in your HTML
    pic = request.files.get('profile_picture')
    if pic and pic.filename != '':
        pic_url = upload_file_to_fileio(pic)
        if pic_url:
            updated_fields['Profile picture'] = [{"url": pic_url}]
        else:
            flash("Failed to upload profile picture")

    # CV upload (already correct)
    cv = request.files.get('cv')
    if cv and cv.filename != '':
        cv_url = upload_file_to_fileio(cv)
        if cv_url:
            updated_fields['CV'] = [{"url": cv_url}]
        else:
            flash("Failed to upload CV")

    if updated_fields:
        success = update_student(student_id, updated_fields)
        if success:
            flash("Profile updated successfully!")
        else:
            flash("Failed to update profile, try again.")

    return redirect(url_for('profile'))


@app.route('/notifications')
def notis():
	username = session.get('username')
	return render_template('notifications.html', username=username)






if __name__ == '__main__':
    #app.run(host='4.3.2.1', port=4000)
    app.run()