# source myenv/bin/activate

from flask import Flask, render_template, redirect, request, url_for, jsonify, session
import secrets
import firebase_admin
from firebase_admin import credentials, auth, firestore, exceptions
from collections import defaultdict, Counter
from dotenv import load_dotenv
from project.config import Config
import os
import random
from datetime import datetime
import pytz
import jinja2
import pandas as pd
from itertools import combinations
from statistics import mean, stdev, variance

import mysql.connector
from mysql.connector import Error

load_dotenv()  # This loads the environment variables from .env

# UNCOMMENT FOR TESTING
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'monashpassword123',
    'database': 'electronic_voting'
}

def create_connection():
    connection = None
    try:
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            print("Connection to MySQL DB successful")
    except mysql.connector.Error as e:
        print(f"The error '{e}' occurred")
    return connection

# UNCOMMENT FOR TESTING
cred = credentials.Certificate("serviceAccountKey.json")

# COMMENT FOR TESTING
# cred = credentials.Certificate({
#     "type": Config.FIREBASE_TYPE,
#     "project_id": Config.FIREBASE_PROJECT_ID,
#     "private_key_id": Config.FIREBASE_PRIVATE_KEY_ID,
#     "private_key": Config.FIREBASE_PRIVATE_KEY.replace('\\n', '\n'),
#     "client_email": Config.FIREBASE_CLIENT_EMAIL,
#     "client_id": Config.FIREBASE_CLIENT_ID,
#     "auth_uri": Config.FIREBASE_AUTH_URI,
#     "token_uri": Config.FIREBASE_TOKEN_URI,
#     "auth_provider_x509_cert_url": Config.FIREBASE_AUTH_PROVIDER_X509_CERT_URL,
#     "client_x509_cert_url": Config.FIREBASE_CLIENT_X509_CERT_URL
# })

firebase_admin.initialize_app(cred)

db = firestore.client()

application = Flask(__name__, template_folder='project/templates', static_folder='project/static')
# print("PRIVATE_KEY", Config.FIREBASE_PRIVATE_KEY.replace('\\n', '\n'))
# print("SECRET", os.urandom(24))
application.secret_key = os.urandom(24)
# print("application", application.secret_key)

# Define the custom filter
def format_datetime(value, format='%Y-%m-%dT%H:%M'):
    if value is None:
        return ""
    # Check if the value is a string and try to parse it into a datetime object
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            # Handle the case where the string is not in the expected format
            return value
    return value.strftime(format)
# Add the filter to Jinja environment
application.jinja_env.filters['datetime'] = format_datetime

def parse_datetime(date_string):
    try:
        return datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        try:
            return datetime.strptime(date_string, '%d/%m/%y %H:%M')
        except ValueError:
            try:
                return datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S')
            except ValueError:
                return datetime.strptime(date_string, '%Y-%m-%dT%H:%M')

def get_clubs_data():
    connection = create_connection()
    clubs_data = []
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT uni_id, uni_club_name, abbreviation, phone_number, email
                FROM clubs
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            for row in rows:
                clubs_data.append(row)
        except Error as e:
            print(f"The error '{e}' occurred")
        finally:
            cursor.close()
            connection.close()
    return clubs_data

def get_elections_data():
    connection = create_connection()
    elections_data = []
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT uni_id, election_id, election_name, election_description, start_date, end_date, 
                       election_type, randomisation, anonymous, pollview, voterview, info_extra, 
                       status, token, voter_member, candidate_token, candidate_member
                FROM elections_data
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            for row in rows:
                print(row['start_date'])
                print(row['end_date'])
                row['start_date'] = parse_datetime(row['start_date'])
                row['end_date'] = parse_datetime(row['end_date'])
                elections_data.append(row)
        except Error as e:
            print(f"The error '{e}' occurred")
        finally:
            cursor.close()
            connection.close()
    return elections_data

def get_candidates_data():
    connection = create_connection()
    candidates_data = {}
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT ballot_id, election_id, user_id, first_name, last_name, email, faculty, 
                       degree, year, gender, ethnicity, position
                FROM candidates_data
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            for row in rows:
                candidate_id = str(row['ballot_id'])
                candidates_data[candidate_id] = {
                    'ballot_id': row['ballot_id'],
                    'election_id': row['election_id'],
                    'user_id': row['user_id'],
                    'first_name': row['first_name'],
                    'last_name': row['last_name'],
                    'email': row['email'],
                    'faculty': row['faculty'],
                    'degree': row['degree'],
                    'year': row['year'],
                    'gender': row['gender'],
                    'ethnicity': row['ethnicity'],
                    'position': row['position']
                }
        except Error as e:
            print(f"The error '{e}' occurred")
        finally:
            cursor.close()
            connection.close()
    return candidates_data

def get_votes_data():
    connection = create_connection()
    votes_data = []
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)

            query = "SELECT election_id, student_id, ballot_id, rank_id FROM votes_data"
            # print("Executing query:", query)  # Debug print
            cursor.execute(query)
            rows = cursor.fetchall()
            # print("rows")
            # print(rows)
            for row in rows:
                votes_data.append({
                    'election_id': row['election_id'],
                    'student_id': row['student_id'],
                    'ballot_id': row['ballot_id'],
                    'rank': row['rank_id']
                })
        except Error as e:
            print(f"The error '{e}' occurred")
        finally:
            cursor.close()
            connection.close()
    return votes_data

def get_students_data():
    connection = create_connection()
    students_data = []
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)

            query = """
                SELECT election_id, student_id, first_name, last_name, email, faculty, degree, year, gender, ethnicity, time
                FROM students
            """
            # print("Executing query:", query)  # Debug print
            cursor.execute(query)
            rows = cursor.fetchall()
            # print("rows")
            # print(rows)
            for row in rows:
                students_data.append({
                    'election_id': row['election_id'],
                    'student_id': row['student_id'],
                    'first_name': row['first_name'],
                    'last_name': row['last_name'],
                    'email': row['email'],
                    'faculty': row['faculty'],
                    'degree': row['degree'],
                    'year': row['year'],
                    'gender': row['gender'],
                    'ethnicity': row['ethnicity'],
                    'time': row['time']
                })
        except Error as e:
            print(f"The error '{e}' occurred")
        finally:
            cursor.close()
            connection.close()
    return students_data

df = pd.read_excel('./project/static/member_test.xlsx')
members = df['Email'].tolist()
# print(members)

