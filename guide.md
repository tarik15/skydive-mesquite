System Restoration Guide for Raspberry Pi

System Restoration Guide for Raspberry Pi
=========================================

This guide will walk you through the process of restoring a Raspberry Pi system to run the server developed by Tarik. This server enables Skydive Mesquite to have their own local server and provide links for customers to download their jump media. The server is controlled by Nginx, files are read from a shared NFS folder, and most of the system is managed through a shell script called "zipandmove". Additionally, there is a backup routine that runs every two weeks, saving an image of the entire system on an external drive attached to the Raspberry Pi.

Setting up NFS Server for Other Machines
----------------------------------------

1.  Install the necessary dependencies for NFS:

    sudo apt install nfs-kernel-server

2.  Enable the NFS server to start on boot:

    sudo systemctl enable --now nfs-server

3.  Create the directory to be shared with others:

    mkdir -p /media/nfs

4.  Edit the NFS configuration file:

    sudo nano /etc/exports

5.  Add the following line to the bottom of the file, ensuring that the network matches your current local network:

    /media/nfs 192.168.1.0/24(rw,all_squash,insecure,async,no_subtree_check,anonuid=1000,anongid=1000)

6.  Export the new configuration:

    sudo exportfs -arv

Connecting to the NFS from Other Computers (not the Raspberry Pi)
-----------------------------------------------------------------

1.  Install the necessary dependencies for NFS:

    sudo apt install nfs-common

2.  Mount the NFS share for the first time to test (replace XXX.XXX.XXX.XXX with the Raspberry Pi's local IP):

    sudo mount -t nfs4 XXX.XXX.XXX.XXX:/media/nfs /media/share

3.  If you can access the shared directory now, make the mount automatic:

    sudo nano /etc/fstab

4.  Add the following line to the bottom of the file, replacing XXX.XXX.XXX.XXX with the Raspberry Pi's local IP:

    XXX.XXX.XXX.XXX:/media/nfs /media/share nfs4 defaults,user,exec 0 0

5.  Commit the configuration:

    sudo mount -a

Setting up the Web Server with Nginx
------------------------------------

1.  Install Nginx:

    sudo apt install nginx

2.  Create a configuration file for skydivingstuff.com:

    sudo nano /etc/nginx/conf.d/www.skydivingstuff.com

3.  Paste the following configuration into the file:

    server {
        server_name skydivingstuff.com www.skydivingstuff.com;
    
        location /media {
            alias /home/monolith/Web/;
        }
    
        location / {
            return 301 https://skydivemesquite.com;
        }
    }

4.  Follow the instructions in this [guide](https://www.nginx.com/blog/using-free-ssltls-certificates-from-lets-encrypt-with-nginx/) to obtain and configure a free SSL/TLS certificate from Let's Encrypt with Nginx:

    sudo apt update
    sudo apt install certbot
    sudo apt install python3-certbot-nginx
    sudo nginx -t && nginx -s reload
    sudo certbot --nginx -d skydivingstuff.com -d www.skydivingstuff.com

5.  Automate the certificate renewal process:

    sudo crontab -e

    0 12 * * * /usr/bin/certbot renew --quiet

Moving Required Scripts
-----------------------

1.  Move the "zipandmove" script to either `/usr/bin/` or `/usr/local/bin`:
'''
    sudo cp ~/Documents/zipandmove /usr/bin
'''
2.  Copy the "rpi\_back" script to either `/usr/bin/` or `/usr/local/bin`:

    sudo cp ~/Documents/rpi_back /usr/bin

3.  Automate the "rpi\_back" script:

    sudo crontab -e

    0 1 * * 1/2 /usr/local/bin/rpi_back.sh
