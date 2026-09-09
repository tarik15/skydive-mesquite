System Restoration Guide for Raspberry Pi
=========================================

This guide will walk you through the process of restoring a Raspberry Pi system to run the server developed by Tarik. This server enables Skydive Mesquite to have their own local server and provide links for customers to download their jump media. The server is controlled by Nginx, files are read from a shared NFS folder, and most of the system is managed through the shell scripts "zipandmove" (tandem media) and "funjumper" (fun jumper media). Additionally, there is a backup routine that saves an image of the entire system to `/media/nfs/pi-backup` on the external disk.

Everything below matches what the scripts in `scripts/` actually do. If you change a path here, change it in the scripts too.

Installing Dependencies
-----------------------

The scripts rely on `zip` and `mail`:

`sudo apt update`

`sudo apt install zip mailutils`

Note: `mailutils` provides the `mail` command, but the Pi still needs a working mail transport (a local MTA or an SMTP relay) before any of the notification e-mails will actually leave the machine. If mail was previously configured on this Pi, restore that configuration as well, otherwise the scripts will still zip and publish media correctly but the e-mail steps will fail.

Mounting the External Disk
--------------------------

All of the media, the backups, and the directory shared over NFS live on an external disk mounted at `/media/nfs`. Mount it before anything else.

If you create the directories in the following sections while the disk is not mounted, they are silently created on the SD card instead. Everything appears to work and media publishes normally, so the problem only shows up later, either when the card fills up or when the disk is finally mounted over the top and the files seem to have disappeared.

1.  Attach the disk and identify it:

    `lsblk -f`

    Find the external disk's partition, for example `sda1`, and note its `UUID` and `FSTYPE`. Mount by UUID rather than by `/dev/sda1`, because device names can change depending on what is plugged in at boot.

2.  Create the mount point:

    `sudo mkdir -p /media/nfs`

3.  Add the disk to the filesystem table:

    `sudo nano /etc/fstab`

    Add the following line. This is the disk that is in service now, a 1.9 TB ext4 partition. If it has been replaced, use the UUID and filesystem that step 1 reported for the new one:
```fstab
    UUID=7a19384b-696a-4f1c-87aa-320653570f43 /media/nfs ext4 defaults,nofail,x-systemd.device-timeout=10 0 2
```
    `nofail` lets the Pi finish booting when the disk is missing or has died, instead of dropping to an emergency prompt on a machine that has no monitor attached. The tradeoff is that a missing disk is no longer obvious at boot, which is why the check in step 5 matters.

4.  Mount it:

    `sudo mount -a`

5.  Confirm it actually mounted before going any further:

    `mountpoint /media/nfs`

    This must report that `/media/nfs` is a mountpoint. If it does not, stop and fix the mount. Every section below assumes `/media/nfs` is the external disk.

The filesystem should be a Linux one, normally `ext4`. NTFS and exFAT do not record Unix ownership, so the `chown` in "Creating the Directory Layout" would not stick and the `anonuid`/`anongid` settings on the NFS export would not behave as described below.

Setting up NFS Server for Other Machines
----------------------------------------

1.  Install the necessary dependencies for NFS:

    `sudo apt install nfs-kernel-server`

2.  Enable the NFS server to start on boot:

    `sudo systemctl enable --now nfs-server`

3.  Confirm the external disk is mounted at `/media/nfs`, which is the directory that will be shared:

    `mountpoint /media/nfs`

4.  Edit the NFS configuration file:

    `sudo nano /etc/exports`

5.  Add the following line to the bottom of the file, ensuring that the network matches your current local network:

    `/media/nfs 192.168.1.0/24(rw,all_squash,insecure,async,no_subtree_check,anonuid=1000,anongid=1000)`

6.  Export the new configuration:

    `sudo exportfs -arv`

Creating the Directory Layout
-----------------------------

The scripts do not create most of their working directories, and they will fail if these are missing. First confirm the external disk is still mounted, otherwise these directories end up on the SD card:

`mountpoint /media/nfs`

Then create all of them up front:

```bash
sudo mkdir -p /media/nfs/share \
              /media/nfs/funjumper \
              /media/nfs/web/fun \
              /media/nfs/backed \
              /media/nfs/pi-backup
sudo chown -R 1000:1000 /media/nfs
mkdir -p /home/monolith/zipandmove
```