@application.route('/app/analysis')
def analysis():
    # Retrieve user_id from session or similar mechanism
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('home_login'))

    connection = create_connection()
    elections_data = get_elections_data()

    connection = create_connection()
    candidates_data = get_candidates_data()

    connection = create_connection()
    votes_data = get_votes_data()

    # Filter elections where uni_id matches user_id
    user_elections = [election for election in elections_data if election['uni_id'] == user_id]
    user_election_ids = {election['election_id'] for election in user_elections}

    # Filter candidates who are part of the filtered elections
    filtered_candidates = {key: val for key, val in candidates_data.items() if val['election_id'] in user_election_ids}
    filtered_votes = [v for v in votes_data if v['election_id'] in user_election_ids]

    # Election type counters
    type_counts = {'Standard': 0, 'Preferential': 0}
    for e in user_elections:
        if e['election_type'] == 'Standard':
            type_counts['Standard'] += 1
        elif e['election_type'] == 'Preferential':
            type_counts['Preferential'] += 1
    print(type_counts)

    # Calculating averages
    vote_counts = [len([v for v in filtered_votes if v['election_id'] == eid]) for eid in user_election_ids]
    vote_counts = [count / 4 if count != 0 else 0 for count in vote_counts]
    candidate_counts = [len([c for c in filtered_candidates.values() if c['election_id'] == eid]) for eid in user_election_ids]
    average_votes = mean(vote_counts) if vote_counts else 0
    average_candidates = mean(candidate_counts) if candidate_counts else 0

    # Min, Max, Standard Deviation, and Variance of votes
    min_votes = min(vote_counts, default=0)
    print("min_votes: "+str(min_votes))
    max_votes = max(vote_counts, default=0)
    print("max_votes: "+str(max_votes))
    std_dev_votes = stdev(vote_counts) if len(vote_counts) > 1 else 0
    print("std_dev_votes: "+str(std_dev_votes))
    variance_votes = variance(vote_counts) if len(vote_counts) > 1 else 0
    print("variance_votes: "+str(variance_votes))

    # Min and Max Candidates
    min_candidates = min(candidate_counts, default=0)
    print("min_candidates: "+str(min_candidates))
    max_candidates = max(candidate_counts, default=0)
    print("max_candidates: "+str(max_candidates))

    # Aggregate data for candidates
    gender_count = {'male': 0, 'female': 0}
    degree_count = {}
    ethnicity_count = {}
    position_count = {}
    election_candidates = {eid: 0 for eid in user_election_ids}

    # filter candidate_data based on the user_id I guess

    for candidate in filtered_candidates.values():
        # Count by gender
        if candidate['gender'] == 'M':
            gender_count['male'] += 1
        else:
            gender_count['female'] += 1

        # Count by degree
        degree = candidate['degree']
        if degree in degree_count:
            degree_count[degree] += 1
        else:
            degree_count[degree] = 1

        # Count by ethnicity
        ethnicity = candidate['ethnicity']
        if ethnicity in ethnicity_count:
            ethnicity_count[ethnicity] += 1
        else:
            ethnicity_count[ethnicity] = 1

        # Count by position
        position = candidate['position']
        if position in position_count:
            position_count[position] += 1
        else:
            position_count[position] = 1

        # Count candidates per election
        election_id = candidate['election_id']
        if election_id in election_candidates:
            election_candidates[election_id] += 1
        else:
            election_candidates[election_id] = 1

    connection = create_connection()
    students = get_students_data()

    # Filter and aggregate students
    filtered_students = [s for s in students if s['election_id'] in user_election_ids]
    student_gender_count = {'male': 0, 'female': 0}
    student_degree_count = {}
    student_ethnicity_count = {}
    student_position_count = {}
    student_election_candidates = {eid: 0 for eid in user_election_ids}

    for student in filtered_students:
        gender = 'male' if student['gender'] == 'Male' else 'female'
        student_gender_count[gender] += 1

        # Count by degree
        degree = student['degree']
        if degree in student_degree_count:
            student_degree_count[degree] += 1
        else:
            student_degree_count[degree] = 1

        # Count by ethnicity
        ethnicity = student['ethnicity']
        if ethnicity in student_ethnicity_count:
            student_ethnicity_count[ethnicity] += 1
        else:
            student_ethnicity_count[ethnicity] = 1

        # Count candidates per election
        election_id = student['election_id']
        if election_id in student_election_candidates:
            student_election_candidates[election_id] += 1
        else:
            student_election_candidates[election_id] = 1

    return render_template('dashboard_analysis.html',
                           gender_count=gender_count,
                           gender_data=[{'gender': 'Male', 'count': gender_count['male']}, {'gender': 'Female', 'count': gender_count['female']}],
                           degree_count=degree_count,
                           ethnicity_count=ethnicity_count,
                           position_count=position_count,
                           election_candidates=election_candidates,
                           student_gender_count=student_gender_count,
                           student_degree_count=student_degree_count,
                           student_ethnicity_count=student_ethnicity_count,
                           student_election_candidates=student_election_candidates,
                           average_votes=average_votes,
                           average_candidates=average_candidates,
                           type_counts=type_counts,
                           min_votes=min_votes,
                           max_votes=max_votes,
                           std_dev_votes=std_dev_votes,
                           variance_votes=variance_votes,
                           min_candidates=min_candidates,
                           max_candidates=max_candidates,
                           preferential_votes=type_counts['Preferential'],
                           standard_votes=type_counts['Standard'],
                           )

@application.route('/about')
def about():
    return render_template('home_page_about.html')

@application.route('/contact')
def contact():
    return render_template('home_page_contact.html')

@application.route('/app/settings')
def settings():
    print(session)
    if 'user_id' not in session:
        # Redirect to login page if the user is not logged in
        return redirect(url_for('home_login'))
    user = auth.get_user(session['user_id'])
    print(user.email)

    connection = create_connection()
    clubs = None
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT uni_club_name, phone_number, email
                FROM clubs 
                WHERE email = %s
            """
            cursor.execute(query, (user.email,))
            clubs = cursor.fetchone()
        except Error as e:
            print(f"The error '{e}' occurred")
        finally:
            cursor.close()
            connection.close()
    clubs = [clubs]
    print(clubs)

    name = None
    phone_number = None
    for club in clubs:
        print(club)
        if club['email'] == user.email:
            name = club['uni_club_name']
            phone_number = club['phone_number']

    return render_template('dashboard_settings.html', email=user.email, name=name, phone_number=phone_number)

@application.route('/update_user_info', methods=['POST'])
def update_user_info():
    data = request.json
    field = data.get('field')
    value = data.get('value')
    user_email = data.get('email')
    print(f"Updating {field} to {value} for email {user_email}")

    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor()
            query = f"UPDATE clubs SET {field} = %s WHERE email = %s"
            cursor.execute(query, (value, user_email))
            connection.commit()

            if cursor.rowcount > 0:
                return jsonify({'message': 'Updated successfully'}), 200
            else:
                return jsonify({'error': 'User not found'}), 404
        except Error as e:
            print(f"The error '{e}' occurred")
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()
            connection.close()
    else:
        return jsonify({'error': 'Database connection failed'}), 500


# Home page
@application.route("/app")
def home_app():
    if 'user_id' not in session:
        # Redirect to login page if the user is not logged in
        return redirect(url_for('home_login'))

    # print(elections_data)

    connection = create_connection()
    elections_data = get_elections_data()

    # Filter the elections data to include only those with matching 'uni_id'
    filtered_elections = [
        election for election in elections_data
        if election.get('uni_id') == session['user_id']
    ]

    print(session)

    return render_template("dashboard.html", elections=filtered_elections)


@application.route('/app/create_election', methods=['GET', 'POST'])
def create_election():
    if 'user_id' not in session:
        # Redirect to login page if the user is not logged in
        return redirect(url_for('home_login'))

    connection = create_connection()
    elections_data = get_elections_data()

    if request.method == 'POST':
        # Extract checkbox values with default as '0' if unchecked
        data = {
            'uni_id': session['user_id'],
            'election_id': len(elections_data) + 1,  # Simple way to generate unique IDs
            'election_name': request.form['election_name'],
            'election_description': request.form['election_description'],
            'start_date': datetime.strptime(request.form['start_date'], '%Y-%m-%dT%H:%M'),
            'end_date': datetime.strptime(request.form['end_date'], '%Y-%m-%dT%H:%M'),
            'election_type': request.form['election_type'],
            'randomisation': int(request.form.get('randomisation', 0)),
            'anonymous': int(request.form.get('anonymous', 0)),
            'pollview': int(request.form.get('pollview', 0)),
            'voterview': int(request.form.get('voterview', 0)),
            'info_extra': int(request.form.get('info_extra', 0)),
            'status': request.form['status'],
            'token': '',
            'candidate_token': ''
        }

        connection = create_connection()
        if connection:
            try:
                cursor = connection.cursor()
                query = """
                    INSERT INTO elections_data (uni_id, election_id, election_name, election_description, start_date, end_date, 
                                           election_type, randomisation, anonymous, pollview, voterview, 
                                           info_extra, status, token, candidate_token)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query, (
                    data['uni_id'], data['election_id'], data['election_name'], data['election_description'], 
                    data['start_date'].strftime('%Y-%m-%d %H:%M:%S'), data['end_date'].strftime('%Y-%m-%d %H:%M:%S'), 
                    data['election_type'], data['randomisation'], data['anonymous'], 
                    data['pollview'], data['voterview'], data['info_extra'], data['status'], 
                    data['token'], data['candidate_token']
                ))
                connection.commit()
            except Error as e:
                print(f"The error '{e}' occurred")
            finally:
                cursor.close()
                connection.close()

        return redirect(url_for('home'))  # Redirect to dashboard after submission

    return render_template('dashboard_election.html')

@application.route("/")
def home():
    return render_template('home_page.html')

@application.route('/verifyToken', methods=['POST'])
def verify_token():
    try:
        id_token = request.json['token']
        token = request.json.get("token")
        print("id_token: "+str(id_token))
        print("token: "+str(token))
        email = request.json['email']
        print("FIREBASE_PROJECT_ID: " + str(Config.FIREBASE_PROJECT_ID))
        decoded_token = auth.verify_id_token(id_token, check_revoked=True)
        print("decoded_token: "+str(decoded_token))
        session['user_id'] = decoded_token['uid']
        session['email'] = email
        return jsonify({'status': 'success', 'uid': decoded_token['uid']})
    except auth.RevokedIdTokenError:
        # Token has been revoked. Inform the user to reauthenticate or signout.
        print("Token revoked")
        return jsonify({'status': 'token_revoked'}), 401
    except auth.InvalidIdTokenError:
        # Token is invalid
        print("Invalid token")
        return jsonify({'status': 'invalid_token'}), 401
    except Exception as e:
        print("Unexpected error: " + str(e))
        return jsonify({'status': 'error', 'message': str(e)}), 500

@application.route('/home_logout')
def home_logout():
    # Here you would clear any session variables
    print("signing out...")
    session.pop('user_id', None)  # Assuming 'user_id' is used to track sessions
    session.pop('email', None)
    # Also clear other related session data if necessary
    return redirect('/')  # Redirect to home or login page after logout

@application.route("/home_login", methods=['GET', 'POST'])
def home_login():
    if 'user_id' in session:
        return render_template('home_page.html')
        # Redirect to login page if the user is not logged in
    return render_template('login.html')

