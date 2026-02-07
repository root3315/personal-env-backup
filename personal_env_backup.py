#!/usr/bin/env python3
"""
personal-env-backup: Backup and restore dotfiles and environment configurations.

Supports discovering, backing up, and restoring common dotfiles and
configuration directories for personal development environments.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
from datetime import datetime
from pathlib import Path

# Default backup destination
DEFAULT_BACKUP_DIR = os.path.expanduser("~/.personal-env-backups")

# Common dotfiles to back up
COMMON_DOTFILES = [
    ".bashrc",
    ".bash_profile",
    ".bash_aliases",
    ".zshrc",
    ".zshenv",
    ".zprofile",
    ".vimrc",
    ".vim",
    ".gitconfig",
    ".gitignore_global",
    ".inputrc",
    ".tmux.conf",
    ".config/nvim",
    ".config/git",
    ".config/htop",
    ".config/i3",
    ".config/pip",
    ".config/flake8",
    ".config/starship.toml",
    ".ssh/config",
    ".Xresources",
    ".xinitrc",
    ".profile",
    ".exports",
    ".env",
]

# Config directories to include
CONFIG_DIRS = [
    ".ssh",
    ".gnupg",
    ".kube",
    ".docker",
    ".local/share/keyrings",
]


def get_home_dir():
    """Return the user's home directory."""
    return Path.home()


def discover_dotfiles():
    """Scan home directory and return list of existing dotfiles/configs."""
    home = get_home_dir()
    found = []

    for item in COMMON_DOTFILES:
        full_path = home / item
        if full_path.exists():
            found.append(str(full_path))

    for item in CONFIG_DIRS:
        full_path = home / item
        if full_path.exists():
            found.append(str(full_path))

    return sorted(found)


