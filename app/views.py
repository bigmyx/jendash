import time
import requests
from flask import render_template
from app import app


@app.template_filter('ctime')
def timectime(s):
    return time.ctime(s / 1000)


def _get_builds_data():
    jenkins = '{url}/job/{job}/api/json?tree=builds[number,status,timestamp,url,result,user,actions[parameters[name,value]]]'.format(url=app.config['JENKINS_URL'],
                                                                                                                                     job=app.config['JOB_NAME'])
    j_data = requests.get(jenkins, auth=(app.config['JENKINS_USER'], app.config['JENKINS_PASS']))
    return j_data.json()['builds']


@app.route('/')
def index():
    builds = _get_builds_data()
    return render_template("index.html", builds=builds)