# # Home page
@application.route("/election/<int:election_id>/")
def election(election_id):

    if 'user_id' not in session:
        return render_template('home_page.html')

    connection = create_connection()
    elections_data = get_elections_data()

    connection = create_connection()
    votes_data = get_votes_data()
    print(votes_data)

    filtered_votes = [vote for vote in votes_data if vote['election_id'] == election_id]

    # Count unique student IDs to get the number of voters
    voters_count = len(set(vote['student_id'] for vote in filtered_votes))

    connection = create_connection()
    candidates_data = get_candidates_data()

    connection = create_connection()
    clubs = get_clubs_data()
    print(clubs)

    email = session.get('email')
    print("email: "+str(email))

    club_name = None
    for club in clubs:
        if club['email'] == email:
            club_name = club['uni_club_name']
    print("club_name: "+str(club_name))

    # print(candidates_data)

    # Count the number of candidates in the election
    ballot_questions_count = len([candidate for candidate_id, candidate in candidates_data.items() if candidate['election_id'] == election_id])

    # Filter candidates based on election_id and extract unique positions
    positions = set(candidate['position'] for candidate_id, candidate in candidates_data.items() if candidate['election_id'] == election_id)
    options_count = len(positions)

    # Fetch and prepare election data (assuming it is also in a list or dict)
    election_data = next((item for item in elections_data if item['election_id'] == election_id), None)

    token = election_data['token']
    candidate_token = election_data['candidate_token']

    return render_template("home.html",
                           club_name=club_name,
                           election_id=election_id,
                           election_data=election_data,
                           active_page="home",
                           voters_count=voters_count,
                           ballot_questions_count=ballot_questions_count,
                           options_count=options_count,
                           token=token,
                           candidate_token=candidate_token
                        )

@application.route('/data', methods=['GET'])
def get_data():
    x_feature = request.args.get('x').lower()  # Get the x-axis feature from query params
    y_feature = request.args.get('y').lower()  # Get the y-axis feature from query params
    election_id = request.args.get('election_id')

    connection = create_connection()
    candidates_data = get_candidates_data()

    connection = create_connection()
    votes_data = get_votes_data()

    connection = create_connection()
    students = get_students_data()

    filtered_students = [student for student in students if student['election_id'] == int(election_id)]
    filtered_votes = [vote for vote in votes_data if vote['election_id'] == int(election_id)]
    filtered_candidates = {k: v for k, v in candidates_data.items() if v['election_id'] == int(election_id)}

    if x_feature != y_feature:

        # print(x_feature)
        # print(y_feature)

        # Convert your datasets into pandas DataFrames
        candidates_df = pd.DataFrame.from_dict(filtered_candidates, orient='index')
        votes_df = pd.DataFrame(filtered_votes)
        print(votes_df)
        students_df = pd.DataFrame(filtered_students)
        print(students_df)

        # Ensure that 'student_id' is an integer in both DataFrames
        votes_df['student_id'] = votes_df['student_id']
        students_df['student_id'] = students_df['student_id']

        # Merge the students dataframe with the votes dataframe on 'student_id'
        merged_df = pd.merge(votes_df, students_df, on='student_id', how='inner')
        print(merged_df)

        # Group by the x_feature and count the number of votes for each category
        grouped = merged_df.groupby([x_feature, y_feature]).size().reset_index(name='votes')
        print(grouped)

        grouped['votes'] = grouped['votes'] / 4

        # Pivot the grouped data to have x_feature as index, y_feature as columns, and votes as values
        pivot_table = grouped.pivot_table(index=x_feature, columns=y_feature, values='votes', fill_value=0)
        # print(pivot_table)

        # Convert the pivot table to a format suitable for the frontend chart plotting library
        # The chart expects labels (for the x-axis) and datasets (for the y-axis values of each group)
        chart_data = {
            'labels': pivot_table.index.tolist(),
            'datasets': []
        }

        for column in pivot_table.columns:
            chart_data['datasets'].append({
                'label': column,
                'data': pivot_table[column].tolist()
            })
        # print(chart_data)

        # Return the data in JSON format
        print("jsonify(chart_data)")
        print(jsonify(chart_data))
        return jsonify(chart_data)
    else:
        return ""

@application.route('/table_data', methods=['GET'])
def get_table_data():
    election_id = request.args.get('election_id')

    connection = create_connection()
    candidates_data = get_candidates_data()

    connection = create_connection()
    votes_data = get_votes_data()

    connection = create_connection()
    students = get_students_data()

    filtered_students = [student for student in students if student['election_id'] == int(election_id)]
    filtered_votes = [vote for vote in votes_data if vote['election_id'] == int(election_id)]
    filtered_candidates = {k: v for k, v in candidates_data.items() if v['election_id'] == int(election_id)}

    candidates_df = pd.DataFrame(filtered_candidates).T  # Transpose to match the expected structure
    votes_df = pd.DataFrame(filtered_votes)
    students_df = pd.DataFrame(filtered_students)

    # Merge the dataframes
    merged_df = pd.merge(votes_df, students_df, on='student_id', how='inner')

    # Features to iterate over
    features = ['ethnicity', 'gender', 'degree', 'faculty', 'year']

    # Container for all results
    all_combinations = []

    # Iterate over all unique pair combinations of features
    for x_feature, y_feature in combinations(features, 2):
        grouped = merged_df.groupby([x_feature, y_feature]).size().reset_index(name='votes')
        grouped['feature_x'] = x_feature
        grouped['feature_y'] = y_feature
        all_combinations.append(grouped)

    # Concatenate all groups into a single DataFrame
    result_df = pd.concat(all_combinations)

    # Adjust votes calculation if necessary
    result_df['votes'] = result_df['votes'] / 4

    # Fill NaN values with None for JSON serialization
    result_df = result_df.where(pd.notnull(result_df), None)

    # Convert to dictionary and replace NaN values
    result_dict = result_df.to_dict(orient='records')
    for record in result_dict:
        for key, value in record.items():
            if pd.isna(value):
                record[key] = None

    # Sort by votes to find the highest counts
    sorted_results = sorted(result_dict, key=lambda x: x['votes'], reverse=True)[:10]
    # print(sorted_results)

    # Return JSON response
    return jsonify(sorted_results)