def compute_checksum(filepath):
    """Compute SHA256 checksum for a given file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def generate_manifest(file_list):
    """Generate a manifest dictionary with file metadata."""
    manifest = {
        "created_at": datetime.now().isoformat(),
        "hostname": os.uname().nodename,
        "username": os.getlogin(),
        "files": {},
    }

    for filepath in file_list:
        full_path = Path(filepath)
        if full_path.is_file():
            manifest["files"][filepath] = {
                "size": full_path.stat().st_size,
                "checksum": compute_checksum(filepath),
                "type": "file",
            }
        elif full_path.is_dir():
            file_count = sum(1 for _ in full_path.rglob("*") if _.is_file())
            manifest["files"][filepath] = {
                "size": 0,
                "checksum": None,
                "type": "directory",
                "file_count": file_count,
            }

    return manifest


def create_backup(output_dir=None, custom_label=None, dry_run=False):
    """Create a compressed tar.gz backup of discovered dotfiles."""
    backup_dir = Path(output_dir or DEFAULT_BACKUP_DIR)
    backup_dir.mkdir(parents=True, exist_ok=True)

    dotfiles = discover_dotfiles()

    if not dotfiles:
        print("No dotfiles or config directories found to back up.")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    label = custom_label if custom_label else timestamp
    archive_name = f"personal-env-backup_{label}.tar.gz"
    archive_path = backup_dir / archive_name

    if dry_run:
        print("DRY RUN — the following items would be included:")
        for item in dotfiles:
            marker = " [dir]" if Path(item).is_dir() else ""
            size = Path(item).stat().st_size if Path(item).is_file() else 0
            print(f"  {item}{marker}  ({size} bytes)")
        print(f"\nArchive would be: {archive_path}")
        return archive_path

    home = str(get_home_dir())
    relative_paths = [os.path.relpath(f, home) for f in dotfiles]

    manifest = generate_manifest(dotfiles)
    manifest_path = backup_dir / f"manifest_{label}.json"
    with open(manifest_path, "w") as mf:
        json.dump(manifest, mf, indent=2)

    try:
        with tarfile.open(archive_path, "w:gz") as tar:
            for rel_path in relative_paths:
                full_path = os.path.join(home, rel_path)
                tar.add(full_path, arcname=rel_path)

        # Append manifest to the archive's parent directory
        manifest_rel = str(manifest_path.relative_to(backup_dir))
        with tarfile.open(archive_path, "a:gz") as tar:
            tar.add(str(manifest_path), arcname=manifest_rel)

        archive_size = archive_path.stat().st_size
        print(f"Backup created: {archive_path}")
        print(f"  Files included: {len(dotfiles)}")
        print(f"  Archive size:   {archive_size / 1024:.1f} KB")
        print(f"  Manifest:       {manifest_path}")
        return archive_path

    except PermissionError as exc:
        print(f"Permission denied: {exc}", file=sys.stderr)
        return None
    except OSError as exc:
        print(f"OS error during backup: {exc}", file=sys.stderr)
        return None


def list_backups(output_dir=None):
    """List all existing backups in the backup directory."""
    backup_dir = Path(output_dir or DEFAULT_BACKUP_DIR)

    if not backup_dir.exists():
        print(f"Backup directory does not exist: {backup_dir}")
        return []

    archives = sorted(backup_dir.glob("personal-env-backup_*.tar.gz"))

    if not archives:
        print("No backups found.")
        return []

    print(f"Backups in {backup_dir}:")
    print("-" * 72)
    print(f"{'Archive':<45} {'Size':>10}  {'Date'}")
    print("-" * 72)

    for archive in archives:
        stat = archive.stat()
        size_kb = stat.st_size / 1024
        date_str = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
        print(f"{archive.name:<45} {size_kb:>8.1f} KB  {date_str}")

    print("-" * 72)
    print(f"Total: {len(archives)} backup(s)")
    return archives


def restore_backup(archive_path, target_dir=None, force=False):
    """Restore dotfiles from a backup archive."""
    archive = Path(archive_path)

    if not archive.exists():
        print(f"Archive not found: {archive}", file=sys.stderr)
        return False

    if not tarfile.is_tarfile(str(archive)):
        print(f"Not a valid tar.gz archive: {archive}", file=sys.stderr)
        return False

    restore_home = Path(target_dir) if target_dir else get_home_dir()

    print(f"Restoring from: {archive}")
    print(f"Target directory: {restore_home}")

    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()

        if not force:
            print("\nFiles to be restored:")
            for member in members:
                if not member.name.startswith("manifest"):
                    print(f"  {member.name}")
            print()

        for member in members:
            if member.name.startswith("manifest"):
                continue

            target_path = restore_home / member.name

            if target_path.exists() and not force:
                resp = input(f"  Overwrite {target_path}? [y/N] ")
                if resp.lower() != "y":
                    print(f"  Skipping {member.name}")
                    continue

            target_path.parent.mkdir(parents=True, exist_ok=True)
            tar.extract(member, path=restore_home)
            print(f"  Restored: {member.name}")

    print("\nRestore complete.")
    return True


def cleanup_old_backups(output_dir=None, keep=5):
    """Remove old backups, keeping only the most recent N."""
    backup_dir = Path(output_dir or DEFAULT_BACKUP_DIR)

    if not backup_dir.exists():
        print("No backup directory found.")
        return

    archives = sorted(backup_dir.glob("personal-env-backup_*.tar.gz"))
    manifests = sorted(backup_dir.glob("manifest_*.json"))

    if len(archives) <= keep:
        print(f"Only {len(archives)} backup(s) found. Nothing to clean up.")
        return

    to_remove = archives[:-keep]
    to_remove_manifests = manifests[:-keep]

    print(f"Removing {len(to_remove)} old backup(s), keeping the latest {keep}:")
    for archive in to_remove:
        print(f"  Deleting: {archive.name}")
        archive.unlink()

    for manifest in to_remove_manifests:
        manifest.unlink()

    remaining = len(list(backup_dir.glob("personal-env-backup_*.tar.gz")))
    print(f"Done. {remaining} backup(s) remaining.")


def verify_backup(archive_path):
    """Verify the integrity of a backup archive."""
    archive = Path(archive_path)

    if not archive.exists():
        print(f"Archive not found: {archive}", file=sys.stderr)
        return False

    if not tarfile.is_tarfile(str(archive)):
        print(f"Not a valid tar.gz archive: {archive}", file=sys.stderr)
        return False

    print(f"Verifying: {archive}")

    with tarfile.open(archive, "r:gz") as tar:
        members = [m for m in tar.getmembers() if not m.name.startswith("manifest")]

        errors = 0
        for member in members:
            try:
                f = tar.extractfile(member)
                if f is not None:
                    f.read()
                print(f"  OK: {member.name}")
            except Exception as exc:
                print(f"  CORRUPT: {member.name} — {exc}")
                errors += 1

    if errors == 0:
        print(f"\nVerification passed. {len(members)} file(s) intact.")
        return True
    else:
        print(f"\nVerification FAILED. {errors} file(s) corrupt.")
        return False


def main():
    """Entry point — parse arguments and dispatch."""
    parser = argparse.ArgumentParser(
        prog="personal-env-backup",
        description="Backup and restore dotfiles and environment configurations.",
    )

    sub = parser.add_subparsers(dest="command", help="Available commands")

    p_backup = sub.add_parser("backup", help="Create a new backup")
    p_backup.add_argument("-o", "--output", help="Backup output directory")
    p_backup.add_argument("-l", "--label", help="Custom label for the backup")
    p_backup.add_argument(
        "--dry-run", action="store_true", help="Show what would be backed up"
    )

    p_list = sub.add_parser("list", help="List existing backups")
    p_list.add_argument("-o", "--output", help="Backup directory to scan")

    p_restore = sub.add_parser("restore", help="Restore from a backup archive")
    p_restore.add_argument("archive", help="Path to the .tar.gz archive")
    p_restore.add_argument("-t", "--target", help="Restore target directory")
    p_restore.add_argument(
        "-f", "--force", action="store_true", help="Overwrite without prompting"
    )

    p_verify = sub.add_parser("verify", help="Verify backup integrity")
    p_verify.add_argument("archive", help="Path to the .tar.gz archive")

    p_cleanup = sub.add_parser("cleanup", help="Remove old backups")
    p_cleanup.add_argument(
        "-k", "--keep", type=int, default=5, help="Number of backups to keep"
    )
    p_cleanup.add_argument("-o", "--output", help="Backup directory")

    sub.add_parser("discover", help="Show dotfiles that would be backed up")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "backup":
        create_backup(
            output_dir=args.output,
            custom_label=args.label,
            dry_run=args.dry_run,
        )
    elif args.command == "list":
        list_backups(output_dir=args.output)
    elif args.command == "restore":
        restore_backup(
            archive_path=args.archive,
            target_dir=args.target,
            force=args.force,
        )
    elif args.command == "verify":
        verify_backup(archive_path=args.archive)
    elif args.command == "cleanup":
        cleanup_old_backups(output_dir=args.output, keep=args.keep)
    elif args.command == "discover":
        found = discover_dotfiles()
        if found:
            print(f"Found {len(found)} item(s):")
            for item in found:
                marker = " [dir]" if Path(item).is_dir() else ""
                print(f"  {item}{marker}")
        else:
            print("No dotfiles found.")


if __name__ == "__main__":
    main()
