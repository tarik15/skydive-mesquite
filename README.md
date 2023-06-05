# Skydive Mesquite Media Server

This repository contains the necessary files and instructions to set up a media server for Skydive Mesquite. The media server allows the organization to save media files from tandem skydives locally and provide links for customers to download their jump videos and photos. The server is built using a Raspberry Pi and utilizes various technologies such as Nginx, NFS, and shell scripts.

## Guide

The [System Restoration Guide](guide.md) provides a detailed step-by-step walkthrough to help you set up and configure the media server on a Raspberry Pi. The guide covers the installation of dependencies, configuration of the NFS server for file sharing, setting up the web server with Nginx, obtaining SSL/TLS certificates, and automating backups.

## Scripts

- [zipandmove](scripts/zipandmove): This shell script is used to manage the media files, compress them into archives, and move them to the appropriate location for customer downloads.

- [rpi_back](scripts/rpi_back): This shell script automates the backup process by creating system images and saving them to an external drive attached to the Raspberry Pi.

## Usage

1. Follow the instructions provided in the [System Restoration Guide](guide.md) to set up the media server on your Raspberry Pi.
2. Use the `zipandmove` script located in the `scripts` directory to manage the media files, compress them into archives, and organize them for customer downloads.
3. Utilize the `rpi_back` script located in the `scripts` directory to automate the backup process and ensure the system is regularly backed up.

## Contributing

If you discover any issues with the setup process, encounter bugs, or have suggestions for improvements, please feel free to open an issue or submit a pull request. We welcome and appreciate your contributions!

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).