@application.route('/candidate_submit', methods=['POST'])
def candidate_submit(): # ADDING NEW CANDIDATE THROUGH THE EOI FORM
    # print(request.form)

    connection = create_connection()
    elections_data = get_elections_data()

    # Extract data from the form
    first_name = request.form.get('student_first_name')
    last_name = request.form.get('student_last_name')
    email = request.form.get('student_email')
    faculty = request.form.get('faculty')
    degree = request.form.get('degree')
    year = request.form.get('year')
    gender = request.form.get('gender')
    ethnicity = request.form.get('ethnicity')
    position = request.form.get('position')
    token = request.form.get('token')
    # election_id = request.form.get('election_id')
    # position = request.form.get('position')
    # print("election_id: "+str(election_id))

    # Find the election_id based on the token
    election = next((e for e in elections_data if e['candidate_token'] == token), None)
    if not election:
        return "Invalid or expired link", 404

    election_id = election['election_id']

    # election_id = 1  # Assuming a single election; adjust as necessary

    connection = create_connection()
    if connection:
        try:
            candidates_data = get_candidates_data()
            max_ballot_id = len(candidates_data)
            max_ballot_id += 1

            user_id = session.get('user_id')

            # Create a new candidate entry
            new_candidate = {
                'ballot_id': max_ballot_id,
                'user_id': user_id,
                'election_id': election_id,
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'faculty': faculty,
                'degree': degree,
                'year': year,
                'gender': gender,
                'ethnicity': ethnicity,
                'position': position
            }

            cursor = connection.cursor()
            query = """
                INSERT INTO candidates_data (ballot_id, election_id, user_id, first_name, last_name, email, faculty, 
                                        degree, year, gender, ethnicity, position)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (
                new_candidate['ballot_id'], new_candidate['election_id'], new_candidate['user_id'], 
                new_candidate['first_name'], new_candidate['last_name'], new_candidate['email'], 
                new_candidate['faculty'], new_candidate['degree'], new_candidate['year'], 
                new_candidate['gender'], new_candidate['ethnicity'], new_candidate['position']
            ))
            connection.commit()

            return "Thank you for submitting your interest into our executive position"
        except Error as e:
            print(f"The error '{e}' occurred")
            return "Error: Could not submit candidate data.", 500
        finally:
            cursor.close()
            connection.close()
    else:
        return "Error: Could not connect to database.", 500

@application.route("/remove_all_votes", methods=["POST"])
def remove_all_votes():
    data = request.get_json()  # Get data from JSON body
    election_id = data.get('election_id')  # Retrieve the election_id from the body

    if not election_id:
        return jsonify({'error': 'Election ID is required.'}), 400

    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor()
            
            # Delete votes from the votes_data table
            delete_votes_query = "DELETE FROM votes_data WHERE election_id = %s"
            cursor.execute(delete_votes_query, (election_id,))
            
            # Delete students related to the election_id from the students table
            delete_students_query = "DELETE FROM students WHERE election_id = %s"
            cursor.execute(delete_students_query, (election_id,))
            
            connection.commit()

            return jsonify({'message': 'All votes removed for election ID {}'.format(election_id)}), 200
        except Error as e:
            print(f"The error '{e}' occurred")
            return jsonify({'error': 'Failed to remove votes due to an internal error.'}), 500
        finally:
            cursor.close()
            connection.close()
    else:
        return jsonify({'error': 'Failed to connect to the database.'}), 500

@application.route("/invalidate_token", methods=["POST"])
def invalidate_token():
    data = request.get_json()
    election_id = data.get('election_id')

    if not election_id:
        return jsonify({'error': 'Election ID is required.'}), 400

    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor()
            query = "UPDATE elections_data SET token = '' WHERE election_id = %s"
            cursor.execute(query, (election_id,))
            connection.commit()

            if cursor.rowcount > 0:
                return jsonify({'message': 'Token invalidated successfully.'}), 200
            else:
                return jsonify({'error': 'Election ID not found or no token to invalidate.'}), 404
        except Error as e:
            print(f"The error '{e}' occurred")
            return jsonify({'error': 'Failed to invalidate token.'}), 500
        finally:
            cursor.close()
            connection.close()
    else:
        return jsonify({'error': 'Database connection failed.'}), 500

@application.route("/invalidate_candidate_token", methods=["POST"])
def invalidate_candidate_token():
    data = request.get_json()
    election_id = data.get('election_id')

    if not election_id:
        return jsonify({'error': 'Election ID is required.'}), 400

    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor()
            query = "UPDATE elections_data SET candidate_token = '' WHERE election_id = %s"
            cursor.execute(query, (election_id,))
            connection.commit()

            if cursor.rowcount > 0:
                return jsonify({'message': 'Candidate token invalidated successfully.'}), 200
            else:
                return jsonify({'error': 'Election ID not found or no candidate token to invalidate.'}), 404
        except Error as e:
            print(f"The error '{e}' occurred")
            return jsonify({'error': 'Failed to invalidate candidate token.'}), 500
        finally:
            cursor.close()
            connection.close()
    else:
        return jsonify({'error': 'Database connection failed.'}), 500


@application.route("/update_election_data", methods=["POST"])
def update_election_data():
    data = request.json
    field = data.get('field')
    value = data.get('value')
    election_id = data.get('election_id')

    # Convert `election_id` from string to integer if necessary
    election_id = int(election_id)

    # Convert value to integer if it is supposed to be a boolean field
    if value in ['0', '1']:
        value = int(value)

    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor()
            query = f"UPDATE elections_data SET {field} = %s WHERE election_id = %s"
            cursor.execute(query, (value, election_id))
            connection.commit()
            return jsonify({'message': 'Data updated successfully.'}), 200
        except Error as e:
            print(f"The error '{e}' occurred")
            return jsonify({'error': 'Failed to update data.'}), 500
        finally:
            cursor.close()
            connection.close()
    else:
        return jsonify({'error': 'Database connection failed.'}), 500

# Subjects page
@application.route("/election/<int:election_id>/ballots/", methods=["GET", "POST"])
def ballots(election_id):

    position_groups = defaultdict(list)
    traits = defaultdict(lambda: defaultdict(list))

    connection = create_connection()
    candidates_data = get_candidates_data()

    filtered_candidates = {key: candidate for key, candidate in candidates_data.items() if candidate['election_id'] == election_id}
    print(filtered_candidates)

    for candidate in filtered_candidates.values():
        position_groups[candidate['position']].append(candidate)
        traits['faculty'][candidate['faculty']].append(candidate)
        traits['degree'][candidate['degree']].append(candidate)
        traits['year'][candidate['year']].append(candidate)
        traits['gender'][candidate['gender']].append(candidate)
        traits['ethnicity'][candidate['ethnicity']].append(candidate)

    # Sorting within each position group by ballot_id
    for position in position_groups:
        position_groups[position].sort(key=lambda x: x['ballot_id'])

    # Counting entries for each trait
    for trait, groups in traits.items():
        for key, candidates in groups.items():
            traits[trait][key] = len(candidates)

    return render_template("ballots.html", active_page="ballots", position_groups=position_groups, traits=traits)


@application.route("/election/<int:election_id>/polls")
def visuals(election_id):
    # Organize candidates by position
    candidates_by_position = defaultdict(list)

    connection = create_connection()
    candidates_data = get_candidates_data()

    connection = create_connection()
    votes_data = get_votes_data()

    # print("election_id: "+str(election_id))
    filtered_candidates = {key: value for key, value in candidates_data.items() if value['election_id'] == int(election_id)}
    # print(filtered_candidates)

    for cid, details in filtered_candidates.items():
        candidates_by_position[details['position']].append(details)

    filtered_votes = [vote for vote in votes_data if vote['election_id'] == election_id]

    # Count votes for each candidate
    vote_counts = Counter((vote['ballot_id'] for vote in filtered_votes))

    # Aggregate votes by position
    results_by_position = defaultdict(list)
    for position, candidates in candidates_by_position.items():
        for candidate in candidates:
            # Append a tuple of candidate name and vote count
            results_by_position[position].append(
                (f"{candidate['first_name']} {candidate['last_name']}", vote_counts[candidate['ballot_id']])
            )

    # Sort each list of candidates by vote count in descending order
    for position in results_by_position:
        results_by_position[position].sort(key=lambda x: x[1], reverse=True)

    return render_template("visuals.html", active_page="visuals", results_by_position=results_by_position)


@application.route("/election/<int:election_id>/ballots/candidate")
def candidate(election_id):
    print("election_id"+str(election_id))
    # subjects_data = fetch_subjects_data()
    # unit_code = request.args.get("unit_code")
    # print(unit_code)
    # subject = None

    # Iterate through each year's subjects to find the matching unit code
    # for year in subjects_data.values():
    #     if unit_code in year:
    #         subject = year[unit_code]
    #         # print(subject)
    #         break

    return render_template("candidate.html", active_page="candidate", election_id=election_id)

@application.route('/election/<int:election_id>/ballots/candidate/submit_candidate', methods=['POST'])
def submit_candidate(election_id): # ADDING NEW CANDIDATE THROUGH THE ADD BUTTON THROUGH ELECTION DASHBOARD
    connection = create_connection()
    if connection:
        try:
            candidates_data = get_candidates_data()

            # Generate a new ballot_id
            new_id = max(int(k) for k in candidates_data.keys()) + 1

            # Get form data and create a new candidate entry
            candidate = {
                'ballot_id': new_id,
                'election_id': election_id,
                'first_name': request.form['student_first_name'],
                'last_name': request.form['student_last_name'],
                'email': request.form['student_email'],
                'faculty': request.form['faculty'],
                'degree': request.form['degree'],
                'year': int(request.form['year']),
                'gender': request.form['gender'],
                'ethnicity': request.form['ethnicity'],
                'position': request.form['position'],
            }

            cursor = connection.cursor()
            query = """
                INSERT INTO candidates_data (ballot_id, election_id, user_id, first_name, last_name, email, faculty, 
                                        degree, year, gender, ethnicity, position)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (
                candidate['ballot_id'], candidate['election_id'], '', candidate['first_name'], 
                candidate['last_name'], candidate['email'], candidate['faculty'], candidate['degree'], 
                candidate['year'], candidate['gender'], candidate['ethnicity'], candidate['position']
            ))
            connection.commit()

            return redirect(url_for('ballots', ballot_id=new_id, election_id=election_id))
        except Error as e:
            print(f"The error '{e}' occurred")
            return "Error: Could not submit candidate data.", 500
        finally:
            cursor.close()
            connection.close()
    else:
        return "Error: Could not connect to database.", 500

