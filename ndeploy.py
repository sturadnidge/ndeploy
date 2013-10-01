import os
import re
import uuid
import time
import json
import shutil

from flask import Flask, Response, abort, jsonify, request, redirect

app = Flask(__name__, static_url_path='')

uuid_re = re.compile('^([0-9a-f]){8}-([0-9a-f]){4}-([0-9a-f]){4}-([0-9a-f]){4}-([0-9a-f]){12}$')

''' root route
'''

@app.route('/')
def index():
    return app.send_static_file('index.html')

''' provision routes
'''
@app.route('/unprovisioned/')
def unprovisioned():
    ''' if iPXE phones home but no provision is found
        a uuid file will be created in here

        create_provision checks this directory and deletes
        any matching uuids it finds

        a GET request will return a directory listing
    '''
    results = [ f for f in os.listdir('unprovisioned') \
                if uuid_re.match(f) \
                and os.path.isfile(os.path.join('unprovisioned', f)) ]

    return jsonify(unprovisioned = results)


@app.route('/provisions/', methods=['GET', 'POST'])
def provisions():
    if request.method == 'POST':

        if not request.json:
            abort(400)

        if uuid_re.match(request.json['uuid']):
            host_uuid = request.json['uuid']
        else:
            abort(400)

        fqdn = request.json['fqdn']
        boot_sequence = request.json['boot_sequence']
        os_template = request.json['os_template']

        create_provision(host_uuid, fqdn, os_template, boot_sequence)

        customise_os_template(host_uuid, fqdn, os_template)

        return 'provision created successfully'

    else:
        ''' a GET will return a directory listing
        '''
        results = [ d for d in os.listdir('provisions') \
                    if uuid_re.match(d) \
                    and os.path.isdir(os.path.join('provisions', d)) ]
        
        return jsonify(provisions = results)

@app.route('/provisions/<host_uuid>')
def provision(host_uuid):
    provision_file = os.path.join('provisions', host_uuid, 'provision.json')

    if not os.path.exists(provision_file):
        abort(404)
    else:
        with open(provision_file) as f:
            data = json.loads(f.read())

        return jsonify(data)

@app.route('/provisions/<host_uuid>/<file_name>', methods=['GET', 'POST'])
def get_file(host_uuid, file_name):
    provision_dir = os.path.join('provisions', host_uuid)
    provision_file = os.path.join(provision_dir, 'provision.json')

    if os.path.exists(provision_file):

        if request.method == 'POST':
            if file_name == 'reprovision':
                with open(provision_file) as f:
                    provision = json.loads(f.read())

                provision['current_step'] = 1
                provision['created'] = int(time.time() * 1000)
                provision['started'] = ""
                provision['finished'] = ""

                create_symlink(provision_dir, provision['boot_sequence']['1'], \
                    'boot')

                provision_content = json.dumps(provision, indent=2)

                with open(provision_file, 'w+') as f:
                    f.write(provision_content)

                return 'reprovision successful'

            else:
                abort(404)

        else:
            if file_name == 'boot':
                ''' get current boot file content immediately
                    because we may change it shortly
                '''
                with open(os.path.join(provision_dir, file_name)) as f:
                    current_bootfile = f.read()

                ''' if it's iPXE, update current_step in provision file
                    and point boot symlink at next file in boot_sequence
                '''
                if 'iPXE' in request.user_agent.string:

                    with open(provision_file) as f:
                        provision = json.loads(f.read())

                    current_step = provision['current_step']

                    if int(current_step) == 1:
                        provision['started'] = int(time.time() * 1000)

                    if int(current_step) < len(provision['boot_sequence']):
                        current_step += 1
                        create_symlink(provision_dir, \
                            provision['boot_sequence'][str(current_step)], \
                            'boot')
                        provision['current_step'] = current_step
                    else:
                        provision['finished'] = int(time.time() * 1000)

                    provision_content = json.dumps(provision, indent=2)

                    with open(provision_file, 'w+') as f:
                        f.write(provision_content)

                return Response(current_bootfile, mimetype='text/plain')

            else:
                ''' it's not a boot file request so 
                    just return requested file as text/plain
                '''
                with open(os.path.join(provision_dir, file_name)) as f:
                    data = f.read()
                    
                return Response(data, mimetype='text/plain')
    else:
        ''' there no provision file, so either it's
            and unknown host or something messing around
        '''
        if not os.path.exists(provision_dir):
            if 'iPXE' in request.user_agent.string:
                ''' never free, never me
                '''
                with open(os.path.join('unprovisioned', host_uuid), 'w') as f:
                    f.write()

                return 'so i dub thee unprovisioned\n'

            else:
                abort(404)



''' template routes
'''

