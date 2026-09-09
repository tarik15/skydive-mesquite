#!/bin/bash
#
# Install the media server scripts from this repository onto the system.
# Run it after "git pull" to put the updated scripts in place:
#
#     sudo ./install.sh
#
# The previous version of every script that changes is kept in
# /var/backups/skydive-scripts, so a bad update can be undone.
#
# Set INSTALL_DIR to install somewhere other than /usr/bin.

set -u

INSTALL_DIR="${INSTALL_DIR:-/usr/bin}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/skydive-scripts}"
STRAY_DIRS="${STRAY_DIRS:-/usr/bin /usr/local/bin}"
SCRIPTS=(zipandmove funjumper rpi_back)

SRC_DIR="$(cd "$(dirname "$0")" && pwd)/scripts"
TIMESTAMP="$(date +%Y%m%d%H%M%S)"

fail() {
    echo "ERROR: $1" >&2
    exit 1
}

[ -d "$INSTALL_DIR" ] || fail "$INSTALL_DIR does not exist."
[ -w "$INSTALL_DIR" ] || fail "Cannot write to $INSTALL_DIR. Run this with sudo."

# Check every script is present and valid before installing any of them, so a
# syntax error cannot leave the system half updated.
for name in "${SCRIPTS[@]}"; do
    [ -f "$SRC_DIR/$name" ] || fail "$SRC_DIR/$name is missing. Run this from the repository."
    bash -n "$SRC_DIR/$name" || fail "$SRC_DIR/$name has a syntax error. Nothing was installed."
done

mkdir -p "$BACKUP_DIR" || fail "Could not create $BACKUP_DIR"

updated=0
for name in "${SCRIPTS[@]}"; do
    src="$SRC_DIR/$name"
    dest="$INSTALL_DIR/$name"

    if [ -f "$dest" ] && cmp -s "$src" "$dest"; then
        echo "unchanged  $dest"
        continue
    fi

    if [ -f "$dest" ]; then
        cp -p "$dest" "$BACKUP_DIR/${name}.${TIMESTAMP}" || fail "Could not back up $dest"
        action="updated   "
    else
        action="installed "
    fi

    # Write to a temporary file in the same directory and rename it into place.
    # Overwriting a script that happens to be running would otherwise confuse
    # the shell that is still reading it.
    tmp="$(mktemp "${INSTALL_DIR}/.${name}.XXXXXX")" || fail "Could not create a temporary file in $INSTALL_DIR"
    trap 'rm -f "$tmp"' EXIT
    cat "$src" > "$tmp" || fail "Could not write to $tmp"
    chmod 755 "$tmp" || fail "Could not set permissions on $tmp"
    mv -f "$tmp" "$dest" || fail "Could not move $tmp into place"
    trap - EXIT

    echo "$action $dest"
    updated=$((updated + 1))
done

echo
if [ "$updated" -eq 0 ]; then
    echo "Everything was already up to date."
else
    echo "$updated script(s) changed. The previous versions are in $BACKUP_DIR."
fi

# The rest are things a person has to decide about, not things to change here.
if grep -q 'yourdoman\|your@email\.com' "$INSTALL_DIR/rpi_back" 2>/dev/null; then
    echo
    echo "WARNING: $INSTALL_DIR/rpi_back still has a placeholder e-mail address."
    echo "         Backup failures will not reach anyone until EMAIL_ADDRESS is set."
fi

# Older installs put copies in /usr/local/bin, sometimes named rpi_back.sh.
# Leaving them there means an out of date script can still be run by mistake.
for stray in rpi_back rpi_back.sh zipandmove zipandmove.sh funjumper funjumper.sh; do
    for dir in $STRAY_DIRS; do
        [ "$dir" = "$INSTALL_DIR" ] && continue
        if [ -e "$dir/$stray" ]; then
            echo
            echo "WARNING: $dir/$stray is left over from an older install."
            echo "         Remove it so nothing runs the old copy:  sudo rm $dir/$stray"
        fi
    done
done

if ! crontab -l 2>/dev/null | grep -q "rpi_back"; then
    echo
    echo "WARNING: this user's crontab has no rpi_back entry, so backups are not"
    echo "         scheduled. See \"Installing the Scripts\" in guide.md."
elif ! crontab -l 2>/dev/null | grep -q "$INSTALL_DIR/rpi_back"; then
    echo
    echo "WARNING: the crontab calls rpi_back from a path other than $INSTALL_DIR,"
    echo "         so the backup may be running an old copy or none at all."
    echo "         Check it with: sudo crontab -l"
fi
