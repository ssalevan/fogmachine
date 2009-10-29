%define _binaries_in_noarch_packages_terminate_build 0

Name:                   fogmachine
Summary:                Cloud creation tool
Version:                0.1
Release:                1%{?dist}
Source0:                fogmachine-%{version}.tar.gz
Epoch:                  0
License:                GPLv2+
URL:                    http://chooselocalmusic.com/
BuildArch:              noarch
Group:                  Applications/System
Vendor:                 Fedora Project
Distribution:           Fedora

Requires: libvirt
Requires: libvirt-python
Requires: python
Requires: python-elixir
Requires: python-pycurl
Requires: python-simplejson

BuildRequires: python-devel
BuildRequires: python-setuptools

Requires(post):  /sbin/chkconfig
Requires(preun): /sbin/chkconfig

%description
Fogmachine allows users to deploy virtual machines across a wide array of host
machines, as specified in a configuration file.  It uses Cobbler and Facebook's
Tornado framework to accomplish the heavy lifting, and it's got a swanky WebUI
for your viewing pleasure.

%prep
setup -q

%install
test "x$RPM_BUILD_ROOT" != "x" && rm -rf $RPM_BUILD_ROOT
%if 0%{?suse_version} >= 1000
PREFIX="--prefix=/usr"
%endif
%{__python} setup.py install --optimize=1 --root=$RPM_BUILD_ROOT $PREFIX

%post
if [ "$1" = "1" ];
then
    # This happens upon initial install. Upgrades will follow the next else
    /sbin/chkconfig --add fogmachined
elif [ "$1" -ge "2" ];
then
    /sbin/service fogmachined condrestart
fi

%preun
if [ $1 = 0 ]; then
    /sbin/service fogmachined stop >/dev/null 2>&1 || :
    chkconfig --del fogmachined || :
fi

%postun
if [ "$1" -ge "1" ]; then
    /sbin/service fogmachined condrestart >/dev/null 2>&1 || :
    /sbin/service fogmachined condrestart >/dev/null 2>&1 || :
fi

%clean
test "x$RPM_BUILD_ROOT" != "x" && rm -rf $RPM_BUILD_ROOT

%files
%defattr(755,root,root)
%{_bindir}/fogmachined

%defattr(-,root,root)
%dir /etc/fogmachine
%config(noreplace) /etc/fogmachine/*.conf
%dir %{python_sitelib}/fogmachine
%{python_sitelib}/fogmachine/*.py*
/etc/init.d/fogmachined

%defattr(755,root,root)
%dir /usr/share/fogmachine
/usr/share/fogmachine/*
%dir /usr/share/fogmachine/static
/usr/share/fogmachine/static/*
%dir /usr/share/fogmachine/static/applets
/usr/share/fogmachine/static/applets/*
%dir /usr/share/fogmachine/static/css
/usr/share/fogmachine/static/css/*
%dir /usr/share/fogmachine/static/images
/usr/share/fogmachine/static/images/*
%dir /usr/share/fogmachine/static/js
/usr/share/fogmachine/static/js/*
%dir /usr/share/fogmachine/static/templates
/usr/share/fogmachine/static/templates/*

%doc AUTHORS CHANGELOG README COPYING

%changelog

* Thu Oct 29 2009 Steve Salevan <ssalevan@redhat.com> - 0.1.0-1
- The fog permeates...
