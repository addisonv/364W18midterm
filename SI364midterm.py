###############################
####### SETUP (OVERALL) #######
###############################

#By: Addison Viener 

## Import statements
# Import statements
import os
from flask import Flask, render_template, session, redirect, url_for, flash, request
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, RadioField, IntegerField, ValidationError, SelectField# Note that you may need to import more here! Check out examples that do what you want to figure out what.
from wtforms.validators import Required # Here, too
from flask_sqlalchemy import SQLAlchemy
import requests
import json

## App setup code
app = Flask(__name__)
app.debug = True
app.use_reloader = True

## All app.config values
app.config['SECRET_KEY'] = 'Super hard to guess secret key for SI364 Midterm'
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://localhost/addisonvMidterm"
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

## Statements for db setup (and manager setup if using Manager)
db = SQLAlchemy(app)

######################################
######## HELPER FXNS (If any) ########
######################################

predict_access_token = 'dIxHa7Y9XVQsws6IVbJkKDBjSrVWsn'

##################
##### MODELS #####
##################

class Name(db.Model):
    __tablename__ = "names"
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(64))

    def __repr__(self):
        return "{} (ID: {})".format(self.name, self.id)

class EventType(db.Model):
	__tablename__ = "types"
	id = db.Column(db.Integer, primary_key = True)
	event_type = db.Column(db.String())
	events = db.relationship('Events', backref='EventType')
	
	def __repr__(self):
		return "{} (ID: {})".format(self.event_type, self.id)

class Events(db.Model):
    __tablename__ = "events"
    id = db.Column(db.Integer, primary_key = True)
    event_id = db.Column(db.String())
    title = db.Column(db.String())
    type_ID = db.Column(db.Integer, db.ForeignKey("types.id"))
    location = db.Column(db.String())
    start = db.Column(db.String())
    end = db.Column(db.String())
    
    def __repr__(self):
        return "{} (ID: {})".format(self.title, self.id)

class RandomData(db.Model):
    __tablename__ = "random_data"
    id = db.Column(db.Integer,primary_key=True)
    entry1 = db.Column(db.String())
    entry2 = db.Column(db.String())
    entry3 = db.Column(db.String())

    def __repr__(self):
        return "{} (ID: {})".format(self.entry1, self.id)

###################
###### FORMS ######
###################

class Form1(FlaskForm):
    name = StringField("Please enter your name.", validators=[Required()])
    submit = SubmitField()

class Form2(FlaskForm):
    search = StringField("Keyword to search events by (No special characters)(No Numbers)(One word only)", validators = [Required()]) #no capitals
    radio = RadioField('Pick a location', validators = [Required()], choices=[('Ann Arbor', 'Ann Arbor'), ('Chicago', 'Chicago'), ('New York', 'New York')])
    radius = IntegerField("Enter the radius you wish to search events by (Must be an integer)", validators = [Required()])
    submit = SubmitField()

    def validate_search(form, field):
        data = field.data
        special_characters = "!@#$%^&*()_-+={}[]:;\|',<.>/?`~"
        numbers = "1234567890"
        for x in special_characters:
            if x in data:
                raise ValidationError("Search cannot contain a special character")
        if " " in data:
            raise ValidationError("Search must one word")
        for x in numbers:
            if x in data:
                raise ValidationError("Search cannot contain numbers")

class Form3(FlaskForm):
    enter1 = StringField('Enter Something', validators = [Required()])
    enter2 = StringField('Enter Something', validators = [Required()])
    enter3 = StringField('Enter Something', validators = [Required()])
    submit = SubmitField()

def get_or_create_type(db_session,event_type):
    e_type = db_session.query(EventType).filter_by(event_type=event_type).first()
    if e_type:
        return e_type
    else:
        e_type = EventType(event_type=event_type)
        db_session.add(e_type)
        db_session.commit()
        return e_type

