import time
import requests
from flask import render_template
from app import app
import pdb
import re


@app.template_filter('ctime')
def timectime(s):
    return time.ctime(s / 1000)


def _get_builds_data():
    jenkins = '{url}/job/{job}/api/json?tree=builds[number,status,timestamp,url,result,user,actions[parameters[name,value]]]'.format(url=app.config['JENKINS_URL'],
                                                                                                                                     job=app.config['JOB_NAME'])
    j_data = requests.get(jenkins, auth=(app.config['JENKINS_USER'], app.config['JENKINS_PASS']))

    builds = j_data.json()['builds']
    metadata = {}
    for build in builds:
        try:
            if build['actions'][2]['parameters'][0]['name'] == 'ENV_NAME' and build['actions'][2]['parameters'][2]['value'] == "build":
                j_details = requests.get("{}/api/json".format(build['url']),
                                         auth=(app.config['JENKINS_USER'], app.config['JENKINS_PASS']))
                j_console = requests.get("{}/consoleText".format(build['url']),
                                         auth=(app.config['JENKINS_USER'], app.config['JENKINS_PASS']))
                metadata[build['number']] = {}
                subjob_re = 'Starting building:\s.*\s#\d+'
                subjob_id = re.search(subjob_re, j_console.text).group(0).split(' ')[3].strip('#')
                subjob_name = 'env-deploy-custom'
                if build['result'] == 'FAILURE':
                    # This call is expencive, use it only for failed builds
                    subjob_err = requests.get("{}/job/{}/{}/consoleText".format(app.config['JENKINS_URL'],
                                                                                subjob_name, subjob_id),
                                              auth=(app.config['JENKINS_USER'], app.config['JENKINS_PASS']))
                    lines = subjob_err.text.split('\n')
                    errors = []
                    for num, line in enumerate(lines):
                        if "Traceback" in line:
                            errors = lines[num - 25:num]

                    metadata[build['number']]['errors'] = errors

                try:
                    autor = j_details.json()['actions'][0]['causes'][0]['userName']
                except KeyError:
                    autor = j_details.json()['actions'][0]['causes'][0]['upstreamProject']
                    autor = (autor[:20] + '..') if len(autor) > 20 else autor  # shorten author name
                metadata[build['number']]['author'] = autor
        except KeyError:
            pass
    return metadata, builds


@app.route('/')
def index():
    metadata, builds = _get_builds_data()
    return render_template("index.html", builds=builds, metadata=metadata)