@application.route('/election/<int:election_id>/edit_candidate/<int:ballot_id>', methods=['GET', 'POST'])
def edit_candidate(ballot_id, election_id):
    print(election_id)
    print(ballot_id)

    connection = create_connection()
    candidates_data = get_candidates_data()

    if request.method == 'POST':
        # Extract form data
        candidate_data = {
            'ballot_id': ballot_id,
            'election_id': election_id,  # Assuming the election_id is constant
            'first_name': request.form.get('student_first_name'),
            'last_name': request.form.get('student_last_name'),
            'email': request.form.get('student_email'),
            'faculty': request.form.get('faculty'),
            'degree': request.form.get('degree'),
            'year': int(request.form.get('year')),
            'gender': request.form.get('gender'),
            'ethnicity': request.form.get('ethnicity'),
            'position': request.form.get('position'),
        }
        print(candidate_data)

        if connection:
            try:
                cursor = connection.cursor()
                query = """
                    UPDATE candidates_data
                    SET first_name = %s, last_name = %s, email = %s, faculty = %s, 
                        degree = %s, year = %s, gender = %s, ethnicity = %s, position = %s
                    WHERE ballot_id = %s AND election_id = %s
                """
                cursor.execute(query, (
                    candidate_data['first_name'], candidate_data['last_name'], candidate_data['email'], 
                    candidate_data['faculty'], candidate_data['degree'], candidate_data['year'], 
                    candidate_data['gender'], candidate_data['ethnicity'], candidate_data['position'],
                    ballot_id, election_id
                ))
                connection.commit()
            except Error as e:
                print(f"The error '{e}' occurred")
                return jsonify({'error': str(e)}), 500
            finally:
                cursor.close()
                connection.close()

        # Redirect to the ballots page to see all candidates including the updated one
        return redirect(url_for('ballots', ballot_id=ballot_id, election_id=election_id))
    else:
        # If it's a GET request, display the candidate edit form
        candidate = candidates_data.get(str(ballot_id))
        if candidate:
            return render_template('edit_candidate.html', election_id=election_id, active_page='edit_candidate', candidate=candidate, edit=True)
        else:
            return 'Candidate not found', 404

@application.route("/generate_link", methods=["POST"])
def generate_link():
    data = request.get_json()
    election_id = data.get('election_id')
    print("election_id: "+str(election_id))

    token = secrets.token_urlsafe(16)

    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor()
            query = "UPDATE elections_data SET token = %s WHERE election_id = %s"
            cursor.execute(query, (token, election_id))
            connection.commit()

            election_token_url = url_for('vote', token=token, _external=True)
        except Error as e:
            print(f"The error '{e}' occurred")
            return jsonify({'error': 'Failed to update token.'}), 500
        finally:
            cursor.close()
            connection.close()
    else:
        return jsonify({'error': 'Database connection failed.'}), 500

    return jsonify({'link': election_token_url})

@application.route("/election/<token>")
def vote(token):
    # print("token: "+str(token))

    connection = create_connection()
    elections_data = get_elections_data()

    print(token)
    election = False
    for item in elections_data:
        if item['token'] == token:
            election = item

    print(election)
    # election = next((item for item in elections_data if item['token'] == token), None)

    if election:
        election_id = election['election_id']
        print("election_id: "+str(election_id))

        uni_id = election['uni_id']

        connection = create_connection()
        clubs = get_clubs_data()

        club = next((club for club in clubs if club['uni_id'] == uni_id), None)
        club_name = club['uni_club_name']

        election_name = election['election_name']
        end_date = election['end_date']
        print(end_date)

        session.clear()

        friendly_date_str = end_date.strftime("%dth %B %Y at %-I:%M%p").lower()

        day = end_date.day
        if 4 <= day <= 20 or 24 <= day <= 30:
            suffix = "th"
        else:
            suffix = ["st", "nd", "rd"][day % 10 - 1]

        end_date = friendly_date_str.replace("th", suffix)

        # Check if the user is already authenticated
        if 'authenticated' in session and session['authenticated']:
            # Redirect directly to the ballot page
            return redirect(url_for('vote_ballot', token=token))
        # If not authenticated, show the voting page
        return render_template("vote.html", club_name=club_name, election_name=election_name, end_date=end_date, token=token)
    else:
        return "Invalid or expired link", 404

@application.route("/generate_candidate_link", methods=["POST"])
def generate_candidate_link():
    data = request.get_json()
    election_id = data.get('election_id')
    print("election_id: "+str(election_id))

    token = secrets.token_urlsafe(16)

    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor()
            query = "UPDATE elections_data SET candidate_token = %s WHERE election_id = %s"
            cursor.execute(query, (token, election_id))
            connection.commit()

            election_token_url = url_for('candidate_vote', token=token, _external=True)
        except Error as e:
            print(f"The error '{e}' occurred")
            return jsonify({'error': 'Failed to update candidate token.'}), 500
        finally:
            cursor.close()
            connection.close()
    else:
        return jsonify({'error': 'Database connection failed.'}), 500

    return jsonify({'link': election_token_url})

# @application.route("/generate_candidate_link")
# def generate_candidate_link():
#     global current_candidate_token
#     # Invalidate the previous token
#     if current_candidate_token:
#         current_candidate_token['valid'] = False

#     print(current_candidate_token)

#     # Generate a new token and set it as valid
#     token = secrets.token_urlsafe(16)
#     print(token)

#     current_candidate_token = {'token': token, 'valid': True}
#     print(current_candidate_token)

#     election_data = elections_data[1]
#     # print(elections_data)

#     candidate_url = url_for('candidate_vote', token=token, _external=True)
#     # print(candidate_url)

#     election_data['candidate_token'] = candidate_url

#     print(elections_data)

#     return jsonify({'link': candidate_url})

@application.route("/candidate_vote/<token>")
def candidate_vote(token):

    connection = create_connection()
    elections_data = get_elections_data()

    # Find the election_id based on the token
    election = next((e for e in elections_data if e['candidate_token'] == token), None)
    if not election:
        return "Invalid or expired link", 404

    election_id = election['election_id']
    election_name = election['election_name']
    end_date = election['end_date']

    session.clear()  # Clear the session after voting

    friendly_date_str = end_date.strftime("%dth %B %Y at %-I:%M%p").lower()

    day = end_date.day
    if 4 <= day <= 20 or 24 <= day <= 30:
        suffix = "th"
    else:
        suffix = ["st", "nd", "rd"][day % 10 - 1]

    end_date = friendly_date_str.replace("th", suffix)

    connection = create_connection()
    clubs = get_clubs_data()


    user_id = session.get('user_id')

    uni_id = election['uni_id']
    print(uni_id)

    club = next((club for club in clubs if club['uni_id'] == uni_id), None)
    club_name = club['uni_club_name']

    connection = create_connection()
    candidates_data = get_candidates_data()

    # Check if the user is already authenticated
    if 'authenticated' in session and session['authenticated']:
        # Redirect directly to the ballot page

        already_voted = any(vote['user_id'] == user_id and vote['election_id'] == 1 for vote in candidates_data.values())
        if already_voted:
            session.clear()  # Clear the session immediately if already voted
            return "You have already submitted eoi."

        return render_template("eoi_candidate.html", club_name=club_name, election_name=election_name, end_date=end_date, token=token)
    # If not authenticated, show the voting page
    return render_template("eoi_candidate.html", club_name=club_name, election_name=election_name, end_date=end_date, token=token)

@application.route("/candidate_vote/<token>/form", methods=["GET"])
def candidate_vote_form(token):

    connection = create_connection()
    elections_data = get_elections_data()

    # Find the election_id based on the token
    election = next((e for e in elections_data if e['candidate_token'] == token), None)
    if not election:
        return "Invalid or expired link", 404

    election_name = election['election_name']
    # print("we are in")

    connection = create_connection()
    candidates_data = get_candidates_data()

    # Check if the session indicates the user is authenticated
    print(session.get('authenticated'))

    position_groups = defaultdict(list)

    user_id = session.get('user_id')  # Get the UID from the session
    if user_id is None:
        return "User ID is not available. Please log in again.", 403

    # Check if user already is a candidate in the dataset
    # Check if the user has already voted in this election
    already_voted = any(vote['user_id'] == user_id and vote['election_id'] == 1 for vote in candidates_data.values())
    if already_voted:
        session.clear()  # Clear the session immediately if already voted
        return "You have already submitted eoi."

    for candidate in candidates_data.values():
        position_groups[candidate['position']].append(candidate)

    return render_template('candidate_vote.html', election_name=election_name, token=token)

