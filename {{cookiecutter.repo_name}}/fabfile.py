# coding=utf-8
"""
Facilitate deployment to server with Fabric

Deploy will consist of:
	pull changes from GIT repository
	update dependences (with pip)
	update db (with and without south)
	collect static
	restart webserver (gunicorn)
A fast deploy can be done:
	pull changes from GIT
	restart webserver
"""

# Supervisor commands
#   supervisorctl start/stop/restart <appname>
#   kill the process... not optimal
# Graceful restart gunicorn with a HUP signal
# 	so instead of use supervisor, do a graceful restart with
# kill -s HUP $(cat gunicorn.pid)

from StringIO import StringIO
import glob
import os
from fabric.api import run, abort, env, put, task, cd
from fabric.context_managers import prefix, lcd
from fabric.contrib.files import exists
import posixpath
from fabric.contrib.console import confirm
from fabric.decorators import serial
from fabric.main import load_settings
from fabric.operations import local
from fabric.utils import puts
from contextlib import contextmanager as _contextmanager
import sys

env.localfolder = os.path.realpath(os.path.dirname(__file__))
env.port = 22
if not env.get('NAME'):
	default_project_name = os.path.split(os.path.dirname(__file__))[1]
	settings_file = 'fab_%s.ini' % default_project_name
	if not os.path.isfile(settings_file):
		print "Cannot find setting file on %s create one or ovveride it calling `fab -c host.ini`." % settings_file
		sys.exit(1)
	print "Loading settings from %s." % settings_file
	env.update(load_settings(settings_file))

if not env.get('PROCESS_NAME'):
	env.PROCESS_NAME = 'gunicorn-%s' % env.NAME

env.USE_SOUTH = env.get('USE_SOUTH') != 'False'

if os.path.exists(os.path.expanduser("~/.ssh/config")):
	env.use_ssh_config = True

DO_REQUIREMENTS = False


def perform_env_substitutions():
	""" Do recursive substitution until the value doesn't change
	Change the type of some env variable that should not be string
	"""
	for key, value in env.items():
		if isinstance(env[key], basestring):
			old_value = env[key]
			while True:
				value = old_value.format(**env)
				if value == old_value:
					break
				old_value = value
			env[key] = value
	if env.USE_SUPERVISOR == 'False':
		env.USE_SUPERVISOR = False
	if env.USE_SUPERVISOR and not env.SUPERVISOR_JOBNAME:
		print "Please specify the SUPERVISOR_JOBNAME to use Supervisor"
		sys.exit(1)


perform_env_substitutions()


def secrets_file_paths():
	""" Return a list of secret files (to be sent) relative to REPOSITORY_FOLDER """
	return env.SECRETS_FILE.split(',')


@_contextmanager
def virtualenv(venv_path=env.VENV_FOLDER):
	"""
	Put fabric commands in a virtualenv
	"""
	with prefix("source %s" % posixpath.join(venv_path, "bin/activate")):
		yield


def get_repository():
	if run("test -d %s" % env.REPOSITORY_FOLDER, quiet=True).failed:
		puts("Creating repository folder.")
		run("mkdir -p %s" % env.REPOSITORY_FOLDER)
	if not exists(posixpath.join(env.REPOSITORY_FOLDER, '.git')):
		puts("Cloning from repository.")
		run("git clone %s %s" % (env.GIT_REPOSITORY, env.REPOSITORY_FOLDER))
	else:
		update_instance(justPull=True)


def create_virtualenv():
	if run("test -d %s" % env.VENV_FOLDER, quiet=True).failed:
		run('virtualenv %s' % env.VENV_FOLDER)


def update_distribute():
	with virtualenv():
		run('pip install -U -q distribute')


@task
def initial_deploy():
	"""
	Prepare the remote instance with git repository and virtualenv.
	"""
	get_repository()
	create_virtualenv()
	update_distribute()  # some package won't install if distriubte is the old one
	run('mkdir -p %s' % env.LOGDIR)  # create the log dir if missing
	if os.path.isfile(os.path.join(env.localfolder, "node_modules", "yuglify", "bin", "yuglify")):
		# if we are using yuglify locally (I suppose it's on remote too)
		run('chmod +x %s' % posixpath.join(env.REPOSITORY_FOLDER, "node_modules", "yuglify", "bin", "yuglify"))
	create_run_command()


