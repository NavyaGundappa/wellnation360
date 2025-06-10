from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import json
from email.message import EmailMessage
import logging
from datetime import datetime
import smtplib

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wellness.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads/'

db = SQLAlchemy(app)

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    profile_pic = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# PricingPlan Model 
class PricingPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    months = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    # service relationship will be defined in Service model via back_populates

# Service Model
class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50), nullable=False) # Corresponds to 'website' in form
    service_name = db.Column(db.String(100), nullable=False)
    instructor_name = db.Column(db.String(100), nullable=False)
    schedule = db.Column(db.String(100), nullable=False) # Corresponds to 'serviceTime' in form
    image_filename = db.Column(db.String(200)) # Store only the filename
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    plans = db.relationship('PricingPlan', backref='service', lazy='dynamic', cascade="all, delete-orphan")

# Create tables
with app.app_context():
    db.create_all()

# Yogaservice Model
class yogaService(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    instructor = db.Column(db.String(100), nullable=False)
    timing = db.Column(db.String(100), nullable=False)
    image = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    options = db.Column(db.Text, nullable=False)

# Create Database
with app.app_context():
    db.create_all()

# Review Model
class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50), nullable=False)
    reviewer_name = db.Column(db.String(100), nullable=False)
    reviewer_image = db.Column(db.String(200))
    content = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    media_type = db.Column(db.String(20))  # 'image' or 'video'
    media_path = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Gallery Model
class GalleryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    media_type = db.Column(db.String(20), nullable=False)  # 'image' or 'video'
    media_path = db.Column(db.String(200), nullable=False)
    caption = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Create tables
with app.app_context():
    db.create_all()

# Helper function for file upload
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_file(file, service_name=None):
    if not file or file.filename == '':
        return None
        
    if not allowed_file(file.filename):
        return None
        
    try:
        # Get file extension
        ext = file.filename.rsplit('.', 1)[1].lower()
        
        # Create filename based on service name or original filename
        if service_name:
            # Clean the service name for filename use
            clean_name = "".join(c if c.isalnum() else "_" for c in service_name)
            filename = f"{clean_name}.{ext}"
        else:
            filename = secure_filename(file.filename)
            
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        file.save(filepath)
        return filename
    except Exception as e:
        current_app.logger.error(f"Error saving file: {str(e)}")
        return None

# Routes
@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['profile_pic'] = user.profile_pic
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get counts for dashboard
    services_count = Service.query.count()
    reviews_count = Review.query.count()
    gallery_count = GalleryItem.query.count()
    
    return render_template('dashboard.html', 
                         services_count=services_count,
                         reviews_count=reviews_count,
                         gallery_count=gallery_count)

@app.route('/admin/yogaservice', methods=['GET', 'POST'])
def admin_yogaservices():
    if request.method == 'POST':
        action = request.form.get('action', 'add')
        service_id = request.form.get('service_id')
        
        # Handle file upload
        image = request.files.get('image')
        image_url = None
        
        if image and image.filename != '':
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(image_path)
            image_url = f"uploads/{filename}"
        
        # Process pricing options
        options = []
        option_count = int(request.form.get('option_count', 0))
        
        for i in range(option_count):
            option_text = request.form.get(f'option_text_{i}')
            option_value = request.form.get(f'option_value_{i}')
            if option_text and option_value:
                options.append({
                    'text': option_text,
                    'value': option_value
                })
        
        # Convert options to JSON string
        options_json = json.dumps(options)
        
        if action == 'add':
            new_service = yogaService(
                name=request.form['name'],
                instructor=request.form['instructor'],
                timing=request.form['timing'],
                image=image_url or 'default-service.jpg',
                description=request.form.get('description', ''),
                options=options_json
            )
            db.session.add(new_service)
            db.session.commit()
            flash('Service created successfully!', 'success')
            
        elif action == 'edit' and service_id:
            service = yogaService.query.get(service_id)
            if service:
                service.name = request.form['name']
                service.instructor = request.form['instructor']
                service.timing = request.form['timing']
                service.description = request.form.get('description', '')
                service.options = options_json
                
                # Update image only if a new one was uploaded
                if image_url:
                    # Delete old image if it exists and not default
                    if service.image and service.image != 'default-service.jpg':
                        try:
                            old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], service.image.split('/')[-1])
                            if os.path.exists(old_image_path):
                                os.remove(old_image_path)
                        except Exception as e:
                            app.logger.error(f"Error deleting old image: {e}")
                    
                    service.image = image_url
                
                db.session.commit()
                flash('Service updated successfully!', 'success')
            else:
                flash('Service not found!', 'danger')
        
        return redirect(url_for('admin_yogaservices'))
    
    # Fetch all services from database
    services = yogaService.query.all()
    
    # Parse options JSON for each service - FIXED: Handle both string and list
    for service in services:
        # Ensure options are always a list
        if isinstance(service.options, str):
            try:
                service.options = json.loads(service.options)
            except:
                service.options = []
        elif not service.options:
            service.options = []
    
    return render_template('yogaservices.html', services=services)

