```
# This file is part of the manjaro-aur-base project:
#   https://github.com/ftalbrecht/manjaro-aur-base/
# Copyright holders: Felix Schindler
# License: BSD 2-Clause License (http://opensource.org/licenses/BSD-2-Clause)
```

This project can help you build [aur](https://aur.archlinux.org/) packages and maintain a
[custom local repository](https://wiki.archlinux.org/index.php/Pacman/Tips_and_tricks#Custom_local_repository)
of these packeges.

You will need docker and if you have a decent setup (see the
[notes on security implications](https://wiki.archlinux.org/index.php/Docker#Installation)
here) you will need to prepend `sudo ` to all `docker` calls.

get/build the docker container
==============================

You need docker. You can either get the corresponding image from
[hub.docker.com](https://hub.docker.com/r/ftschindler/manjaro-aur-base/)
(it will not be updated regularly) or build the image locally (recommended):

```bash
systemctl start docker
git clone https://github.com/ftalbrecht/manjaro-aur-base.git
docker build --rm -t ftschindler/manjaro-aur-base -f manjaro-aur-base/Dockerfile manjaro-aur-base/
```

build a single package
======================

If you are just interested in building a single package, simply spawn a docker container.
Since everything you do inside docker will be lost afterwards, you need to mount a folder
into the docker container.

```bash
mkdir pkg
docker run --rm -t -i --hostname aur \
  -v $PWD/pkg:/var/www/ \
  ftschindler/manjaro-aur-base \
  /bin/bash
```

This should give you a root shell inside the docker container. Calling `mount | grep www` should
show you that something is mounted at `/var/www`.

First of all, you should update the system (`pacman -Syuu --noconfirm`) in case the image is outdated.
Afterwards you can build a package by calling

```bash
su-exec aur build-aur-package.sh <pkgname>
```

where `<pkgname>` is a valid package name or package group name (say `cower`). If you get a gpg error, something went wrong
when building the image or updating, please [report an issue](https://github.com/ftalbrecht/manjaro-aur-base/issues/new).

If all went well, the final package can be found in `/var/aur/`. If not, calling

```bash
su aur
```

should give you a shell of the `aur` user, `cd` will bring you to `/var/aur` where you will find the package
sources. Fix any build failures as you would usually (the `aur` user is `sudo pacman` capable without password).
Afterwards move the package to `/var/aur`.

To make the final package available outside of the docker container, simply move it to `/var/www/`, i.e.

```bash
mv /var/aur/cower-17-2-x86_64.pkg.tar.xz /var/www/
```

You can now exit the docker (`exit` or `Ctrl + D`) and you should find the package ready for installation:

```bash
pacman -U pkg/cower-17-2-x86_64.pkg.tar.xz
```