def get_or_create_event(db_session, event_id, title, event_type, location, start, end):
    event = db_session.query(Events).filter_by(event_id=event_id).first()
    if event:
        return event
    else:
        e_type = get_or_create_type(db_session, event_type)
        event = Events(event_id=event_id, title=title, type_ID=e_type.id, location=location, start=start, end=end)
        db_session.add(event)
        db_session.commit()
        return event

def get_or_random_data(db_session, entry1, entry2, entry3):
    data = db_session.query(RandomData).filter_by(entry1=entry1).first()
    if data:
        return data
    else:
        data = RandomData(entry1 = entry1, entry2 = entry2, entry3 = entry3)
        db_session.add(data)
        db_session.commit()
        return data

#######################
###### VIEW FXNS ######
#######################
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/', methods=['GET', 'POST'])
def home():
    form1 = Form1() # User should be able to enter name after name and each one will be saved, even if it's a duplicate! Sends data with GET
    if form1.validate_on_submit():
        name = form1.name.data
        newname = Name(name = name)
        db.session.add(newname)
        db.session.commit() 
        return redirect(url_for('event_search'))
    return render_template('base.html',form = form1)

@app.route('/event_search', methods=['POST', 'GET'])
def event_search():
    form2 = Form2()
    locations = {'Ann Arbor':('42.2808', '-83.7430'), "Chicago":('41.8781', '-87.6298'), "New York":('40.7128', '-74.0060')}
    event_results = {}
    if request.method == 'POST':
        if form2.validate_on_submit():
            keyword = form2.search.data.lower()
            radius = str(form2.radius.data)
            area = form2.radio.data
            location = locations[area]
            latitude = location[0]
            longitude = location[1]
            response = requests.get(url="https://api.predicthq.com/v1/events/?q"+keyword+"&within="+radius+"mi@"+latitude+","+longitude, headers={"Authorization": "Bearer " + predict_access_token})
            response_json = response.text
            data = json.loads(response_json)
            results = data['results']
            event_counter = 0
            for x in results:
                event_counter += 1
                event_id = x['id']
                title = x['title']
                event_type = x['category']
                location = x['location']
                start = x['start']
                end = x['end']
                event_results[event_counter] = [title, event_type, location, start, end]
                get_or_create_event(db.session, event_id, title, event_type, location, start, end)
    len_event_results = len(event_results)
            # for x in event_results:
            #     print(event_results[x])   
    errors = [error for error in form2.errors.values()]
    if len(errors) > 0:
        flash("ERRORS IN FORM SUBMISSION - " + str(errors))
    return render_template('event_search.html', form = form2, len_event_results = len_event_results, event_results = event_results)

@app.route('/view_db_info', methods=['GET', 'POST'])
def view_db_info():
    types = EventType.query.all()
    events = Events.query.all()
    data = RandomData.query.all()
    return render_template('view_db_info.html', types = types, events = events, data = data)

@app.route('/get_from', methods=['POST', 'GET'])
def get_form():
    form = Form3()
    req = request.args
    data = []
    data1 = req.get('enter1')
    data2 = req.get('enter2')
    data3 = req.get('enter3')
    data.append(data1)
    data.append(data2)
    data.append(data3)
    if data1:
        if data2:
            if data3:
                get_or_random_data(db.session, data1, data2, data3)
                return render_template('display_get.html', data = data)
    errors = [error for error in form.errors.values()]
    if len(errors) > 0:
        flash("ERRORS IN FORM SUBMISSION - " + str(errors))
    return render_template('get_form.html', form = form)  

@app.route('/names', methods=['GET', 'POST'])
def all_names():
    names = Name.query.all()
    return render_template('name_example.html',names=names)






## Code to run the application...
if __name__ == "__main__":
    db.create_all()
    app.run(use_reloader = True, debug = True)
# Put the code to do so here!
# NOTE: Make sure you include the code you need to initialize the database structure when you run the application!