@application.route("/election/<token>/ballot", methods=["GET"])
def vote_ballot(token):

    connection = create_connection()
    elections_data = get_elections_data()

    connection = create_connection()
    clubs = get_clubs_data()

    election = False
    for item in elections_data:
        if item['token'] == token:
            election = item

    if election == False:
        return "Invalid or expired token", 403

    # election = next((item for item in elections_data if item['token'] == token), None)
    election_id = election['election_id']
    uni_id = election['uni_id']
    # print("election_id: "+str(election_id))

    voting_type = election['election_type']
    # print("voting_type:" +str(voting_type))
    randomize = election['randomisation'] == 1

    election_name = election['election_name']

    club = next((club for club in clubs if club['uni_id'] == uni_id), None)
    club_name = club['uni_club_name']

    # print(session.get('authenticated'))
    # print(current_token.get('token'))
    # print(current_token.get('valid', False))

    # Check if the session indicates the user is authenticated


    if session.get('authenticated'):
        position_groups = defaultdict(list)

        user_id = session.get('user_id')  # Get the UID from the session
        if user_id is None:
            return "User ID is not available. Please log in again.", 403

        # Check if results and voters should be shown
        show_pollview = int(election['pollview']) == 1
        show_voterview = int(election['voterview']) == 1
        anonymous = int(election['anonymous']) == 1

        results_by_position = defaultdict(list)

        connection = create_connection()
        candidates_data = get_candidates_data()

        connection = create_connection()
        votes_data = get_votes_data()

        # Filter candidates for the given election_id
        filtered_candidates = [candidate for candidate in candidates_data.values() if candidate['election_id'] == election_id]
        # print(filtered_candidates)

        # Fetch results and voter list if required
        results = []
        if show_pollview:

            # Filter votes for the given election_id
            votes = [vote for vote in votes_data if vote['election_id'] == election_id]
            # Count votes for each ballot_id
            vote_counts = Counter(vote['ballot_id'] for vote in votes)
            # Fetch candidate names and ballot_ids
            for ballot_id, count in vote_counts.items():
                candidate_info = candidates_data.get(str(ballot_id), {})
                candidate_name = f"{candidate_info.get('first_name', '')} {candidate_info.get('last_name', '')}".strip()
                position = candidate_info.get('position', 'Unknown')
                results_by_position[position].append((candidate_name, count))
                # Sorting each list in the dictionary by vote count in descending order
                for position in results_by_position:
                    results_by_position[position].sort(key=lambda x: x[1], reverse=True)
                results.append({'candidate': candidate_name, 'votes': count, 'position': candidate_info.get('position', 'Unknown')})

        voter_list = []
        if show_voterview:
            connection = create_connection()
            if connection:
                try:
                    cursor = connection.cursor(dictionary=True)
                    query = """
                        SELECT s.email
                        FROM votes_data v
                        JOIN students s ON v.student_id = s.student_id
                        WHERE v.election_id = %s;
                    """
                    cursor.execute(query, (election_id,))
                    rows = cursor.fetchall()
                    voter_list = [{'email': row['email']} for row in rows]
                except Error as e:
                    print(f"The error '{e}' occurred")
                finally:
                    cursor.close()
                    connection.close()

        # Check if the user has already voted in this election
        already_voted = False
        connection = create_connection()
        if connection:
            try:
                cursor = connection.cursor()
                query = """
                    SELECT COUNT(*)
                    FROM votes_data
                    WHERE election_id = %s AND student_id = %s;
                """
                cursor.execute(query, (election_id, user_id))
                result = cursor.fetchone()
                already_voted = result[0] > 0
            except Error as e:
                print(f"The error '{e}' occurred")
            finally:
                cursor.close()
                connection.close()

        if already_voted:
            session.clear()  # Clear the session immediately if already voted
            print("ALREADY VOTED!")
            return render_template('vote_submit.html', active='vote_submit', results_by_position=results_by_position, results=results, voter_list=voter_list, show_pollview=show_pollview, show_voterview=show_voterview, anonymous=anonymous)


        for candidate in filtered_candidates:
            position_groups[candidate['position']].append(candidate)

        # Sort candidates within each position by last name or any other criterion
        for position in position_groups:
            if randomize:
                random.shuffle(position_groups[position])
            else:
                position_groups[position].sort(key=lambda x: x['last_name'])

        # Choose the template based on voting type
        if voting_type == "Standard":
            template_name = "vote_ballot_single.html"
        else:  # Preferential
            template_name = "vote_ballot_multiple.html"

        info_extra = int(election['info_extra'])
        # print("infl_extra: ", info_extra)

        return render_template(template_name, club_name=club_name, election_name=election_name, token=token, info_extra=info_extra, position_groups=position_groups, anonymous=anonymous)
    else:
        # If not authenticated, redirect them to the login page or home page
        return "Not authenticated", 404

