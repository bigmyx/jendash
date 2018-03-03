import time
import requests
from flask import render_template
from app import app
import pdb


@app.template_filter('ctime')
def timectime(s):
    return time.ctime(s / 1000)


def _get_builds_data():
    jenkins = '{url}/job/{job}/api/json?tree=builds[number,status,timestamp,url,result,user,actions[parameters[name,value]]]'.format(url=app.config['JENKINS_URL'],
                                                                                                                                     job=app.config['JOB_NAME'])
    j_data = requests.get(jenkins, auth=(app.config['JENKINS_USER'], app.config['JENKINS_PASS']))

    builds = j_data.json()['builds']
    authors = {}
    for build in builds:
        try:
            if build['actions'][2]['parameters'][0]['name'] == 'ENV_NAME' and build['actions'][2]['parameters'][2]['value'] == "build":
                j_details = requests.get("{}/api/json".format(build['url']),
                                         auth=(app.config['JENKINS_USER'], app.config['JENKINS_PASS']))
                try:
                    authors[build['number']] = j_details.json()['actions'][0]['causes'][0]['userName']
                except KeyError:
                    autor = j_details.json()['actions'][0]['causes'][0]['upstreamProject']
                    autor = (autor[:20] + '..') if len(autor) > 20 else autor
                    authors[build['number']] = autor
        except KeyError:
            pass
    return authors, builds


@app.route('/')
def index():
    authors, builds = _get_builds_data()
    return render_template("index.html", builds=builds, authors=authors)
