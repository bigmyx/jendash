# pylint: disable=R0914,C0301,R0101
import time
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
    for idx, build in enumerate(builds):
        errors = []
        try:
            if build['actions'][2]['parameters'][6]['name'] == 'ENV_NAME' and build['actions'][2]['parameters'][14]['value'] != "destroy":
                metadata[build['number']] = {}
                j_details = requests.get("{}/api/json".format(build['url']),
                                         auth=(app.config['JENKINS_USER'], app.config['JENKINS_PASS']))
                app.logger.debug('Get Job Details Headers: %s\ntime: %d', j_details.headers, j_details.elapsed.total_seconds())
                if build['result'] == 'FAILURE':
                    j_console = requests.get("{}/consoleText".format(build['url']),
                                             auth=(app.config['JENKINS_USER'], app.config['JENKINS_PASS']))
                    app.logger.debug('Get Job Console Headers: %s\ntime: %d', j_console.headers, j_console.elapsed.total_seconds())
                    lines = j_console.text.split('\n')
                    for num, line in enumerate(lines):
                        if "FAILURE" in line:
                            errors = lines[num - 50:num]

                metadata[build['number']]['errors'] = errors

                try:
                    author = j_details.json()['actions'][0]['causes'][0]['userName']
                except KeyError:
                    author = j_details.json()['actions'][0]['causes'][0]['upstreamProject']
                    upstream_url = j_details.json()['actions'][0]['causes'][0]['upstreamUrl']
                    upstream_build = j_details.json()['actions'][0]['causes'][0]['upstreamBuild']
                    if 'regression' not in author:
                        upstream_job = requests.get("{url}/{job}/{build}/api/json".format(url=app.config['JENKINS_URL'],
                                                                                          job=upstream_url, build=upstream_build),
                                                    auth=(app.config['JENKINS_USER'], app.config['JENKINS_PASS']))
                        author = upstream_job.json()['actions'][1]['causes'][0]['userName']
                    author = (author[:20] + '..') if len(author) > 20 else author  # shorten author name
                metadata[build['number']]['author'] = author
            else:
                del builds[idx]
                continue
        except KeyError as e:
            app.logger.error('build #%d, key error: %s', build['number'], e)
            del builds[idx]
            continue
    return metadata, builds


@app.route('/')
def index():
    metadata, builds = _get_builds_data()
    return render_template("index.html", builds=builds, metadata=metadata)