@serial
def update_database():
	with virtualenv():
		with cd(env.REPOSITORY_FOLDER):
			# update database, both standard apps and south migrated
			run("python manage.py syncdb")
			if env.get('USE_SOUTH', True):
				run("python manage.py migrate")


@task
def update_requirements():
	""" Update all libraries in requirements file """
	with virtualenv():
		with cd(env.REPOSITORY_FOLDER):
			run('pip install -U -r %s' % env.REQUIREMENT_PATH)  # update libraries


def update_instance(do_update_requirements=True, justPull=False):
	with cd(env.REPOSITORY_FOLDER):
		run("git pull")  # pull the changes
	if justPull:
		return
	with virtualenv():
		with cd(env.REPOSITORY_FOLDER):
			if do_update_requirements:
				update_requirements()

			run("python manage.py syncdb")

			# if run("test -d %s" % env.STATIC_FOLDER, quiet=True).failed:
			# 	puts("Creating static subfolder for generated assets.")
			# 	run("mkdir -p %s" % env.STATIC_FOLDER)

			if run("test -d %s" % env.MEDIA_FOLDER, quiet=True).failed:
				puts("Creating media subfolder for user uploaded assets.")
				run("mkdir -p %s" % env.MEDIA_FOLDER)

			run("python manage.py collectstatic --noinput")

			update_database()


def get_gunicorn_command(daemon=True):
	options = [
		'-w %s' % env.GUNICORN_WORKERS,  # --user=$USER --group=$GROUP
		'--log-level=debug',
		'-b 127.0.0.1:%s' % env.GUNICORN_PORT,
		'--pid %s' % env.GUNICORN_PID_FILE,
		'--log-file %(log)s' % {'log': env.GUNICORN_LOGFILE},
		'-t %s' % env.GUNICORN_WORKERS_TIMEOUT,  # timeout, upload processes can take some time (default is 30 seconds)
		# '--name \'gunicorn-%s\'' % env.NAME,
	]
	if daemon:
		options.append('--daemon')
	return "{env_path}/bin/gunicorn {options_string} {wsgi_app}".format(
		env_path=env.VENV_FOLDER,
		options_string=" ".join(options),
		wsgi_app=env.WSGI_APPLICATION,
	)


def start(daemon=False):
	if env.USE_SUPERVISOR:
		# Supervisor should be set to use this fabfile too
		# the command should be 'fab gunicorn_start_local'
		run('supervisorctl start %s' % env.SUPERVISOR_JOBNAME)
	else:  # directly start remote Gunicorn
		with virtualenv():
			with cd(env.REPOSITORY_FOLDER):
				gunicorn_command = get_gunicorn_command(daemon=True)
				run(gunicorn_command)


@task
def stop():
	""" Stop the remote gunicorn instance (eventually using supervisor) """
	if env.USE_SUPERVISOR:
		run('supervisorctl stop %s' % env.SUPERVISOR_JOBNAME)
	else:  # directly start remote Gunicorn
		puts('Sending TERM signal to Gunicorn.')
		gunicorn_pid = int(run('cat %s' % env.GUNICORN_PID_FILE, quiet=True))
		run("kill %d" % gunicorn_pid)


@task
def start_local():
	""" Start locally gunicorn instance """
	gunicorn_command = get_gunicorn_command(daemon=False)
	if env.USE_SUPERVISOR:
		#abort("You should not start_local if you would like to use Supervisor.")
		process = None
		try:
			process = local(gunicorn_command)
		except Exception as e:
			print "EXCEPTION: %s" % e
			if process is not None:
				import signal

				process.send_signal(signal.SIGTERM)
	else:
		with lcd(env.REPOSITORY_FOLDER):
			local(gunicorn_command)


@task
def restart():
	""" Start/Restart the remote gunicorn instance (eventually using supervisor) """
	if run("test -e %s" % env.GUNICORN_PID_FILE, quiet=True).failed:
		puts("Gunicorn doesn't seems to be running (PID file missing)...")
		start()

	# gunicorn_pid = int(run('cat %s' % GUNICORN_PID_FILE, quiet=True))
	# if not gunicorn_pid:
	# 	abort('ERROR: Gunicorn seems down after the start command.')
	else:
		puts('Gracefully restarting Gunicorn.')
		gunicorn_pid = int(run('cat %s' % env.GUNICORN_PID_FILE, quiet=True))
		if run("kill -s HUP %d" % gunicorn_pid, quiet=True).failed:
			puts("Gunicorn is not running. Starting...")
			start()