@app.route('/templates')
def get_templates():
    ''' split out ipxe and os templates
        using a list comprehension here
        would be taking the piss
    '''
    os_t = []
    boot_t = []
    for root,dirs,files in os.walk('templates'):
        for f in files:
            if f.endswith('ipxe'):
                boot_t.append(f)
            elif f.endswith('ks'):
                os_t.append(f)

    return jsonify(boot = boot_t, os = os_t)


''' helper functions
'''
def create_provision(host_uuid, fqdn, os_file, sequence):
    ''' this calls most of the other helper functions
    '''
    provision_created = int(time.time() * 1000)
    provision_dir = os.path.join('provisions', host_uuid)
    provision_file = os.path.join(provision_dir, 'provision.json')

    check_unprovisioned(host_uuid)

    create_dir(provision_dir)

    create_file(provision_file, \
                create_provision_content(host_uuid, fqdn, os_file, \
                                         sequence, provision_created))

    with open(provision_file) as f:
        data = json.loads(f.read())

    copy_provision_files(provision_dir, data['os_template'], \
                         data['boot_sequence'])

    create_symlink(provision_dir, data['os_template'], 'ks.cfg')

    create_symlink(provision_dir, data['boot_sequence']['1'], 'boot')


def check_unprovisioned(host_uuid):
    unprovisioned_uuid = os.path.join('unprovisioned', host_uuid)
    
    if os.path.exists(unprovisioned_uuid):
        try:
            os.unlink(unprovisioned_uuid)
        except OSError:
            raise

def copy_provision_files(provision_dir, os_template, boot_sequence):
    ''' provision_dir and os_template come in as strings, boot_sequence
        as a dict. return a 400 if source file not found.
    '''
    os_install_src = os.path.join('templates', os_template)
    if os.path.exists(os_install_src):
        try:
            shutil.copy(os_install_src, provision_dir)
        except OSError:
            raise
    else:
        abort(400)

    for k, boot_file in boot_sequence.iteritems():
        boot_src = os.path.join('templates', boot_file)
        if os.path.exists(boot_src):
            try:
                shutil.copy(boot_src, provision_dir)
            except OSError:
                raise
        else:
            abort(400)


def customise_os_template(host_uuid, fqdn, os_template_file):
    ''' will eventually use jinja for this, in the meantime
        just keep it simple.
    '''
    provision_dir = os.path.join('provisions', host_uuid)
    template_file = os.path.join(provision_dir, os_template_file)

    with open(template_file) as f:
        data = f.read()

    customised = data.replace("{{hostname}}", fqdn, 1)

    with open(template_file, 'w') as f:
        f.write(customised)


def create_dir(dir_name):
    if not os.path.isdir(dir_name):
        try: 
            os.makedirs(dir_name)
        except OSError:
            raise


def create_file(target, content):
    with open(target, 'w') as f:
        f.write(content)


def create_symlink(dir_name, link_source, link_name):
    if os.path.islink(os.path.join(dir_name, link_name)):
        try:
            os.unlink(os.path.join(dir_name, link_name))
        except IOError:
            raise

    try:
        os.symlink(link_source, os.path.join(dir_name, link_name))
    except IOError:
        raise


def create_provision_content(host_uuid, fqdn, os_file, sequence, provision_created):
    ''' build up the provision content, manipulate as JSON
        but return as a string.
    '''
    provision_uuid = str(uuid.uuid4())
    fqdn_array = fqdn.split('.')
    host_name = ''.join(fqdn_array[:1])
    host_suffix = '.'.join(fqdn_array[1:])

    with open(os.path.join('templates','provision.json')) as f:
        data = json.loads(f.read())

    data['id'] = provision_uuid
    data['created'] = provision_created
    data['current_step'] = 1
    data['boot_sequence'] = sequence
    data['os_template'] = os_file
    data['host']['suffix'] = host_suffix
    data['host']['name'] = host_name
    data['host']['uuid'] = host_uuid
    data['network'] = get_network_details(fqdn)

    if data['network']['ip'] == 'dhcp':
        del data['regional_settings']
    else:
        data['regional_settings'] = get_regional_settings(data['network']['ip'])

    return json.dumps(data, indent=2)


def get_network_details(fqdn):
    ''' takes an fqdn (string) and resolves DNS
        if no DNS entry, return {"ip": "dhcp"}
        else returns JSON fragment
    '''
    return {u'ip': u'dhcp'}


def get_regional_settings(ip_address):
    ''' takes an ip_address (string) and derives regional settings
        if 'ip_address' == 'dhcp' return nothing
        else returns JSON fragment
    '''
    pass


if __name__ == '__main__':
    app.run('0.0.0.0', debug=False)