What each directory is for:

| Directory | Purpose |
| --- | --- |
| `/media/nfs/share` | Drop folder for tandem media. `zipandmove` reads from here. |
| `/media/nfs/funjumper` | Drop folder for fun jumper media. `funjumper` reads from here. |
| `/media/nfs/web` | Zipped tandem media served by Nginx. Cleared after 180 days. |
| `/media/nfs/web/fun` | Zipped fun jumper media served by Nginx. Cleared after 14 days. |
| `/media/nfs/backed` | Original tandem folders, kept for 180 days. |
| `/media/nfs/pi-backup` | System images written by `rpi_back`, kept for 90 days. |
| `/home/monolith/zipandmove` | Lock files and logs for `zipandmove` and `funjumper`. |

The `chown` to `1000:1000` matches the `anonuid`/`anongid` in the NFS export above, so files written over NFS and files written by the scripts have the same owner. If the primary user on this Pi is not UID 1000, use that user's UID and GID instead and update the export line to match.

Connecting to the NFS from Other Computers (not the Raspberry Pi)
-----------------------------------------------------------------

1.  Install the necessary dependencies for NFS:

    `sudo apt install nfs-common`

2.  Mount the NFS share for the first time to test (replace XXX.XXX.XXX.XXX with the Raspberry Pi's local IP):

    `sudo mount -t nfs4 XXX.XXX.XXX.XXX:/media/nfs /media/share`

3.  If you can access the shared directory now, make the mount automatic:

    `sudo nano /etc/fstab`

4.  Add the following line to the bottom of the file, replacing XXX.XXX.XXX.XXX with the Raspberry Pi's local IP:

    `XXX.XXX.XXX.XXX:/media/nfs /media/share nfs4 defaults,user,exec 0 0`

5.  Commit the configuration:

    `sudo mount -a`

Setting up the Web Server with Nginx
------------------------------------

1.  Install Nginx:

    `sudo apt install nginx`

2.  Create a configuration file for skydivingstuff.com. The filename **must** end in `.conf`, because Nginx only includes `/etc/nginx/conf.d/*.conf`:

    `sudo nano /etc/nginx/conf.d/www.skydivingstuff.com.conf`

3.  Paste the following configuration into the file:
```nginx
    server {
        listen 80;
        server_name skydivingstuff.com www.skydivingstuff.com;

        location /media/ {
            alias /media/nfs/web/;
        }

        location / {
            return 301 https://skydivemesquite.com;
        }
    }
```
The `alias` must point at `/media/nfs/web/`, which is where `zipandmove` and `funjumper` put the finished zip files. This is what makes the links the scripts e-mail out resolve:

  - `zipandmove` produces `https://skydivingstuff.com/media/NAME.zip` -> `/media/nfs/web/NAME.zip`
  - `funjumper` produces `https://skydivingstuff.com/media/fun/NAME.zip` -> `/media/nfs/web/fun/NAME.zip`

4.  Follow the instructions in this [guide](https://www.nginx.com/blog/using-free-ssltls-certificates-from-lets-encrypt-with-nginx/) to obtain and configure a free SSL/TLS certificate from Let's Encrypt with Nginx:

    `sudo apt update`

    `sudo apt install certbot`

    `sudo apt install python3-certbot-nginx`

    `sudo nginx -t && sudo systemctl reload nginx`

    `sudo certbot --nginx -d skydivingstuff.com -d www.skydivingstuff.com`

5.  Automate the certificate renewal process:

    `sudo crontab -e`
```crontab
    0 12 * * * /usr/bin/certbot renew --quiet
```
6.  Confirm a customer link actually downloads. Drop a test zip into `/media/nfs/web/` and fetch it:

    `curl -I https://skydivingstuff.com/media/test.zip`

    A `200` means the alias and permissions are correct. A `403` means the Nginx worker cannot read the files, so recheck the ownership set in "Creating the Directory Layout".

Installing the Scripts
----------------------

All three scripts live in `/usr/bin`, which is where the cron entry below expects them. `install.sh` in this repository puts them there.

1.  Get the repository onto the Pi, or update the copy that is already on it:

    `git clone git@github.com:tarik15/skydive-mesquite.git`

    or, from inside an existing clone:

    `git pull`

2.  Install the scripts:

    `sudo ./install.sh`

    It checks every script for syntax errors before installing any of them, so a bad pull cannot leave the system half updated. Each script it replaces is copied to `/var/backups/skydive-scripts` first, and it reports what changed. Run it again after every `git pull`; when nothing has changed it says so and does nothing.

    To install somewhere other than `/usr/bin`, set `INSTALL_DIR`:

    `sudo INSTALL_DIR=/usr/local/bin ./install.sh`

3.  Check the notification e-mail addresses at the top of each script:

    - `zipandmove` sends the day's media links to `DESTINATION_EMAIL`, set to `skydive@skydivemesquite.com`.
    - `rpi_back` sends backup successes and failures to `EMAIL_ADDRESS`, which is still the placeholder `admin@yourdoman.com` and needs to be set to whoever should be told when a backup fails.

    `funjumper` prompts for its recipients when you run it, so it needs no edit.

4.  Automate the "rpi\_back" script. It runs on the 1st and 15th of each month at 01:00, which is the every-two-weeks cadence the backup routine is meant to have:

    `sudo crontab -e`
```crontab
    0 1 1,15 * * /usr/bin/rpi_back
```
    The path in the crontab must match where `install.sh` put the script. If the two disagree, cron silently runs nothing and the backups stop without any warning. This has happened before: the crontab called `/usr/local/bin/rpi_back.sh` while the script lived in `/usr/bin`, and no backups were taken at all.

5.  If this Pi had an older install, remove the leftovers so nothing can run an out of date copy. `install.sh` names any it finds:

    `sudo rm -f /usr/local/bin/rpi_back /usr/local/bin/rpi_back.sh /usr/local/bin/zipandmove /usr/local/bin/funjumper`

    Then confirm the crontab has exactly one `rpi_back` line and that it points at `/usr/bin/rpi_back`:

    `sudo crontab -l | grep rpi_back`

6.  Take the first backup by hand instead of waiting for cron, and confirm it lands:

    `sudo /usr/bin/rpi_back`

    `ls -lh /media/nfs/pi-backup`

    This copies the whole SD card, so it takes a while and the image is as large as the card. Check there is room for it first with `df -h /media/nfs`, and remember `MAX_DAYS` in the script keeps 90 days of images.
Running the Scripts
-------------------

`zipandmove` is run by hand when a day's tandem media is ready to publish:

`zipandmove`

`funjumper` is also run by hand, and will prompt for the e-mail addresses to send the links to:

`funjumper`

Before zipping, both scripts normalize the top level folder names in their drop folder, so it does not matter how carefully the folder was typed. Runs of blanks collapse to one, leading and trailing blanks are dropped, blanks become underscores, and the result is lower cased: `  TANDEM   Bob Smith ` is published as `tandem_bob_smith.zip`. Underscores that were typed on purpose are left alone. Download links are case sensitive, so this is what keeps them predictable no matter how the folder was typed. If two folders in the same batch normalize to the same name, both are still published: the second one gets a `-2` suffix (`tandem_bob-2.zip`), and the script prints an `ERROR:` line to the screen and to the log naming both folders. That is not fatal, but it means two jumps had the same name, so confirm they really are different jumps before sending the links out. Errors are written to standard error, so `zipandmove 2> errors.txt` will capture just those.

Both write progress to `/home/monolith/zipandmove/zipandmove.log` and `/home/monolith/zipandmove/fun.log` respectively. If a script reports that another instance is already running and you are certain it is not, check for a stale lock file in `/home/monolith/zipandmove/`.

`rpi_back` runs from cron, must be run as root, and logs to `/var/log/rpi_backup.log`. It e-mails `EMAIL_ADDRESS` whether it succeeds or fails, and the success message includes the size of the image it wrote. If a run is interrupted or the Pi loses power part way through, nothing needs cleaning up by hand: the lock is held on an open file descriptor and the kernel releases it automatically. A partial image is left behind on failure so it can be looked at, and the error message names it; delete it once you are done with it.
