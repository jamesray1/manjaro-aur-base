FROM zalox/manjaro

MAINTAINER Felix Schindler <aut at felixschindler dot net>

ADD root_home.tgz /root/
RUN chown -R root:root /root

RUN [ -e /etc/ssl/certs/ca-certificates.crt ] || \
      ln -s /etc/ca-certificates/extracted/ca-bundle.trust.crt /etc/ssl/certs/ca-certificates.crt
RUN pacman -Rsc --noconfirm wayland llvm-libs ; \
    pacman-mirrors --fasttrack && \
    pacman -Syuu --noconfirm

RUN pacman -S --noconfirm base-devel bash-completion cower glibc git lzop openssh python sed sudo vim wget && \
    echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && \
    echo "de_DE.UTF-8 UTF-8" >> /etc/locale.gen && \
    locale-gen && \
    echo "LANG=en_US.UTF-8" > /etc/locale.conf && \
    echo "LC_COLLATE=C" > /etc/locale.conf && \
    echo "LC_ALL=en_US.UTF-8" > /etc/locale.conf && \
    echo "LC_TIME=de_DE.UTF-8" > /etc/locale.conf

RUN yes | pacman -S gcc-multilib

RUN useradd -r -s /bin/bash -m -d /var/aur aur && \
    echo "aur ALL=(ALL) NOPASSWD: /usr/bin/pacman" >> /etc/sudoers
ADD aur_home.tgz /var/aur/
RUN chown -R aur:aur /var/aur

USER aur
RUN mkdir -p /var/aur/.gnupg/dirmngr-cache.d && \
    touch /var/aur/.gnupg/dirmngr_ldapservers.conf && \
    chmod 700 /var/aur/.gnupg && \
    echo "keyserver-options auto-key-retrieve" > /var/aur/.gnupg/gpg.conf && \
    gpg -k && \
    dirmngr < /dev/null
RUN cd /tmp && \
    wget --no-check-certificate https://aur.archlinux.org/cgit/aur.git/snapshot/suexec.tar.gz && \
    tar -xzf suexec.tar.gz && \
    cd suexec && \
    makepkg -si --noconfirm && \
    cd /tmp && rm -rf suexec*

USER root
RUN pacman -Rsc --noconfirm $(pacman -Qdt) || echo no orphans present; pacman -Sc --noconfirm

COPY build-aur-package.sh update-aur-repo.py /usr/local/bin/
CMD ["/bin/bash"]