@app.route('/delete_service/<int:service_id>', methods=['POST'])
def delete_service(service_id):
    service = yogaService.query.get_or_404(service_id)
    
    # Delete associated image if it exists and not the default
    if service.image and service.image != 'default-service.jpg':
        try:
            image_name = service.image.split('/')[-1]
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_name)
            if os.path.exists(image_path):
                os.remove(image_path)
        except Exception as e:
            app.logger.error(f"Error deleting image: {e}")
    
    db.session.delete(service)
    db.session.commit()
    flash('Service deleted successfully!', 'success')
    return redirect(url_for('admin_yogaservices'))

@app.route('/api/yogaservices', methods=['GET'])
def get_yogaservices():
    try:
        # Get query parameters for filtering (optional)
        service_id = request.args.get('id')
        instructor = request.args.get('instructor')
        
        # Base query
        query = yogaService.query
        
        # Apply filters if provided
        if service_id:
            query = query.filter(yogaService.id == service_id)
        if instructor:
            query = query.filter(yogaService.instructor.ilike(f'%{instructor}%'))
        
        # Execute query
        services = query.all()
        
        # Prepare response data
        services_data = []
        for service in services:
            try:
                # Parse options JSON
                options = json.loads(service.options)
            except json.JSONDecodeError:
                options = []
            
            service_data = {
                'id': service.id,
                'name': service.name,
                'instructor': service.instructor,
                'timing': service.timing,
                'image': service.image,
                'description': service.description,
                'pricing_options': options,
                'created_at': service.created_at.isoformat() if hasattr(service, 'created_at') else None
            }
            services_data.append(service_data)
        
        return jsonify({
            'status': 'success',
            'count': len(services_data),
            'services': services_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
        
@app.route('/admin/services', methods=['GET']) # Removed POST from here
def admin_services():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('manage_services.html')

@app.route('/admin/reviews', methods=['GET', 'POST'])
def admin_reviews():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        platform = request.form['platform']
        reviewer_name = request.form['reviewer_name']
        content = request.form['content']
        rating = int(request.form['rating'])
        media_type = request.form['media_type']
        
        # Handle file upload
        media_path = None
        if 'media' in request.files and request.files['media'].filename:
            media_path = save_file(request.files['media'])
        
        # Handle reviewer image
        reviewer_image = save_file(request.files['reviewer_image']) if 'reviewer_image' in request.files else None
        
        new_review = Review(
            platform=platform,
            reviewer_name=reviewer_name,
            reviewer_image=reviewer_image,
            content=content,
            rating=rating,
            media_type=media_type,
            media_path=media_path
        )
        
        db.session.add(new_review)
        db.session.commit()
        flash('Review added successfully!', 'success')
        return redirect(url_for('admin_reviews'))
    
    all_reviews = Review.query.all()
    return render_template('manage_reviews.html', reviews=all_reviews)

@app.route('/delete_review/<int:id>')
def delete_review(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    review = Review.query.get_or_404(id)
    db.session.delete(review)
    db.session.commit()
    flash('Review deleted successfully!', 'success')
    return redirect(url_for('reviews'))

@app.route('/admin/gallery', methods=['GET', 'POST'])
def admin_gallery():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        category = request.form['category']
        media_type = request.form['media_type']
        caption = request.form.get('caption', '')
        
        # Handle multiple file uploads
        media_paths = []
        if 'media' in request.files:
            for file in request.files.getlist('media'):
                if file.filename:
                    filename = save_file(file)
                    if filename:
                        new_item = GalleryItem(
                            category=category,
                            media_type=media_type,
                            media_path=filename,
                            caption=caption
                        )
                        db.session.add(new_item)
        
        db.session.commit()
        flash('Items added to gallery successfully!', 'success')
        return redirect(url_for('admin_gallery'))
    
    # Get gallery items grouped by category
    gallery_items = GalleryItem.query.order_by(GalleryItem.category).all()
    return render_template('manage_gallery.html', gallery_items=gallery_items)

@app.route('/delete_gallery_item/<int:id>')
def delete_gallery_item(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    item = GalleryItem.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('Gallery item deleted successfully!', 'success')
    return redirect(url_for('admin_gallery'))

# Create default admin user if not exists
with app.app_context():
    if not User.query.first():
        hashed_password = generate_password_hash('admin123')
        default_user = User(
            username='admin',
            email='admin@wellness.com',
            password=hashed_password,
            profile_pic=None
        )
        db.session.add(default_user)
        db.session.commit()
        print("Default admin user created - username: admin, password: 123")

#===============================================User End===================================================

os.makedirs(app.instance_path, exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configuration for Email
SMTP_HOST = "smtp.2020@vemanait.edu.in"
SMTP_PORT = 587
SENDER_EMAIL = os.getenv('SENDER_EMAIL')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD') # This MUST be a Gmail App Password
RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL')

@app.route("/base")
def base():
    return render_template("base.html")

@app.route('/glimpse')
def gallery():
    # Get all distinct categories
    distinct_categories = db.session.query(GalleryItem.category).distinct().all()
    
    gallery_data = [] # This will be a list of dictionaries
    
    for category_tuple in distinct_categories:
        category_name_str = category_tuple[0] # Extract category name
        # Get all items for this category
        items_from_db = GalleryItem.query.filter_by(category=category_name_str).all()
        
        category_items_list = [] # This will be a list of item dictionaries
        for item_db in items_from_db:
            category_items_list.append({
                'image_url': url_for('static', filename='uploads/' + item_db.media_path),
                'caption': item_db.caption,
                'media_type': item_db.media_type
            })
        
        # Each dictionary added to gallery_data has a 'name' key and an 'items' key
        gallery_data.append({
            'name': category_name_str.capitalize(),
            'items': category_items_list # The value for 'items' is a list
        })
    
    return render_template('gallery.html', gallery_data=gallery_data)

@app.route('/')
def home():
    return render_template('logo.html')

@app.route("/yogakshema")
def yogakshema():
    return render_template("yogakshema.html")

@app.route('/index') # Changed from /index to /home to match navigation links
def index():
    services_from_db = Service.query.order_by(Service.created_at.desc()).all()
    services_data = []
    for service in services_from_db:
        image_url = None
        if service.image_filename:
            image_url = url_for('static', filename=os.path.join('uploads', service.image_filename))

        # Get plans and find the one with the minimum months for display
        service_plans = service.plans.order_by(PricingPlan.months.asc()).all() # Use .all() with lazy='dynamic'
        plans_list_for_json = []
        display_price_info = "Contact for Pricing"

        if service_plans:
            cheapest_plan = service_plans[0] # Already sorted by months
            display_price_info = f"₹{cheapest_plan.price:.0f} for {cheapest_plan.months} month(s)"
            if cheapest_plan.months == 1:
                 display_price_info = f"₹{cheapest_plan.price:.0f} / month"


            for p in service_plans:
                plans_list_for_json.append({"months": p.months, "price": p.price})

        services_data.append({
            "id": service.id,
            "platform": service.platform,
            "service_name": service.service_name,
            "instructor_name": service.instructor_name,
            "schedule": service.schedule,
            "image_url": image_url, # Use the generated URL
            "plans": plans_list_for_json, # Pass all plans
            "display_price": display_price_info # Pass the formatted price for the card
        })
    return render_template('index.html', services_data=services_data)

@app.route("/dummy")
def dummy():
    return render_template("dummy.html")

@app.route("/meditation")
def meditation():
    return render_template("mindful.html")

@app.route("/diet_modification")
def diet_modification():
    return render_template("diet_modification.html")

@app.route("/gut_health")
def gut_health():
    return render_template("blog.html")

@app.route("/sleep_modification")
def sleep_modification():
    return render_template("sleep.html")

@app.route("/weight_loss")
def weight_loss():
    return render_template("weightloss.html")

@app.route("/Diabetics")
def diabetics():
    return render_template("diabetics.html")

@app.route("/Menopause")
def menopause():
    return render_template("menopause.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/service")
def services():
    return render_template("service.html")

@app.route('/api/services', methods=['GET'])
def get_services():
    services_from_db = Service.query.order_by(Service.created_at.desc()).all()
    services_list = []
    for service_db in services_from_db:
        image_url = None
        if service_db.image_filename:
            # Use forward slashes and proper path joining
            image_path = os.path.join('uploads', service_db.image_filename).replace('\\', '/')
            image_url = url_for('static', filename=image_path, _external=True)
            
        plans_list = [{"months": plan.months, "price": plan.price} for plan in service_db.plans]
        services_list.append({
            "id": service_db.id,
            "website": service_db.platform, # Map 'platform' (DB) to 'website' (JS/HTML)
            "service_name": service_db.service_name,
            "instructor_name": service_db.instructor_name,
            "time": service_db.schedule, # Map 'schedule' (DB) to 'time' (JS/HTML)
            "image_url": image_url,
            "plans": plans_list
        })
    return jsonify(services_list)

@app.route('/add_service', methods=['POST'])
def add_service():
    name = request.form['name']
    instructor = request.form['instructor']
    timing = request.form['timing']
    description = request.form['description']
    
    # Handle image upload
    image = request.files['image']
    if image:
        filename = secure_filename(image.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(image_path)
        image_url = f'uploads/{filename}'
    
    # Process pricing options
    options = []
    for i in range(int(request.form['option_count'])):
        text = request.form[f'option_text_{i}']
        value = request.form[f'option_value_{i}']
        options.append({'text': text, 'value': value})
    
    # Save to database
    new_service = Service(
        name=name,
        instructor=instructor,
        timing=timing,
        image=image_url,
        options=json.dumps(options),
        description=description
    )
    db.session.add(new_service)
    db.session.commit()
    
    return redirect(url_for('admin_services'))

# API route to add a new service
@app.route('/api/service/add', methods=['POST'])
def api_add_service():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    try:
        # Get form data
        platform = request.form.get('website')
        service_name = request.form.get('serviceName')
        instructor_name = request.form.get('instructorName')
        schedule = request.form.get('serviceTime')

        if not all([platform, service_name, instructor_name, schedule]):
            return jsonify({"error": "Missing required fields"}), 400

        # Handle file upload with service name
        image_filename = None
        if 'serviceImage' in request.files:
            file = request.files['serviceImage']
            if file and file.filename:
                image_filename = save_file(file, service_name=service_name)
                if not image_filename:
                    return jsonify({"error": "Invalid image file type"}), 400

        # Rest of your service creation code...
        new_service = Service(
            platform=platform,
            service_name=service_name,
            instructor_name=instructor_name,
            schedule=schedule,
            image_filename=image_filename
        )
        
        db.session.add(new_service)
        db.session.flush()  # To get the new_service.id for plans

        # Handle pricing plans
        months_list = request.form.getlist('months[]')
        prices_list = request.form.getlist('prices[]')

        if len(months_list) != len(prices_list):
            db.session.rollback()
            return jsonify({"error": "Mismatch in number of plan months and prices"}), 400

        for i in range(len(months_list)):
            try:
                months = int(months_list[i])
                price = float(prices_list[i])
                if months < 1 or price < 0:
                    raise ValueError("Invalid plan values")
                plan = PricingPlan(service_id=new_service.id, months=months, price=price)
                db.session.add(plan)
            except ValueError:
                db.session.rollback()
                return jsonify({"error": f"Invalid data for plan {i+1}: Months and prices must be valid numbers."}), 400

        db.session.commit()
        
        # Debug: Print the saved service
        print("Service saved with image:", new_service.image_filename)
        
        return jsonify({
            "message": "Service added successfully!", 
            "service_id": new_service.id,
            "image_saved": image_filename is not None
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding service: {str(e)}")
        return jsonify({"message": f"Error adding service: {str(e)}"}), 500

# API route to update an existing service
@app.route('/api/service/update/<int:service_id>', methods=['POST']) # JS uses POST, could be PUT
def api_update_service(service_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    service = Service.query.get_or_404(service_id)
    try:
        service.platform = request.form.get('website', service.platform)
        service.service_name = request.form.get('serviceName', service.service_name)
        service.instructor_name = request.form.get('instructorName', service.instructor_name)
        service.schedule = request.form.get('serviceTime', service.schedule)

        if 'serviceImage' in request.files and request.files['serviceImage'].filename:
            new_image_filename = save_file(request.files['serviceImage'])
            if new_image_filename: # save_file might return None if extension not allowed
                # Optionally, delete old image file from server
                if service.image_filename and service.image_filename != new_image_filename:
                    old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], service.image_filename)
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                service.image_filename = new_image_filename
            else: # New image provided but was invalid
                 return jsonify({"error": "Invalid image file for update"}), 400


        # Update plans: simpler approach is to delete old and add new
        PricingPlan.query.filter_by(service_id=service.id).delete()

        months_list = request.form.getlist('months[]')
        prices_list = request.form.getlist('prices[]')

        if len(months_list) != len(prices_list):
             db.session.rollback() # Important: rollback changes made above if plans are bad
             return jsonify({"error": "Mismatch in number of plan months and prices for update"}), 400

        for i in range(len(months_list)):
            try:
                months = int(months_list[i])
                price = float(prices_list[i])
                if months < 1 or price < 0:
                    raise ValueError("Invalid plan values for update")
                plan = PricingPlan(service_id=service.id, months=months, price=price)
                db.session.add(plan)
            except ValueError:
                db.session.rollback()
                return jsonify({"error": f"Invalid data for plan {i+1} during update."}), 400

        db.session.commit()
        return jsonify({"message": "Service updated successfully!"}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating service {service_id}: {str(e)}")
        return jsonify({"message": f"Error updating service: {str(e)}"}), 500

# API route to delete a service
@app.route('/api/service/delete/<int:service_id>', methods=['POST']) # JS uses POST, could be DELETE
def api_delete_service(service_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    service = Service.query.get_or_404(service_id)
    try:
        # Optionally, delete image file from server
        if service.image_filename:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], service.image_filename)
            if os.path.exists(image_path):
                os.remove(image_path)
        # Plans will be deleted due to cascade delete on the relationship
        db.session.delete(service)
        db.session.commit()
        return jsonify({"message": "Service deleted successfully!"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting service {service_id}: {str(e)}")
        return jsonify({"message": f"Error deleting service: {str(e)}"}), 500

@app.route('/api/reviews', methods=['GET'])
def get_reviews():
    reviews_from_db = Review.query.order_by(Review.created_at.desc()).all()
    reviews_list = []
    for review_db in reviews_from_db:
        reviewer_image_url = None
        if review_db.reviewer_image:
            image_path = os.path.join('uploads', review_db.reviewer_image).replace('\\', '/')
            reviewer_image_url = url_for('static', filename=image_path, _external=True)
            
        media_url = None
        if review_db.media_path:
            media_path = os.path.join('uploads', review_db.media_path).replace('\\', '/')
            media_url = url_for('static', filename=media_path, _external=True)
            
        reviews_list.append({
            "platform": review_db.platform,  # <--- ADD THIS LINE
            "reviewer_name": review_db.reviewer_name,
            "rating": review_db.rating,
            "content": review_db.content,
            "reviewer_image_url": reviewer_image_url,
            "media_type": review_db.media_type,
            "media_url": media_url
        })
    return jsonify({"reviews": reviews_list})

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route("/contact", methods=["GET"])
def contact_get():
    return render_template("contact.html")

@app.route("/yoga_service", methods=["GET"])
def yoga_service():
    return render_template("yoga_service.html")

@app.route("/book_service", methods=["POST"])
def book_service():
    try:
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        branch = request.form.get('branch', '').strip()
        service = request.form.get('service', '').strip()
        date = request.form.get('date', '').strip()
        time = request.form.get('time', '').strip()
        message = request.form.get('message', '').strip()

        if not all([name, phone, email, branch, service, date, time]):
            return jsonify({
                "error": "Please fill in all required fields."
            }), 400

        if not SENDER_EMAIL or not SENDER_PASSWORD or not RECIPIENT_EMAIL:
            logger.error("Email credentials (SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL) are not set in .env")
            return jsonify({
                "error": "Email sending is not configured. Please contact support."
            }), 500

        msg = EmailMessage()
        msg['Subject'] = f"New Service Booking: {service}"
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECIPIENT_EMAIL

        email_body = f"""
        <html>
            <body>
                <h2>New Service Booking Request</h2>
                <table>
                    <tr><td><strong>Name:</strong></td><td>{name}</td></tr>
                    <tr><td><strong>Phone:</strong></td><td>{phone}</td></tr>
                    <tr><td><strong>Email:</strong></td><td>{email}</td></tr>
                    <tr><td><strong>Branch:</strong></td><td>{branch}</td></tr>
                    <tr><td><strong>Service:</strong></td><td>{service}</td></tr>
                    <tr><td><strong>Preferred Date:</strong></td><td>{date}</td></tr>
                    <tr><td><strong>Preferred Time:</strong></td><td>{time}</td></tr>
                    <tr><td><strong>Message:</strong></td><td>{message or 'No additional message'}</td></tr>
                </table>
            </body>
        </html>
        """
        msg.set_content(email_body)
        msg.add_alternative(email_body, subtype='html')

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)

        return jsonify({
            "detail": "Thank you! Your booking request has been sent. We'll contact you shortly."
        })

    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP Authentication Error - Check SENDER_EMAIL and SENDER_PASSWORD (use App Password for Gmail)")
        return jsonify({
            "error": "Failed to authenticate with email server. Please check credentials or contact support."
        }), 500
    except smtplib.SMTPException as e:
        logger.error(f"SMTP Error sending booking email: {e}")
        return jsonify({
            "error": "Failed to send booking request due to email server issues. Please try again later."
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error sending booking email: {e}")
        return jsonify({
            "error": "An unexpected error occurred. Please try again later."
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)