(1) For pythonanywhere, when there is not enough disk space run: 

rm -rf /tmp/* /tmp/.*

(2) For creating a virtual environment, go the main directory (/home/[USER]) and run the following:

mkvirtualenv myvirtualenv --python=/usr/bin/python3.10
workon myvirtualenv - activate the environment
pip install -r requirements.txt

Then modify in the project page the virtual environment path to:
/home/[USER]/.virtualenvs/myvirtualenv

(3) When deploying make sure the following:
- Be sure to rename the app.py to main.py
- You have the .env file stored in the directory
- make sure the requirements.txt has the relevant packages (otherwise it will install others and go over the 500MB limit in pythonanywhere)
- Make sure to have deployed the mysql server in pythonanywhere (look at the youtube video for details)
- Be sure to add the [USER].pythonanywhere.com to the firebase domain (under authentication -> settings -> authorized domains)
- Make sure the WSGI file (under pythonanywhere) is correctly formatted
    - Particuarly the line: 
        - from flask_app import app as application 
        CHANGE TO 
        - from [MAIN_RUN_FILE_NAME].py import [application OR app] as application
- Be sure change the db_config to the respective db info variable inside main/app.py
    - 'host': '[USER].mysql.pythonanywhere-services.com',
    - 'user': '[USER]',
    - 'password': '[PYTHONANYWHERE_SQL_PASSWORD]',
    - 'database': '[USER]$[PROJECT]'

(4) Moving folder content (/[PROJECT]/*) to the current directory (.)

mv /[PROJECT]/* .

(5) Be sure to change the .env file to incldue the relevant firebase credentials.

(6) Be sure to change the /project/config.py file to include the following:
- project_folder = os.path.expanduser('~/[PROJECT FOLDER NAME]')
- load_dotenv(os.path.join(project_folder, '.env'))

(7) Be sure to uncomment "db_config" and "cred" variables