@application.route("/election/<token>/ballot/submit_vote", methods=["POST"])
def submit_vote_single(token):
    # print("token: "+str(token))

    connection = create_connection()
    elections_data = get_elections_data()

    connection = create_connection()
    votes_data = get_votes_data()

    # print(elections_data)

    # Find the election using the token
    election_data = next((item for item in elections_data if item['token'] == token), None)
    if not election_data:
        return "Invalid or expired token", 404

    # election = next((item for item in elections_data if item['token'] == token), None)
    election_id = election_data['election_id']
    # print("election_id: "+str(election_id))

    # Check if the user is authenticated and the session is valid
    if 'authenticated' in session:
        user_id = session.get('user_id')  # Get the UID from the session
        email = session.get('email')

        # print("Form data:", request.form)

        connection = create_connection()
        candidates_data = get_candidates_data()

        if not election_data:
            return "Election data not found", 404

        # Check if results and voters should be shown
        show_pollview = int(election_data['pollview']) == 1
        show_voterview = int(election_data['voterview']) == 1
        anonymous = (election_data['anonymous']) == 1

        results_by_position = defaultdict(list)
        results = []
        voter_list = []

        # Check if the user has already voted in this election
        already_voted = False
        connection = create_connection()
        if connection:
            try:
                cursor = connection.cursor()
                query = """
                    SELECT COUNT(*)
                    FROM votes_data
                    WHERE election_id = %s AND student_id = %s;
                """
                cursor.execute(query, (election_id, user_id))
                result = cursor.fetchone()
                already_voted = result[0] > 0
            except Error as e:
                print(f"The error '{e}' occurred")
            finally:
                cursor.close()
                connection.close()

        if not already_voted:
            # Define personal info fields
            personal_info_fields = {'first_name', 'last_name', 'faculty', 'degree', 'year', 'gender', 'ethnicity'}

            # Initialize personal_info with blank fields
            personal_info = {key: "" for key in personal_info_fields}

            # print("personal_info1: "+str(personal_info))

            # Update personal_info with values from request.form if they exist
            personal_info.update({key: request.form[key] for key in personal_info_fields if key in request.form})

            # print("personal_info2: "+str(personal_info))

            # Extract personal information
            # personal_info = {key: request.form[key] for key in personal_info_fields if key in request.form}
            # print("personal_info3: "+str(personal_info))

            personal_info['student_id'] = user_id
            personal_info['year'] = 0
            personal_info['email'] = email
            personal_info['election_id'] = int(election_id)
            tz = pytz.timezone('Australia/Melbourne')
            submission_time = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(tz)
            personal_info['time'] = submission_time
            # print("-------------------")
            # print("personal_info4: "+str(personal_info))
            # print("-------------------")

            # Insert or update the student's personal info in the database
            connection = create_connection()
            cursor = connection.cursor()
            try:
                query = """
                    INSERT INTO students (election_id, student_id, first_name, last_name, email, faculty, degree, year, gender, ethnicity, time)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query, (
                    personal_info['election_id'], personal_info['student_id'], personal_info['first_name'], personal_info['last_name'],
                    personal_info['email'], personal_info['faculty'], personal_info['degree'], personal_info['year'],
                    personal_info['gender'], personal_info['ethnicity'], personal_info['time']
                ))
                connection.commit()
            except Error as e:
                print(f"The error '{e}' occurred")
            finally:
                cursor.close()
                connection.close()

            # Update or append new data
            # students.append(personal_info)
            # print(students)

            # vote_anonymous = {
            #     'election_id': election_id, 
            #     'student_id': user_id,
            #     'email': '' if anonymous == 1 else email
            # }

            # votes_data_anonymous.append(vote_anonymous)
            # print(votes_data_anonymous)

        # Process each vote. Assume the form names are aligned with position ids
            for key, value in request.form.items():
                if key not in personal_info_fields:

                    vote = {
                            'election_id': election_id,
                            'student_id': 0 if anonymous else user_id,
                            'ballot_id': int(value),
                            'rank': 0
                        }
                    # Insert the new vote into the database
                    connection = create_connection()
                    cursor = connection.cursor()
                    try:
                        query = """
                            INSERT INTO votes_data (election_id, student_id, ballot_id, rank_id)
                            VALUES (%s, %s, %s, %s)
                        """
                        cursor.execute(query, (
                            vote['election_id'], vote['student_id'], vote['ballot_id'], vote['rank']
                        ))
                        connection.commit()
                    except Error as e:
                        print(f"The error '{e}' occurred")
                    finally:
                        cursor.close()
                        connection.close()



        # Fetch results and voter list if required
        if show_pollview:

            connection = create_connection()
            votes_data = get_votes_data()

            # Filter votes for the given election_id
            votes = [vote for vote in votes_data if vote['election_id'] == election_id]
            # Count votes for each ballot_id
            vote_counts = Counter(vote['ballot_id'] for vote in votes)
            # Fetch candidate names and ballot_ids
            for ballot_id, count in vote_counts.items():
                candidate_info = candidates_data.get(str(ballot_id), {})
                candidate_name = f"{candidate_info.get('first_name', '')} {candidate_info.get('last_name', '')}".strip()
                position = candidate_info.get('position', 'Unknown')
                results_by_position[position].append((candidate_name, count))
                # Sorting each list in the dictionary by vote count in descending order
                for position in results_by_position:
                    results_by_position[position].sort(key=lambda x: x[1], reverse=True)
                results.append({'candidate': candidate_name, 'votes': count, 'position': candidate_info.get('position', 'Unknown')})

        voter_list = []
        if show_voterview:
            connection = create_connection()
            if connection:
                try:
                    cursor = connection.cursor(dictionary=True)
                    query = """
                        SELECT s.email
                        FROM votes_data v
                        JOIN students s ON v.student_id = s.student_id
                        WHERE v.election_id = %s;
                    """
                    cursor.execute(query, (election_id,))
                    rows = cursor.fetchall()
                    voter_list = [{'email': row['email']} for row in rows]
                except Error as e:
                    print(f"The error '{e}' occurred")
                finally:
                    cursor.close()
                    connection.close()

        if user_id is None:
            return "User ID is not available. Please log in again.", 403

                # Optionally, you can print the new vote or handle other logic
                # print(f"New vote added: {vote}")

        # print(votes_data)

        # session.clear()  # Clear the session immediately if already voted
        return render_template('vote_submit.html', active='vote_submit', results_by_position=results_by_position, results=results, voter_list=voter_list, show_pollview=show_pollview, show_voterview=show_voterview, anonymous=anonymous)
        # return "Thank you for voting!"
    else:
        # If not authenticated, or token is invalid, redirect to the login page
        return redirect(url_for('login'))

@application.route("/election/<token>/ballot/submit_vote/multiple", methods=["POST"])
def submit_vote_multiple(token):
    print("HELLOOOOOOOO")
    connection = create_connection()
    elections_data = get_elections_data()

    connection = create_connection()
    votes_data = get_votes_data()
    print("---------------------------")
    print(votes_data)
    print("---------------------------")

    election = False
    for item in elections_data:
        if item['token'] == token:
            election = item

    if election == False:
        return "Invalid or expired token", 403

    # print(session.get('authenticated'))
    # print(current_token.get('token'))
    # print(current_token.get('valid', False))

    election_id = election['election_id']
    anonymous = election['anonymous']

    # Check if the session indicates the user is authenticated
    if session.get('authenticated'):
        position_groups = defaultdict(list)
        user_id = session.get('user_id')  # Get the UID from the session
        email = session.get('email')


        user_id = session.get('user_id')  # Get the UID from the session
        if user_id is None:
            return "User ID is not available. Please log in again.", 403

        # Check if results and voters should be shown
        show_pollview = int(election['pollview']) == 1
        show_voterview = int(election['voterview']) == 1

        results_by_position = defaultdict(list)
        results = []
        voter_list = []

        connection = create_connection()
        candidates_data = get_candidates_data()

        # Check if the user has already voted in this election
        # Check if the user has already voted in this election
        already_voted = False
        connection = create_connection()
        if connection:
            try:
                cursor = connection.cursor()
                query = """
                    SELECT COUNT(*)
                    FROM votes_data
                    WHERE election_id = %s AND student_id = %s;
                """
                cursor.execute(query, (election_id, user_id))
                result = cursor.fetchone()
                already_voted = result[0] > 0
            except Error as e:
                print(f"The error '{e}' occurred")
            finally:
                cursor.close()
                connection.close()

        if not already_voted:
            # Define personal info fields
            personal_info_fields = {'first_name', 'last_name', 'faculty', 'degree', 'year', 'gender', 'ethnicity'}

            # Initialize personal_info with blank fields
            personal_info = {key: "" for key in personal_info_fields}

            # print("personal_info1: "+str(personal_info))

            # Update personal_info with values from request.form if they exist
            personal_info.update({key: request.form[key] for key in personal_info_fields if key in request.form})

            personal_info['student_id'] = user_id
            personal_info['year'] = 0
            personal_info['email'] = '' if anonymous == 1 else email
            personal_info['election_id'] = int(election_id)
            tz = pytz.timezone('Australia/Melbourne')
            submission_time = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(tz)
            personal_info['time'] = submission_time

            # Insert or update the student's personal info in the database
            connection = create_connection()
            cursor = connection.cursor()
            try:
                query = """
                    INSERT INTO students (election_id, student_id, first_name, last_name, email, faculty, degree, year, gender, ethnicity, time)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query, (
                    personal_info['election_id'], personal_info['student_id'], personal_info['first_name'], personal_info['last_name'],
                    personal_info['email'], personal_info['faculty'], personal_info['degree'], personal_info['year'],
                    personal_info['gender'], personal_info['ethnicity'], personal_info['time']
                ))
                connection.commit()
            except Error as e:
                print(f"The error '{e}' occurred")
            finally:
                cursor.close()
                connection.close()

            # print(students)

            # vote_anonymous = {
            #     'election_id': election_id, 
            #     'student_id': user_id,
            #     'email': email
            # }

            # votes_data_anonymous.append(vote_anonymous)

            for key, value in request.form.items():
                if key not in personal_info_fields:
                    print(f"Received key: {key}, value: {value}")  # Debug print to show received form data
                    position, candidate_id = key.split('_')
                    rank = int(value)
                    print(rank)

                    vote = {
                        'election_id': election_id,
                        'student_id': 0 if anonymous == 1 else user_id,
                        'ballot_id': int(candidate_id),
                        'rank': rank
                    }
                    # print(vote)

                    # Append the new vote to the votes_data list
                    # Insert the new vote into the database
                    connection = create_connection()
                    cursor = connection.cursor()
                    try:
                        query = """
                            INSERT INTO votes_data (election_id, student_id, ballot_id, rank_id)
                            VALUES (%s, %s, %s, %s)
                        """
                        cursor.execute(query, (
                            vote['election_id'], vote['student_id'], vote['ballot_id'], vote['rank']
                        ))
                        connection.commit()
                    except Error as e:
                        print(f"The error '{e}' occurred")
                    finally:
                        cursor.close()
                        connection.close()
                    print(vote)
                    print("--------")


                print("All votes after submission:", len(votes_data))

        # Fetch results and voter list if required
        print("show_pollview: "+str(show_pollview))
        if show_pollview:

            connection = create_connection()
            votes_data = get_votes_data()

            # Filter votes for the given election_id
            votes = [vote for vote in votes_data if vote['election_id'] == election_id]
            print("votes")
            print(votes)
            # Count votes for each ballot_id
            vote_counts = Counter(vote['ballot_id'] for vote in votes)
            print("vote_counts")
            print(vote_counts)
            # Fetch candidate names and ballot_ids
            for ballot_id, count in vote_counts.items():
                candidate_info = candidates_data.get(str(ballot_id), {})
                candidate_name = f"{candidate_info.get('first_name', '')} {candidate_info.get('last_name', '')}".strip()
                position = candidate_info.get('position', 'Unknown')
                results_by_position[position].append((candidate_name, count))
                # Sorting each list in the dictionary by vote count in descending order
                for position in results_by_position:
                    results_by_position[position].sort(key=lambda x: x[1], reverse=True)
                results.append({'candidate': candidate_name, 'votes': count, 'position': candidate_info.get('position', 'Unknown')})

            print(results)

        voter_list = []
        if show_voterview:
            connection = create_connection()
            if connection:
                try:
                    cursor = connection.cursor(dictionary=True)
                    query = """
                        SELECT s.email
                        FROM votes_data v
                        JOIN students s ON v.student_id = s.student_id
                        WHERE v.election_id = %s;
                    """
                    cursor.execute(query, (election_id,))
                    rows = cursor.fetchall()
                    user_emails = {row['email'] for row in rows}  # Use set comprehension to ensure unique emails
                    voter_list = [{'email': email} for email in user_emails]
                except Error as e:
                    print(f"The error '{e}' occurred")
                finally:
                    cursor.close()
                    connection.close()

        # session.clear()  # Clear the session after voting
        # return "Thank you for voting!"
        print("show_pollview: "+str(show_pollview))
        print("show_voterview: "+str(show_voterview))
        print("--------------- results_by_position -------------")
        print(results_by_position)
        print("--------------- results -------------")
        print(results)
        print("--------------- voter_list -------------")
        print(voter_list)
        
        return render_template('vote_submit.html', active='vote_submit', results_by_position=results_by_position, results=results, voter_list=voter_list, show_pollview=show_pollview, show_voterview=show_voterview, anonymous=anonymous)
    else:
        print("Authentication failed or token invalid")  # Debug print for failed auth
        return jsonify({"message": "Invalid credentials"}), 401

@application.route("/election/<int:election_id>/voters")
def voters(election_id):
    print(election_id)
    
    connection = create_connection()
    students = get_students_data()

    # Filter the students who participated in election_id 1
    filtered_students = [student for student in students if student.get('election_id') == int(election_id)]
    print(filtered_students)

    traits = defaultdict(lambda: defaultdict(int))

    for student in filtered_students:
        for key in ['faculty', 'degree', 'year', 'gender', 'ethnicity']:
            traits[key][student[key]] += 1

    return render_template("voters.html", active_page="voters", students=filtered_students, traits=traits)