@task
def send_secrets(secret_files=None, ask=False):
	""" Send the secret settings file that is excluded from VCS """
	if ask and not confirm("Upload secret settings?"):
		return
	if secret_files is None:
		secret_files = secrets_file_paths()
	if isinstance(secret_files, basestring):
		secret_files = [secret_files]
	puts("Uploading secrets.")
	for filename in secret_files:
		local_path = os.path.join(env.localfolder, filename)
		remote_path = posixpath.join(env.REPOSITORY_FOLDER, filename)
		put(local_path, remote_path)
	if len(secret_files) == 1:
		with cd(env.REPOSITORY_FOLDER):
			run('ln -s -f %s settings_local.py' % secret_files[0])


def run_command_content(daemon=None):
	if daemon is None:
		daemon = env.USE_SUPERVISOR
	default_args = "-w={GUNICORN_WORKERS} --log-level=warning -t {GUNICORN_WORKERS_TIMEOUT}"
	#--name '{PROCESS_NAME}'
	if daemon:
		default_args += " --daemon"
	env.GUNICORN_ARGUMENTS = default_args.format(**env)

	# prepare the variables

	content = file(os.path.join(env.localfolder, 'run_server.sh.tmpl')).read()
	return content.format(**env)


@task
def create_run_command():
	""" Create the remote_run command to be executed """
	puts("Creating run_server.")
	with lcd(env.localfolder):
		with cd(env.REPOSITORY_FOLDER):
			run_temp_file = StringIO(run_command_content())
			run_temp_file.name = "run_server"  # to show it as fabric file representation
			put(run_temp_file, posixpath.join(env.REPOSITORY_FOLDER, 'run_server'))
			run('chmod +x run_server')


@task
def local_create_run_command():
	puts("Creating run_server command to be run with supervisor.")
	with lcd(env.localfolder):
		with file('run_server', 'w') as runner:
			runner.write(run_command_content())


@task
def local_create_run_command():
	puts("Creating run_server command to be run " + ("with" if env.USE_SUPERVISOR else "without") + " supervisor.")
	with lcd(env.localfolder):
		with file('run_server', 'w') as runner:
			runner.write(run_command_content())


@task
def deploy(justPull=False):
	"""
	Update the remote instance.

	Pull from git, update virtualenv, create static and restart gunicorn
	"""
	is_this_initial = False
	if run("test -d %s/.git" % env.REPOSITORY_FOLDER, quiet=True).failed:  # destination folder to be created
		message = 'Repository folder doesn\'t exists on destination. Proceed with initial deploy?'
		if not confirm(message):
			abort("Aborting at user request.")
		else:
			initial_deploy()
			is_this_initial = True

	for secret in secrets_file_paths():
		if run("test -e %s" % posixpath.join(env.REPOSITORY_FOLDER, secret), quiet=True).failed:  # secrets missing
			message = 'Some secret doesn\'t exists on destination. Should we send them?'
			send_secrets(ask=True)

	update_instance(do_update_requirements=is_this_initial or DO_REQUIREMENTS, justPull=justPull)

	restart()


@task
def discard_remote_git():
	"""Discard changes done on remote """
	with cd(env.REPOSITORY_FOLDER):
		run('git reset --hard HEAD')


@task
def send_file(mask='*.*', subfolder='files', mask_prefix=None):
	if mask_prefix:
		mask = mask_prefix + mask
	run('mkdir -p %s' % posixpath.join(env.REPOSITORY_FOLDER, subfolder))
	with lcd(env.localfolder):
		puts("Uploading %s." % posixpath.join(subfolder, mask))
		file_paths = glob.glob(os.path.join(env.localfolder, subfolder, mask))
		for path in file_paths:
			filename = os.path.basename(path)
			remote_path = posixpath.join(env.REPOSITORY_FOLDER, subfolder, filename)
			put(path, remote_path)
