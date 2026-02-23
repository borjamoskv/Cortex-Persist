#!/zsh
# Management script for CORTEX Cloud Mount
# Remote: gdrive
# Mount Point: ~/Cloud

MOUNT_POINT="$HOME/Cloud"
REMOTE="gdrive:"

function mount_drive() {
    if mount | grep -q "$MOUNT_POINT"; then
        echo "Cloud already mounted at $MOUNT_POINT"
    else
        echo "Mounting $REMOTE to $MOUNT_POINT..."
        # Note: mount on macOS via rclone requires FUSE or nfsmount. 
        # Since FUSE might not be installed, we use a background sync or rclone serve if mount fails.
        # However, for simply moving files and symlinking, we can use rclone directly.
        rclone mount $REMOTE $MOUNT_POINT --vfs-cache-mode full --daemon
    fi
}

function check_status() {
    rclone about $REMOTE
}

case "$1" in
    mount)
        mount_drive
        ;;
    status)
        check_status
        ;;
    *)
        echo "Usage: $0 {mount|status}"
        exit 1
esac
