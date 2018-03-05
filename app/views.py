import time
import re
import requests
from flask import render_template
from app import app
import requests_cache


requests_cache.install_cache(cache_name='jendash_cache', backend='sqlite', expire_after=300)


@app.template_filter('ctime')
def timectime(s):
    return time.ctime(s / 1000)


def _get_builds_data():
    jenkins = '{url}/job/{job}/api/json?tree=builds[number,status,timestamp,url,result,user,actions[parameters[name,value]]]'.format(url=app.config['JENKINS_URL'],
                                                                                                                                     job=app.config['JOB_NAME'])
    j_data = requests.get(jenkins, auth=(app.config['JENKINS_USER'], app.config['JENKINS_PASS']))
    app.logger.debug('Get Jobs Headers: %s\ntime: %d', j_data.headers, j_data.elapsed.total_seconds())

    builds = j_data.json()['builds']
    metadata = {}
    for build in builds:
        try:
            if build['actions'][2]['parameters'][0]['name'] == 'ENV_NAME' and build['actions'][2]['parameters'][2]['value'] == "build":
                metadata[build['number']] = {}
                j_details = requests.get("{}/api/json".format(build['url']),
                                         auth=(app.config['JENKINS_USER'], app.config['JENKINS_PASS']))
                app.logger.debug('Get Job Details Headers: %s\ntime: %d', j_details.headers, j_details.elapsed.total_seconds())
                if build['result'] == 'FAILURE':
                    j_console = requests.get("{}/consoleText".format(build['url']),
                                             auth=(app.config['JENKINS_USER'], app.config['JENKINS_PASS']))
                    app.logger.debug('Get Job Console Headers: %s\ntime: %d', j_console.headers, j_console.elapsed.total_seconds())
                    subjob_re = 'Starting building:\s.*\s#\d+'
                    subjob_id = re.search(subjob_re, j_console.text).group(0).split(' ')[3].strip('#')
                    subjob_name = 'env-deploy-custom'
                    subjob_err = requests.get("{}/job/{}/{}/consoleText".format(app.config['JENKINS_URL'],
                                                                                subjob_name, subjob_id),
                                              auth=(app.config['JENKINS_USER'], app.config['JENKINS_PASS']))
                    app.logger.debug('Get Subjob Console Headers: %s\ntime: %d', subjob_err.headers, subjob_err.elapsed.total_seconds())
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