@application.route("/login_voter", methods=["POST"])
def login_voter():
    token = request.json.get("token")
    token_url = request.json.get("token_url")

    # print("token_url: "+str(token_url))

    try:
        # Verify the Firebase ID token using Firebase Admin SDK
        decoded_token = auth.verify_id_token(token)
        email = decoded_token.get("email")

        # Check if the email belongs to a Monash student
        if not email.endswith("@student.monash.edu"):
            return jsonify({"message": "Access denied. Please sign in with your Monash student email."}), 403

        election = None

        connection = create_connection()
        elections_data = get_elections_data()

        for elections in elections_data:
        # Check if the current election's token matches the given token_value
            if elections['token'] == token_url:
                # Return the election object if the token matches
                election = elections

        print("election['voter_member']: "+str(election['voter_member']))

        if int(election['voter_member']) == 1:
            if email not in members:
                return jsonify({"message": "Access denied. You need to be a member."}), 403

        # User email is valid, so proceed with session creation
        session['user_id'] = decoded_token['uid']
        session['email'] = email
        session['authenticated'] = True  # Indicate the user is authenticated

        # Return a success response
        return jsonify({"message": "Successfully logged in"}), 200

    except auth.InvalidIdTokenError:
        # Handle the case where the token is not valid
        return jsonify({"message": "Invalid ID token"}), 401
    except Exception as e:
        # Handle other exceptions that may occur
        return jsonify({"message": str(e)}), 500

@application.route("/login_candidate", methods=["POST"])
def login_candidate():
    token = request.json.get("token")
    token_url = request.json.get("token_url")

    print("token_url_2: "+str(token_url))

    try:
        # Verify the Firebase ID token using Firebase Admin SDK
        decoded_token = auth.verify_id_token(token)
        email = decoded_token.get("email")

        # Check if the email belongs to a Monash student
        if not email.endswith("@student.monash.edu"):
            return jsonify({"message": "Access denied. Please sign in with your Monash student email."}), 403

        election = None

        connection = create_connection()
        elections_data = get_elections_data()

        for elections in elections_data:
        # Check if the current election's token matches the given token_value
            if elections['candidate_token'] == token_url:
                # Return the election object if the token matches
                election = elections

        print("election['candidate_member']: "+str(election['candidate_member']))

        if int(election['candidate_member']) == 1:
            if email not in members:
                return jsonify({"message": "Access denied. You need to be a member."}), 403

        # User email is valid, so proceed with session creation
        session['user_id'] = decoded_token['uid']
        session['email'] = email
        session['authenticated'] = True  # Indicate the user is authenticated

        # Return a success response
        return jsonify({"message": "Successfully logged in"}), 200

    except auth.InvalidIdTokenError:
        # Handle the case where the token is not valid
        return jsonify({"message": "Invalid ID token"}), 401
    except Exception as e:
        # Handle other exceptions that may occur
        return jsonify({"message": str(e)}), 500

# @application.route("/election/<token>/ballot/submit_vote", methods=["GET"])
# def submit_vote():
#     print("ENTERED")
#     election_data = elections_data[1]
#     if not election_data:
#         return "Election data not found", 404

#     # Check if results and voters should be shown
#     show_pollview = election_data['pollview'] == 1
#     show_voterview = election_data['voterview'] == 1

#     # Fetch results and voter list if required
#     results = []
#     if show_pollview:
#         # Filter votes for the given election_id
#         votes = [vote for vote in votes_data if vote['election_id'] == 1]
#         # Count votes for each ballot_id
#         vote_counts = Counter(vote['ballot_id'] for vote in votes)
#         # Fetch candidate names and ballot_ids
#         for ballot_id, count in vote_counts.items():
#             candidate_info = candidates_data.get(str(ballot_id), {})
#             candidate_name = f"{candidate_info.get('first_name', '')} {candidate_info.get('last_name', '')}".strip()
#             results.append({'candidate': candidate_name, 'votes': count, 'position': candidate_info.get('position', 'Unknown')})

#     voter_list = []
#     if show_voterview:
#         # Filter the anonymous votes for the given election_id
#         anonymous_votes = [vote for vote in votes_data_anonymous if vote['election_id'] == 1]
#         # Extract user_ids
#         user_ids = set(vote['student_id'] for vote in anonymous_votes)
#         # Fetch user information based on user_ids
#         for user_id in user_ids:
#             user_info = next((student for student in students if student['student_id'] == user_id), None)
#             if user_info:
#                 voter_list.append({'name': f"{user_info['first_name']} {user_info['last_name']}", 'email': user_info['email']})

#     return render_template("vote_submit.html", results=results, voter_list=voter_list, show_pollview=show_pollview, show_voterview=show_voterview)

























# Acknowledgements
@application.route("/acknowledgements")
def acknowledgements():
    return render_template("acknowledgements.html", active_page="acknowledgements")


@application.route("/acknowledgements_form", methods=["POST"])
def acknowledgements_form():
    return redirect(
        url_for("acknowledgements")
    )  # Redirect to the home page or another appropriate page


@application.route("/submit_form", methods=["POST"])
def submit_form():
    subjects_data = fetch_subjects_data()
    # Extract form data
    name = request.form.get("name")
    unit_code = request.form.get("unitCode")
    year_completed = request.form.get("yearCompleted")
    score = request.form.get("score")
    credit_points = request.form.get("creditPoints")
    grade = request.form.get("grade")
    in_progress = request.form.get("inProgress")

    # Construct the new subject dictionary
    new_subject = {
        "unit_code": unit_code,
        "name": name,
        "grade": grade,
        "score": score,
        "credit_points": credit_points,
        "year_completed": year_completed,
        "in_progress": in_progress,
    }

    # Check if the year exists in subjects_data, if not, create a new dict for the year
    if year_completed not in subjects_data:
        subjects_data[year_completed] = {}

    # Check if the subject already exists in the specified year
    if unit_code in subjects_data[year_completed]:
        # Update existing subject
        subjects_data[year_completed][unit_code].update(new_subject)
    else:
        # Add new subject
        subjects_data[year_completed][unit_code] = new_subject

    user_id = session.get("user_id")  # Retrieve uid from session

    doc_ref = (
        db.collection("users")
        .document(user_id)
        .collection(year_completed)
        .document(unit_code)
    )
    doc_ref.set(
        {
            "unit_code": unit_code,
            "name": name,
            "grade": grade,
            "score": score,
            "credit_points": credit_points,
            "year_completed": year_completed,
            "in_progress": in_progress,
        }
    )

    # Redirect to the home page or another appropriate page
    return redirect(url_for("home"))


# @application.route("/login", methods=["POST"])
# def login():
#     # Get the token from the request
#     token = request.json.get("token")

#     try:
#         # print(token)
#         # Verify the token with Firebase Admin SDK
#         decoded_token = auth.verify_id_token(token)
#         # print("passed decoded_token", decoded_token)
#         email = decoded_token.get("email")

#         # Check if the email ends with the Monash student email domain
#         if not email.endswith("@student.monash.edu"):
#             return jsonify({"message": "Access denied: Unauthorized email domain"}), 403

#         # If email is verified, proceed to create a session
#         session["name"] = decoded_token.get("name")
#         session["email"] = email

#         uid = decoded_token["uid"]
#         # print("passed uid", uid)

#         # Create a new session for the user
#         # Make sure to import 'session' from flask
#         session["user_id"] = uid
#         return jsonify({"message": "Successfully logged in"}), 200
#     except auth.InvalidIdTokenError:
#         return jsonify({"message": "Invalid ID token"}), 401
#     except Exception as e:
#         print(e)
#         # It's a good practice not to expose the exception details in production
#         # You may want to log the exception here
#         return jsonify({"message": "Error logging in"}), 500


@application.route("/check-login")
def check_login():
    if "user_id" in session:
        return jsonify(logged_in=True)
    else:
        return jsonify(logged_in=False)


@application.route("/logout", methods=["POST"])
def logout():
    session.clear()  # This will clear the session
    session.pop("name", None)
    session.pop("email", None)
    return jsonify({"message": "Session cleared"}), 200


@application.route("/delete_subject", methods=["POST"])
def delete_subject():
    data = request.json
    unit_code = data.get("unit_code")
    year = data.get("year")

    user_id = session.get("user_id")  # Retrieve uid from session

    try:
        # Attempt to delete the document
        db.collection("users").document(user_id).collection(year).document(
            unit_code
        ).delete()
        return jsonify({"success": True}), 200
    except Exception as e:
        # If an error occurs, log it and return a failure response
        print(f"An error occurred: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    application.run(debug=True)
