#!/usr/bin/env python3

import io
import glob
import logging
from logging import getLogger as log
import shutil
from subprocess import CalledProcessError, DEVNULL, PIPE, run
import tempfile

logging.basicConfig(level='INFO')

DISTRO = 'manjaro'
SILENCE = True

def run_s(args):
    if SILENCE:
        return run(args, stdout=DEVNULL, stderr=DEVNULL)
    else:
        return run(args)

def run_sc(args):
    if SILENCE:
        return run(args, check=True, stdout=DEVNULL, stderr=DEVNULL)
    else:
        return run(args, check=True)

def run_p(args):
    return run(args, stdout=PIPE, stderr=PIPE)

def run_pc(args):
    return run(args, check=True, stdout=PIPE, stderr=PIPE)

def install_package(pkg):
    run_sc(['pacman', '-Sy'])
    try:
        return run_sc(['pacman', '-S', '--noconfirm', pkg])
    except CalledProcessError:
        if SILENCE:
            return run('yes | pacman -S {}'.format(pkg), shell=True, check=True, stdout=DEVNULL, stderr=DEVNULL)
        else:
            return run('yes | pacman -S {}'.format(pkg), shell=True, check=True)

def remove_orphans():
    if SILENCE: 
        run('pacman -Rns --noconfirm $(pacman -Qtdq)', shell=True, stdout=DEVNULL, stderr=DEVNULL)
    else:
        run('pacman -Rns --noconfirm $(pacman -Qtdq)', shell=True)

def remove_package(pkg):
    if pkg not in ('cower', 'suexec', 'pkgbuild-introspection'):
        run_s(['pacman', '-Rsc', '--noconfirm', pkg])
    remove_orphans()

def add_to_repo(pkg):
    if SILENCE:
        run(['repo-add', '-R', 'aur.db.tar.xz', pkg], cwd='/var/www/aur/', check=True, stdout=DEVNULL, stderr=DEVNULL)
    else:
        run(['repo-add', '-R', 'aur.db.tar.xz', pkg], cwd='/var/www/aur/', check=True)
    run_sc(['pacman', '-Sy'])

def parse(stream):
    return str(stream)[1:].strip('"').strip('\'').split('\\n')

def update_package_and_dependencies(all_packages, packages_to_check, pkg):
    logger = log('main.{}'.format(pkg))
    logger.debug(' all packages: {}'.format(all_packages))
    logger.debug(' still to check: {}'.format(packages_to_check))
    install_package(pkg)
    # check all dependencies first, enforce rebuilt if a dependency is updated
    deps = []
    result = run_pc(['pactree', '-l', pkg])
    for dep in parse(result.stdout):
        if dep != pkg and dep in all_packages:
            deps.append(dep)
    remove_package(pkg)
    if deps:
        logger.info(' dependencies: {}'.format(deps))
        while deps:
            dep = deps.pop(0)
            if dep in packages_to_check:
                checked = update_package_and_dependencies(all_packages, packages_to_check, dep)
                for p in checked:
                    if p in deps:
                        deps.remove(p)
                    if p in packages_to_check:
                        packages_to_check.remove(p)
    # at this point all dependencies should be handled
    # (i) check if the package is up to date
    install_package(pkg)
    result = run_s(['cower', '-u', pkg])
    if result.returncode == 0:
        logger.info(' package up to date!')
        remove_package(pkg)
        return (pkg,)
    # (ii) an update is available, find out if this is a from a split pkgbuild
    result = run_pc(['cower', '-i', pkg])
    src = pkg
    for line in parse(result.stdout):
        if 'PackageBase' in line:
            src = line.split(':')[1].strip()
            break
    remove_package(pkg)
    # (iii) build the package
    logger.info(' update available, building {} ...'.format(src))
    result = run_p(['/usr/sbin/su-exec', 'aur', '/usr/local/bin/build-aur-package.sh', src])
    if result.returncode != 0:
        logger.error(' build failed!')
        _, logfile = tempfile.mkstemp()
        with open(logfile, 'w') as f:
            for line in parse(result.stderr):
                f.write(line + '\n')
        raise RuntimeError('error building {}, see {} for more infos!'.format(pkg, logfile))
    # (iv) add all built packages to repo
    checked_packages = []
    for pkg_file in glob.glob('/var/aur/*.pkg.tar.*'):
        # get the name of the package
        pkg_name = None
        for line in parse(run_pc(['pacman', '-Qi', '-p', pkg_file]).stdout):
            if 'Name' in line:
                pkg_name = line.split(':')[1].strip()
                break
        if not pkg_name:
            raise RuntimeError('could not extract package name from {}'.format(pkg_file))
        checked_packages.append(pkg_name)
        # move the package
        try:
            shutil.move(pkg_file, '/var/www/aur/')
        except shutil.Error:
            pass
        # refresh the repo
        add_to_repo(pkg_file)
    if not checked_packages:
        raise RuntimeError('no packages present after building {}'.format(pkg))
    return checked_packages

def ensure_build_env_packages():
    for pkg in ('cower', 'suexec', 'pkgbuild-introspection'):
        result = run_s(['pacman', '-Q', pkg])
        if result.returncode == 0:
            break
        install_package(pkg)

log('main').info(' updating system ...')
run_sc(['pacman-mirrors', '-c', 'Germany'])
run_sc(['pacman', '-Syuu', '--noconfirm'])
remove_orphans()

result = run_s(['pacman', '-Q', 'cower'])
if result.returncode != 0:
    log('main').info(' installing cower ...')
    run_sc(['/usr/sbin/su-exec', 'aur', '/usr/local/bin/build-aur-package.sh', 'cower'])
    run_sc(['pacman', '-U', '--noconfirm'] + glob.glob('/var/aur/cower*.pkg.tar.*'))
    run_sc(['rm', ] + glob.glob('/var/aur/cower*.pkg.tar.*'))

log('main').info(' adding repo to pacman.conf ...')
with open('/etc/pacman.conf', 'a') as f:
    f.write('[aur]\n')
    f.write('SigLevel = Optional TrustAll\n')
    f.write('Server = http://repos.schindlerfamily.de/{}/aur/\n'.format(DISTRO))
log('main').info(' updating ...')
run_sc(['pacman', '-Syuu', '--noconfirm'])
run_sc(['pacman', '-S', '--noconfirm', 'pkgbuild-introspection'])
log('main').info(' processing all packages from this repository:')

packages = run('pacman -Sl aur | awk \'{ print $2}\' | sort', check=True, shell=True, stdout=PIPE, stderr=PIPE)
packages = [ p for p in parse(packages.stdout) if p]
packages_to_check = packages.copy()
while packages_to_check:
    pkg = packages_to_check.pop(0)
    checked = update_package_and_dependencies(packages, packages_to_check, pkg)
    for p in checked:
        if p in packages_to_check:
            packages_to_check.remove(p)

log('main').info(' everything up to date, refreshig repo ...')
run(['./update-repos.sh',], cwd='/var/www', check=True, stdout=DEVNULL, stderr=DEVNULL)

