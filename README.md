# Skydive Mesquite Media Server

This repository contains the necessary files and instructions to set up a media server for Skydive Mesquite. The media server allows the organization to save media files from tandem skydives locally and provide links for customers to download their jump videos and photos. The server is built using a Raspberry Pi and utilizes various technologies such as Nginx, NFS, and shell scripts.

It also includes the web UI staff use day to day, so nobody needs SSH to publish a jump.

## Guide

The [System Restoration Guide](guide.md) provides a detailed step-by-step walkthrough to help you set up and configure the media server on a Raspberry Pi. The guide covers the installation of dependencies, configuration of the NFS server for file sharing, setting up the web server with Nginx, obtaining SSL/TLS certificates, and automating backups.

## Scripts

- [zipandmove](scripts/zipandmove): This shell script is used to manage the media files, compress them into archives, and move them to the appropriate location for customer downloads.

- [rpi_back](scripts/rpi_back): This shell script automates the backup process by creating system images and saving them to an external drive attached to the Raspberry Pi.

- [funjumper](scripts/funjumper): This shell script is similar to [zipandmove](scripts/zipandmove) but sends the links to e-mails you provide while running it.

## Web UI

A small Flask app, in [webapp](webapp), that staff reach at `/ui` over HTTPS or on the LAN at `http://monolith.local:8080/ui/`. It runs in Docker as the `monolith` user so it can write the NFS directories, and it can upload footage, run the scripts, list the published links, and tail the logs. Logins come from `.env`; the admin account can publish tandem media, staff can only use the fun jumper page.

The container builds the scripts from the same [scripts](scripts) directory that `install.sh` copies to `/usr/bin`, so the web UI and the command line always run identical code.

## Credentials

This repository is public and holds no real credentials. Every secret lives in a git-ignored file on the Pi, with a template checked in:

| Real file, on the Pi | Template here |
|---|---|
| `.env` | [.env.example](.env.example) |
| `/etc/msmtprc` | [docker/msmtprc.example](docker/msmtprc.example) |
| `/etc/skydive-media.conf` | [skydive-media.conf.example](skydive-media.conf.example) |

`install.sh` creates each one from its template if it is missing, never overwrites an existing one, and warns about any value still left blank. To guard against a slip, enable the pre-commit hook in every clone:

```
git config core.hooksPath .githooks
```

It refuses any commit containing an access token, a private key, a URL with an embedded password, or one of the live files above.
  
## Installing

Run [install.sh](install.sh) after cloning or pulling this repository. It installs the shell scripts into `/usr/bin`, creates any missing configuration from the templates, installs the Nginx pieces, and rebuilds and restarts the web UI container:

```
git pull
sudo ./install.sh
```

To update only the shell scripts and leave the web UI running untouched:

```
sudo SKIP_UI=1 ./install.sh
```

It refuses to install a script with a syntax error, keeps the previous version of anything it replaces in `/var/backups/skydive-scripts`, and reports what changed.

The notification e-mail addresses are not in this repository. On the first run `install.sh` creates `/etc/skydive-media.conf` from [skydive-media.conf.example](skydive-media.conf.example) and never overwrites it afterwards, so a `git pull` cannot clobber local settings.

## Usage

1. Follow the instructions provided in the [System Restoration Guide](guide.md) to set up the media server on your Raspberry Pi.
2. Use the `zipandmove` script located in the `scripts` directory to manage the media files, compress them into archives, and organize them for customer downloads.
3. Utilize the `rpi_back` script located in the `scripts` directory to automate the backup process and ensure the system is regularly backed up.

## Contributing

If you discover any issues with the setup process, encounter bugs, or have suggestions for improvements, please feel free to open an issue or submit a pull request. We welcome and appreciate your contributions!

## BASE Jumping is dangerous kids

I created this guide in case I'm no longer here and folks at Skydive Mesquite need to fix or rebuild their Media Server. 

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).
