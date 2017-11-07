#!/bin/bash

set -e

export pkg=${@}

source /etc/profile.d/perlbin.sh

cd
[ -e ${pkg} ] && rm -rf ${pkg}
git clone https://aur.archlinux.org/${pkg}.git
cd ${pkg}
makepkg -fs --noconfirm
mv *.pkg.tar.* ../
cd
rm -rf ${pkg}

