from flask import Flask, render_template, request, session, redirect, url_for,flash
from logging import FileHandler,WARNING
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import openai
import os
import pandas as pd


openai.api_key = os.environ.get("OPENAI_API_KEY")

app = Flask(__name__)
app.config.from_pyfile('config.py')
app.config['SECRET_KEY'] = 'mysecretkey'
app.debug = True

file_handler = FileHandler('errorlog.txt')
file_handler.setLevel(WARNING)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Statement(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    statement_text = db.Column(db.Text, nullable=False)
    question = db.Column(db.Text,nullable=False)
    ans_style_1 = db.Column(db.Text,nullable=False)
    ans_style_2 = db.Column(db.Text,nullable=False)
    ans_style_3 = db.Column(db.Text,nullable=False)
    ans_style_4 = db.Column(db.Text,nullable=False)
    responses = db.relationship('UserResponse', backref='statement', lazy=True)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), nullable=True, unique=True)
    responses = db.relationship('UserResponse', backref='user', lazy=True)

class UserResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    statement_id = db.Column(db.Integer, db.ForeignKey('statement.id'), nullable=False)
    ans_style_1 = db.Column(db.Text,nullable=False)
    ans_style_2 = db.Column(db.Text,nullable=False)
    ans_style_3 = db.Column(db.Text,nullable=False)
    ans_style_4 = db.Column(db.Text,nullable=False)


@app.route('/', methods=['GET'])
def instruction():

    if request.method == "GET":
        users = User.query.all()
        print(users)
        return render_template('instruction.html', users=users)

@app.route('/survey', methods=['GET', 'POST'])
def survey():

    if request.method == "GET":
    
        user_id = request.args.get('user_name')
        session['user_id'] = user_id

        data = get_statement()

        return render_template("survey.html", data=data)
    
    elif request.method == "POST":
        res = store_response()

        if res == "SUCCESS":
            data = get_statement()
            return render_template("survey.html", data=data)
        else:
            flash("Error saving data!")

@app.route('/done', methods=['GET'])
def done():
    return render_template('done.html')

@app.route('/generate', methods = ['GET','POST'])
def generate_completion():

    if request.method == 'GET':
        return render_template('generate.html')

    if request.method == 'POST':

        system_prompt = request.form.get('system_prompt')
        user_prompt = request.form.get("user_prompt")

        session['system_prompt'] = system_prompt
        session['user_prompt'] = user_prompt

        for i in range(50):
            res = store_generated_text()
            print(res)

        return f'<h1>DONE!</h1>'
                
def store_generated_text():

    prompts = {
            'system_prompt': session['system_prompt'],
            'user_prompt' : session['user_prompt']
        }

        #"You are a tutor who is an expert in C programming and have conceptual understanding on anything about programming. Follow the marker for writing response.
        #Generate a short demo code on the use of any operators in C followed by 1 question about the code and then followed by 4 different styles of short answer for the question.  For example, [DEMO] the statement, [QUESTION] question [ANS_STYLE_1] answer style 1 is a direct explanation ,[ANS_STYLE_2] answer style 2 is example-based, [ANS_STYLE_3] answer style 3 is comparison and contrast ,  [ANS_STYLE_4] answer style 4 could be an analogy or just anything.
        
    response = openai.ChatCompletion.create(
    model='gpt-3.5-turbo',  # Choose the model that suits your needs
    temperature = 0.9,
    max_tokens=1000,  # Set the desired length of the generated text
    n = 1,  # Number of responses to generate
    stop=None,  # Stop generation at a specific token, if desired

    messages=[
            {"role": "system", "content": prompts['system_prompt']},
            {"role": "user", "content": prompts['user_prompt'] }
        ]

    )
    
    res = response.choices[0].message.content.strip()
    split1 = res.split('[QUESTION]')
    a = split1[0].strip('[DEMO]')
    split2 = split1[1].split('[ANS_STYLE_1]')
    q = split2[0]
    split3 = split2[1].split('[ANS_STYLE_2]')
    st1 = split3[0]
    split4 = split3[1].split('[ANS_STYLE_3]')
    st2 = split4[0]
    split5 = split4[1].split('[ANS_STYLE_4]')
    st3 = split5[0]
    st4 = split5[1]

    print("\n")
    print("Statement: ", a)
    print("Question: ", q)
    print("A1: ",st1)
    print("A2: ",st2)
    print("A3: ", st3)
    print("A4: ", st4)

    if len(a) == 0 or len(q)==0 or len(st1)==0 or len(st2)==0 or len(st3)==0 or len(st4)==0 :
        return
    else:
        try :
            response = Statement(statement_text=a, question=q, ans_style_1=st1, ans_style_2=st2, ans_style_3=st3,ans_style_4=st4)
            db.session.add(response)
            db.session.commit()

            return "Stored successfully!"

        except Exception as error:
            return str(error.orig) + " for parameters" + str(error.params)

def store_response():
    data = request.form
    user_id = session['user_id'],
    statement_id = data.get('st_num'),
    ans_style_1 = data.get('style1_btn'),
    ans_style_2 = data.get('style2_btn'),
    ans_style_3 = data.get('style3_btn'),
    ans_style_4 = data.get('style4_btn')

    try :
        response = UserResponse(user_id=user_id, statement_id=statement_id, ans_style_1=ans_style_1, ans_style_2=ans_style_2, ans_style_3=ans_style_3,ans_style_4=ans_style_4)
        db.session.add(response)
        db.session.commit()

        return 'SUCCESS'

    except Exception as error:
        print(str(error.orig) + " for parameters" + str(error.params))
        return -1

def get_statement():
    user_id = session["user_id"]
    user = User.query.get(user_id)

    if not user:
        return None

    unresponded_statements = []

    # Get all statement IDs associated with the user
    statement_ids = [response.statement_id for response in user.responses]

    # Get all statements whose IDs are not in the user's responses
    unresponded_statements = Statement.query.filter(~Statement.id.in_(statement_ids)).all()
    print(len(unresponded_statements))

    if len(unresponded_statements) > 0:
        data_dict = {
            'statement_id' : unresponded_statements[0].id,
            'statement_text' : unresponded_statements[0].statement_text,
            'question' : unresponded_statements[0].question,
            'ans_style_1'  : unresponded_statements[0].ans_style_1,
            'ans_style_2' : unresponded_statements[0].ans_style_2,
            'ans_style_3' : unresponded_statements[0].ans_style_3,
            'ans_style_4' : unresponded_statements[0].ans_style_4
        }
    else:
        data_dict = {
            'statement_id' : '',
            'statement_text' : 'No more statement to be annotated.',
            'question' : 'No more question to be annotated.',
            'ans_style_1'  : '',
            'ans_style_2' : '',
            'ans_style_3' : '',
            'ans_style_4' : ''
        }

  
    return data_dict


if __name__ == '__main__':
    app.run(host='0.0.0.0')
